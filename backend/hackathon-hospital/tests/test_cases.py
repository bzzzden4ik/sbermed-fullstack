from tests.conftest import register_and_login

SUMMARY = {
    "chief_complaint": "Давящая боль в груди при подъёме по лестнице",
    "symptoms": ["давящая боль за грудиной", "одышка при нагрузке"],
    "onset_and_duration": "около двух недель, усиливается",
    "severity": "5/10, мешает подниматься по лестнице",
    "medical_history": "гипертония",
    "current_medications": "эналаприл",
    "allergies": "не отмечает",
    "red_flags": ["боль при нагрузке"],
    "patient_questions": "нужно ли обследование сердца",
}


def setup_clinic(client, admin_headers):
    """General practitioner (self-registered) and a cardiologist (created by admin)."""
    gp_headers = register_and_login(client, "gp@clinic.com", "doctor", "Dr General")
    response = client.post("/doctors", json={
        "full_name": "Dr Heart",
        "specialization": "Cardiology",
        "qualification": "MD",
        "phone_number": "1112223333",
        "email": "heart@clinic.com",
        "consultation_fee": 1500,
        "available_timings": "Mon-Fri 09:00-17:00",
    }, headers=admin_headers)
    assert response.status_code == 201
    cardio_id = response.json()["id"]
    cardio_token = client.post("/auth/login", json={"email": "heart@clinic.com", "password": "doctor123"}).json()["access_token"]
    gp_id = next(d["id"] for d in client.get("/doctors").json() if d["email"] == "gp@clinic.com")
    return gp_headers, gp_id, {"Authorization": f"Bearer {cardio_token}"}, cardio_id


def start_case(client, headers):
    conversation = client.post("/conversations", json={"message": "Болит в груди"}, headers=headers).json()["conversation"]
    return conversation["id"], conversation["case_id"]


