def test_create_and_get_doctor(client, admin_headers):
    # Create doctor
    doc_payload = {
        "full_name": "Dr. John Doe",
        "specialization": "Cardiology",
        "qualification": "MD - Cardiology",
        "phone_number": "1234567890",
        "email": "johndoe@clinic.com",
        "consultation_fee": 1500.0,
        "available_timings": "Mon-Fri 09:00 - 13:00"
    }
    create_resp = client.post("/doctors", json=doc_payload, headers=admin_headers)
    assert create_resp.status_code == 201
    doc_data = create_resp.json()
    assert doc_data["full_name"] == "Dr. John Doe"
    assert doc_data["specialization"] == "Cardiology"
    doctor_login = client.post("/auth/login", json={
        "email": "johndoe@clinic.com",
        "password": "doctor123"
    })
    assert doctor_login.status_code == 200

    # Get list of doctors
    list_resp = client.get("/doctors")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # Get doctor by ID
    doc_id = doc_data["id"]
    get_resp = client.get(f"/doctors/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["email"] == "johndoe@clinic.com"

def test_create_doctor_unauthorized(client):
    # Attempt to create doctor without token
    doc_payload = {
        "full_name": "Dr. Unauthorized",
        "specialization": "Pediatrics",
        "qualification": "MBBS",
        "phone_number": "9999999999",
        "email": "unauthorized@clinic.com",
        "consultation_fee": 500.0,
        "available_timings": "Mon-Fri 14:00 - 18:00"
    }
    response = client.post("/doctors", json=doc_payload)
    assert response.status_code == 401
    login_response = client.post("/auth/login", json={
        "email": "unauthorized@clinic.com",
        "password": "doctor123"
    })
    assert login_response.status_code == 401


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def test_admin_manages_doctor_photo(client, admin_headers, tmp_path, monkeypatch):
    from app.routes import doctors

    monkeypatch.setattr(doctors, "PHOTO_DIR", str(tmp_path))
    doctor = client.post("/doctors", json={
        "full_name": "Dr Photo", "specialization": "Cardiology", "qualification": "MD",
        "phone_number": "1234567890", "email": "photo@clinic.com", "consultation_fee": 1000,
        "available_timings": "Mon-Fri 09:00-17:00",
    }, headers=admin_headers).json()
    assert doctor["photo_url"] is None

    # Upload: stored under the doctors folder and exposed through the public uploads URL.
    first = client.post(f"/doctors/{doctor['id']}/photo", files={"file": ("me.png", PNG_BYTES, "image/png")}, headers=admin_headers)
    assert first.status_code == 200
    first_url = first.json()["photo_url"]
    assert first_url.startswith("/uploads/doctors/") and first_url.endswith(".png")
    assert (tmp_path / first_url.rsplit("/", 1)[1]).read_bytes() == PNG_BYTES
    assert client.get(f"/doctors/{doctor['id']}").json()["photo_url"] == first_url

    # Replace: the new photo is saved and the old file is removed.
    second_url = client.post(f"/doctors/{doctor['id']}/photo", files={"file": ("me.jpg", JPEG_BYTES, "image/jpeg")}, headers=admin_headers).json()["photo_url"]
    assert second_url.endswith(".jpg")
    assert not (tmp_path / first_url.rsplit("/", 1)[1]).exists()

    # Type is checked by content, not by the file name or the declared content type.
    fake = client.post(f"/doctors/{doctor['id']}/photo", files={"file": ("x.png", b"<script>alert(1)</script>", "image/png")}, headers=admin_headers)
    assert fake.status_code == 400
    big = client.post(f"/doctors/{doctor['id']}/photo", files={"file": ("big.png", PNG_BYTES + b"\x00" * (5 * 1024 * 1024), "image/png")}, headers=admin_headers)
    assert big.status_code == 413

    # Only admins may change photos.
    doctor_token = client.post("/auth/login", json={"email": "photo@clinic.com", "password": "doctor123"}).json()["access_token"]
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
    assert client.post(f"/doctors/{doctor['id']}/photo", files={"file": ("me.png", PNG_BYTES, "image/png")}, headers=doctor_headers).status_code == 403
    assert client.delete(f"/doctors/{doctor['id']}/photo", headers=doctor_headers).status_code == 403
    assert client.post(f"/doctors/{doctor['id']}/photo", files={"file": ("me.png", PNG_BYTES, "image/png")}).status_code == 401
    assert client.post("/doctors/9999/photo", files={"file": ("me.png", PNG_BYTES, "image/png")}, headers=admin_headers).status_code == 404

    # Remove.
    removed = client.delete(f"/doctors/{doctor['id']}/photo", headers=admin_headers)
    assert removed.status_code == 200 and removed.json()["photo_url"] is None
    assert list(tmp_path.iterdir()) == []


def test_doctor_with_history_cannot_be_deleted(client, admin_headers, make_patient, fake_ai):
    def new_doctor(email):
        return client.post("/doctors", json={
            "full_name": f"Dr {email}", "specialization": "Cardiology", "qualification": "MD",
            "phone_number": "1234567890", "email": email, "consultation_fee": 1000,
            "available_timings": "Mon-Fri 09:00-17:00",
        }, headers=admin_headers).json()

    patient_headers, _ = make_patient("history@clinic.com", "9000000050")

    # A doctor with an appointment is protected; nothing is changed.
    busy = new_doctor("busy@clinic.com")
    appointment = client.post("/appointments", json={
        "doctor_id": busy["id"], "appointment_date": "2030-01-10", "time_slot": "09:00 - 09:30", "reason_for_visit": "check",
    }, headers=patient_headers).json()
    response = client.delete(f"/doctors/{busy['id']}", headers=admin_headers)
    assert response.status_code == 409
    assert "1 appointments" in response.json()["detail"]
    assert client.get(f"/doctors/{busy['id']}").status_code == 200
    assert client.get(f"/appointments/{appointment['id']}", headers=patient_headers).json()["doctor"]["id"] == busy["id"]

    # A doctor holding an open patient case is protected too.
    conversation = client.post("/conversations", json={"message": "Болит сердце"}, headers=patient_headers).json()["conversation"]
    case = client.post("/cases/submit", json={
        "conversation_id": conversation["id"], "summary": {"chief_complaint": "Боль в сердце"},
        "specialization": "Cardiology", "urgency": "high",
    }, headers=patient_headers).json()
    assigned_id = case["doctor"]["id"]
    blocked = client.delete(f"/doctors/{assigned_id}", headers=admin_headers)
    assert blocked.status_code == 409 and "open patient cases" in blocked.json()["detail"]

    # A doctor without any history can still be deleted.
    free = new_doctor("free@clinic.com")
    assert client.delete(f"/doctors/{free['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/doctors/{free['id']}").status_code == 404


def test_doctor_with_resolved_case_only_is_deleted_and_case_kept(client, admin_headers, make_patient, fake_ai):
    doctor = client.post("/doctors", json={
        "full_name": "Dr Solo", "specialization": "Neurology", "qualification": "MD",
        "phone_number": "1234567890", "email": "solo@clinic.com", "consultation_fee": 1000,
        "available_timings": "Mon-Fri 09:00-17:00",
    }, headers=admin_headers).json()
    doctor_headers = {"Authorization": "Bearer " + client.post("/auth/login", json={"email": "solo@clinic.com", "password": "doctor123"}).json()["access_token"]}
    patient_headers, _ = make_patient("solo-patient@clinic.com", "9000000060")
    conversation = client.post("/conversations", json={"message": "Голова"}, headers=patient_headers).json()["conversation"]
    case = client.post("/cases/submit", json={
        "conversation_id": conversation["id"], "summary": {"chief_complaint": "Головная боль"},
        "specialization": "Neurology", "urgency": "low",
    }, headers=patient_headers).json()
    assert case["doctor"]["id"] == doctor["id"]
    client.post(f"/cases/{case['id']}/decision", json={"decision": "NO_EXAMINATION_NEEDED", "comment": "Отдых"}, headers=doctor_headers)

    assert client.delete(f"/doctors/{doctor['id']}", headers=admin_headers).status_code == 204
    kept = client.get(f"/cases/{case['id']}", headers=patient_headers)
    assert kept.status_code == 200
    assert kept.json()["decision"] == "NO_EXAMINATION_NEEDED" and kept.json()["doctor"] is None


def test_doctor_with_prescription_cannot_be_deleted(client, admin_headers, make_patient):
    doctor = client.post("/doctors", json={
        "full_name": "Dr Rx", "specialization": "Therapy", "qualification": "MD",
        "phone_number": "1234567890", "email": "rx@clinic.com", "consultation_fee": 1000,
        "available_timings": "Mon-Fri 09:00-17:00",
    }, headers=admin_headers).json()
    doctor_headers = {"Authorization": "Bearer " + client.post("/auth/login", json={"email": "rx@clinic.com", "password": "doctor123"}).json()["access_token"]}
    patient_headers, _ = make_patient("rx-patient@clinic.com", "9000000070")
    appointment = client.post("/appointments", json={
        "doctor_id": doctor["id"], "appointment_date": "2030-02-10", "time_slot": "10:00 - 10:30", "reason_for_visit": "cough",
    }, headers=patient_headers).json()
    assert client.post("/prescriptions", json={
        "appointment_id": appointment["id"], "diagnosis": "ОРВИ", "medicines": ["Чай"], "dosage": "-", "instructions": "Отдых",
    }, headers=doctor_headers).status_code == 201
    response = client.delete(f"/doctors/{doctor['id']}", headers=admin_headers)
    assert response.status_code == 409
    assert "1 appointments, 1 prescriptions" in response.json()["detail"]
