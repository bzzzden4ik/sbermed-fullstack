def test_patient_crud(client, admin_headers):
    # Register and login patient
    client.post("/auth/register", json={
        "email": "jane@clinic.com",
        "password": "patientpassword123",
        "full_name": "Jane Smith",
        "role": "patient"
    })
    login_resp = client.post("/auth/login", json={
        "email": "jane@clinic.com",
        "password": "patientpassword123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Register Patient
    patient_payload = {
        "full_name": "Jane Smith",
        "age": 32,
        "gender": "Female",
        "phone_number": "9876543210",
        "address": "456 Main St, New York",
        "blood_group": "O-positive",
        "emergency_contact": "9876543211"
    }
    create_resp = client.post("/patients", json=patient_payload, headers=headers)
    assert create_resp.status_code == 201
    p_data = create_resp.json()
    assert p_data["full_name"] == "Jane Smith"
    
    # Get Patient details
    p_id = p_data["id"]
    get_resp = client.get(f"/patients/{p_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["blood_group"] == "O-positive"

    # Update Patient details
    update_payload = {"age": 33}
    update_resp = client.put(f"/patients/{p_id}", json=update_payload, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["age"] == 33

    # Patients cannot create multiple profiles or view all patient profiles
    duplicate_resp = client.post("/patients", json=patient_payload, headers=headers)
    assert duplicate_resp.status_code == 400
    assert [patient["id"] for patient in client.get("/patients", headers=headers).json()] == [p_id]

    # Admins can still create profiles, but patients cannot access another patient's profile
    other_patient = client.post("/patients", json={
        **patient_payload,
        "full_name": "Other Patient",
        "phone_number": "9876543212"
    }, headers=admin_headers).json()
    other_account = client.post("/auth/register", json={
        "email": "other@clinic.com",
        "password": "patientpassword123",
        "full_name": "Other Patient",
        "role": "patient"
    }).json()
    link_resp = client.put(
        f"/patients/{other_patient['id']}",
        json={"user_id": other_account["id"]},
        headers=admin_headers
    )
    assert link_resp.status_code == 200
    assert client.get(f"/patients/{other_patient['id']}", headers=headers).status_code == 403
    assert client.put(f"/patients/{other_patient['id']}", json={"age": 40}, headers=headers).status_code == 403
    other_token = client.post("/auth/login", json={
        "email": "other@clinic.com",
        "password": "patientpassword123"
    }).json()["access_token"]
    assert client.get(f"/patients/{other_patient['id']}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 200