def test_full_case_flow_with_referral(client, admin_headers, make_patient, fake_ai, monkeypatch):
    from app.routes import cases

    emails = []
    monkeypatch.setattr(cases, "send_case_decision_email", lambda **kwargs: emails.append(kwargs))

    gp_headers, gp_id, cardio_headers, cardio_id = setup_clinic(client, admin_headers)
    patient_headers, patient = make_patient("patient@clinic.com", "9000000010", "Мария Иванова")
    other_headers, _ = make_patient("other@clinic.com", "9000000011")

    conversation_id, case_id = start_case(client, patient_headers)
    assert "Cardiology" in fake_ai[0]["instructions"]
    assert client.get(f"/cases/{case_id}", headers=patient_headers).json()["status"] == "AI_COLLECTING"

    # Doctors never see a case while the AI is still collecting.
    assert client.get("/cases", headers=cardio_headers).json() == []
    assert client.get(f"/cases/{case_id}", headers=cardio_headers).status_code == 403

    # Another patient cannot submit someone else's conversation.
    foreign = client.post("/cases/submit", json={
        "conversation_id": conversation_id, "summary": SUMMARY, "specialization": "Cardiology", "urgency": "medium",
    }, headers=other_headers)
    assert foreign.status_code == 404

    # This is the call the AI agent makes through MCP with the patient's token after confirmation.
    submit = client.post("/cases/submit", json={
        "conversation_id": conversation_id, "summary": SUMMARY, "specialization": "Cardiology", "urgency": "Medium",
    }, headers=patient_headers)
    assert submit.status_code == 201
    case = submit.json()
    assert case["id"] == case_id
    assert case["status"] == "READY_FOR_DOCTOR"
    assert case["doctor"]["id"] == cardio_id
    assert case["urgency"] == "medium"
    assert case["ai_summary"]["symptoms"] == SUMMARY["symptoms"]

    # Submitted cases are frozen: no resubmission, no further paid AI messages.
    assert client.post("/cases/submit", json={
        "conversation_id": conversation_id, "summary": SUMMARY, "specialization": "Cardiology", "urgency": "low",
    }, headers=patient_headers).status_code == 409
    calls_before = len(fake_ai)
    assert client.post(f"/conversations/{conversation_id}/messages", json={"content": "ещё"}, headers=patient_headers).status_code == 409
    assert len(fake_ai) == calls_before

    # Access control.
    assert client.get("/cases", headers=gp_headers).json() == []
    assert client.get(f"/cases/{case_id}", headers=gp_headers).status_code == 403
    assert client.get(f"/cases/{case_id}", headers=other_headers).status_code == 403
    assert client.get("/cases", headers=other_headers).json() == []
    assert client.post(f"/cases/{case_id}/decision", json={"decision": "NO_EXAMINATION_NEEDED"}, headers=patient_headers).status_code == 403
    assert client.post(f"/cases/{case_id}/decision", json={"decision": "NO_EXAMINATION_NEEDED"}, headers=gp_headers).status_code == 403
    assert len(client.get("/cases", headers=admin_headers).json()) == 1

    cardio_notifications = client.get("/notifications", headers=cardio_headers).json()
    assert [n["case_id"] for n in cardio_notifications] == [case_id]

    # Cardiologist reviews and refers to the general practitioner.
    assert client.post(f"/cases/{case_id}/review", headers=cardio_headers).json()["status"] == "UNDER_REVIEW"
    assert client.post(f"/cases/{case_id}/decision", json={"decision": "REFER_TO_SPECIALIST"}, headers=cardio_headers).status_code == 422
    referred = client.post(f"/cases/{case_id}/decision", json={
        "decision": "REFER_TO_SPECIALIST", "referred_doctor_id": gp_id, "comment": "Нужна оценка терапевта",
    }, headers=cardio_headers)
    assert referred.status_code == 200
    assert referred.json()["status"] == "REFERRED"
    assert referred.json()["doctor"]["id"] == gp_id
    assert referred.json()["referred_from_doctor"]["id"] == cardio_id

    # The referring doctor keeps read access but can no longer decide.
    assert client.get(f"/cases/{case_id}", headers=cardio_headers).status_code == 200
    assert client.post(f"/cases/{case_id}/decision", json={"decision": "NO_EXAMINATION_NEEDED"}, headers=cardio_headers).status_code == 403

    # The specialist makes the final decision.
    assert [c["id"] for c in client.get("/cases", headers=gp_headers).json()] == [case_id]
    final = client.post(f"/cases/{case_id}/decision", json={
        "decision": "NEEDS_EXAMINATION", "comment": "Запишитесь на ЭКГ и очный приём",
    }, headers=gp_headers)
    assert final.status_code == 200
    assert final.json()["status"] == "RESOLVED"
    assert final.json()["resolved_at"] is not None
    assert client.post(f"/cases/{case_id}/decision", json={"decision": "NO_EXAMINATION_NEEDED"}, headers=gp_headers).status_code == 409

    # Patient sees the decision, notifications and got emails; no appointment was auto-created.
    patient_case = client.get(f"/cases/{case_id}", headers=patient_headers).json()
    assert patient_case["decision"] == "NEEDS_EXAMINATION"
    assert patient_case["doctor_comment"] == "Запишитесь на ЭКГ и очный приём"
    notifications = client.get("/notifications", headers=patient_headers).json()
    assert len(notifications) == 2 and all(not n["is_read"] for n in notifications)
    assert [e["decision"] for e in emails] == ["REFER_TO_SPECIALIST", "NEEDS_EXAMINATION"]
    assert emails[1]["patient_email"] == "patient@clinic.com"
    assert client.get("/appointments", headers=patient_headers).json() == []

    assert client.post(f"/notifications/{notifications[0]['id']}/read", headers=other_headers).status_code == 404
    assert client.post(f"/notifications/{notifications[0]['id']}/read", headers=patient_headers).json()["is_read"] is True
    assert client.post("/notifications/read-all", headers=patient_headers).status_code == 204
    assert client.get("/notifications?unread_only=true", headers=patient_headers).json() == []


def test_unknown_specialization_falls_back_to_general_medicine(client, admin_headers, make_patient, fake_ai):
    _, gp_id, _, _ = setup_clinic(client, admin_headers)
    headers, _ = make_patient("fallback@clinic.com", "9000000020")
    conversation_id, _ = start_case(client, headers)
    response = client.post("/cases/submit", json={
        "conversation_id": conversation_id, "summary": SUMMARY, "specialization": "Dermatology", "urgency": "low",
    }, headers=headers)
    assert response.status_code == 201
    assert response.json()["doctor"]["id"] == gp_id
    assert client.get("/cases/specializations").json() == ["Cardiology", "General Medicine"]


