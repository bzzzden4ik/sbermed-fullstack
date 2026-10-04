import datetime

def test_prescription_flow(client, admin_headers):
    # Register and login doctor user
    client.post("/auth/register", json={
        "email": "doctor_jones@clinic.com",
        "password": "doctorpassword123",
        "full_name": "Dr. Jones",
        "role": "doctor"
    })
    doc_login = client.post("/auth/login", json={
        "email": "doctor_jones@clinic.com",
        "password": "doctorpassword123"
    })
    doc_token = doc_login.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Fetch Doctor profile id from DB (it was automatically created during register doctor)
    # Let's get the list of doctors to find Dr. Jones
    doctors_resp = client.get("/doctors")
    doc_profile = [d for d in doctors_resp.json() if d["email"] == "doctor_jones@clinic.com"][0]
    doctor_id = doc_profile["id"]

    # Register patient
    pat_resp = client.post("/patients", json={
        "full_name": "Alice Cooper",
        "age": 45,
        "gender": "Female",
        "phone_number": "3334445555",
        "address": "456 Oak Ave, Seattle",
        "blood_group": "A-positive",
        "emergency_contact": "3334445556"
    }, headers=admin_headers)
    patient_id = pat_resp.json()["id"]

    # Book appointment
    appt_date = datetime.date.today().strftime("%Y-%m-%d")
    appt_resp = client.post("/appointments", json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": appt_date,
        "time_slot": "11:00 - 11:30",
        "reason_for_visit": "Chronic pain"
    }, headers=admin_headers)
    appt_id = appt_resp.json()["id"]

    # Doctor creates prescription
    prescription_payload = {
        "appointment_id": appt_id,
        "diagnosis": "Severe Migraine",
        "medicines": [{"name": "Sumatriptan", "dosage": "50mg", "instructions": "Take at onset of migraine"}],
        "dosage": "50mg",
        "instructions": "As needed, maximum 100mg in 24 hours",
        "follow_up_date": (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    }
    presc_resp = client.post("/prescriptions", json=prescription_payload, headers=doc_headers)
    assert presc_resp.status_code == 201
    presc_data = presc_resp.json()
    assert presc_data["diagnosis"] == "Severe Migraine"
    assert presc_data["doctor_id"] == doctor_id
    assert presc_data["patient_id"] == patient_id

    # A linked patient can read their own prescription but cannot create one
    patient_account = client.post("/auth/register", json={
        "email": "alice@clinic.com",
        "password": "patientpassword123",
        "full_name": "Alice Cooper",
        "role": "patient"
    }).json()
    link_resp = client.put(
        f"/patients/{patient_id}",
        json={"user_id": patient_account["id"]},
        headers=admin_headers
    )
    assert link_resp.status_code == 200
    patient_token = client.post("/auth/login", json={
        "email": "alice@clinic.com",
        "password": "patientpassword123"
    }).json()["access_token"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}
    assert len(client.get("/prescriptions", headers=patient_headers).json()) == 1
    assert client.get(f"/prescriptions/{presc_data['id']}", headers=patient_headers).status_code == 200
    assert client.post("/prescriptions", json=prescription_payload, headers=patient_headers).status_code == 403

    # Verify appointment is automatically Completed
    appt_check = client.get(f"/appointments/{appt_id}", headers=admin_headers)
    assert appt_check.json()["status"] == "Completed"