def test_submit_requires_patient_role_and_valid_payload(client, admin_headers, make_patient, fake_ai):
    setup_clinic(client, admin_headers)
    headers, _ = make_patient("payload@clinic.com", "9000000030")
    conversation_id, _ = start_case(client, headers)
    payload = {"conversation_id": conversation_id, "summary": SUMMARY, "specialization": "Cardiology", "urgency": "urgent"}
    assert client.post("/cases/submit", json=payload, headers=headers).status_code == 422
    payload["urgency"] = "high"
    assert client.post("/cases/submit", json=payload, headers=admin_headers).status_code == 403
    assert client.post("/cases/submit", json=payload).status_code == 401


def test_latest_case_and_follow_up_link(client, admin_headers, make_patient, fake_ai):
    gp_headers, gp_id, cardio_headers, cardio_id = setup_clinic(client, admin_headers)
    headers, _ = make_patient("followup@clinic.com", "9000000040")
    other_headers, _ = make_patient("followup-other@clinic.com", "9000000041")

    # No sent case yet: the tool returns null (drafts don't count).
    first_conversation, _ = start_case(client, headers)
    assert client.get("/cases/latest", headers=headers).json() is None
    assert "first message of the conversation: yes" in fake_ai[0]["instructions"]

    first = client.post("/cases/submit", json={
        "conversation_id": first_conversation, "summary": SUMMARY, "specialization": "Cardiology", "urgency": "medium",
    }, headers=headers).json()
    client.post(f"/cases/{first['id']}/decision", json={
        "decision": "NO_EXAMINATION_NEEDED", "comment": "Наблюдайте за давлением",
    }, headers=cardio_headers)

    latest = client.get("/cases/latest", headers=headers).json()
    assert latest["id"] == first["id"]
    assert latest["decision"] == "NO_EXAMINATION_NEEDED"
    assert latest["doctor_comment"] == "Наблюдайте за давлением"
    assert client.get("/cases/latest", headers=other_headers).json() is None
    assert client.get("/cases/latest", headers=cardio_headers).status_code == 403

    # Follow-up complaint linked to the earlier case; another patient's case cannot be linked.
    second_conversation, _ = start_case(client, headers)
    assert f"latest sent case (earlier than this conversation): case No. {first['id']}, status RESOLVED" in fake_ai[-1]["instructions"]
    payload = {"conversation_id": second_conversation, "summary": SUMMARY, "specialization": "General Medicine", "urgency": "high"}
    foreign_conversation, _ = start_case(client, other_headers)
    assert client.post("/cases/submit", json={**payload, "conversation_id": foreign_conversation, "related_case_id": first["id"]},
                       headers=other_headers).status_code == 404
    follow_up = client.post("/cases/submit", json={**payload, "related_case_id": first["id"]}, headers=headers)
    assert follow_up.status_code == 201
    assert follow_up.json()["related_case_id"] == first["id"]
    assert follow_up.json()["doctor"]["id"] == gp_id
    assert client.get("/cases/latest", headers=headers).json()["id"] == follow_up.json()["id"]

    # The doctor handling the follow-up can read the earlier case, but cannot decide on it.
    assert client.get(f"/cases/{first['id']}", headers=gp_headers).status_code == 200
    assert client.post(f"/cases/{first['id']}/decision", json={"decision": "NO_EXAMINATION_NEEDED"}, headers=gp_headers).status_code == 403
    gp_notes = client.get("/notifications", headers=gp_headers).json()
    assert f"повторное по обращению №{first['id']}" in gp_notes[0]["message"]


def test_russian_specializations_route_and_fall_back_to_therapy(client, admin_headers, make_patient, fake_ai):
    def doctor(name, email, specialization):
        return client.post("/doctors", json={
            "full_name": name, "specialization": specialization, "qualification": "MD",
            "phone_number": "1112223333", "email": email, "consultation_fee": 2000,
            "available_timings": "Пн–Пт 09:00–17:00",
        }, headers=admin_headers).json()["id"]

    therapist = doctor("Терапевт", "ther@clinic.com", "Терапия")
    cardiologist = doctor("Кардиолог", "cardio-ru@clinic.com", "Кардиология")
    headers, _ = make_patient("ru-spec@clinic.com", "9000000300")

    def submit(spec):
        conversation_id, _ = start_case(client, headers)
        return client.post("/cases/submit", json={
            "conversation_id": conversation_id, "summary": SUMMARY, "specialization": spec, "urgency": "low",
        }, headers=headers).json()["doctor"]["id"]

    assert submit("Кардиология") == cardiologist
    assert submit("Дерматология") == therapist  # unknown specialization -> general practice
