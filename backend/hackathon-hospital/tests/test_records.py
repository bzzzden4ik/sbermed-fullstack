def test_medical_records_upload_and_download(client, admin_headers):
    # Register patient
    pat_resp = client.post("/patients", json={
        "full_name": "Bob Vance",
        "age": 50,
        "gender": "Male",
        "phone_number": "5556667777",
        "address": "Scranton, PA",
        "blood_group": "B-positive",
        "emergency_contact": "5556667778"
    }, headers=admin_headers)
    patient_id = pat_resp.json()["id"]

    # Upload valid PDF medical report
    files = {"file": ("blood_report.pdf", b"test pdf content", "application/pdf")}
    data = {"patient_id": patient_id}
    upload_resp = client.post(
        "/medical-records/upload", 
        data=data, 
        files=files, 
        headers=admin_headers
    )
    assert upload_resp.status_code == 201
    record_data = upload_resp.json()
    assert record_data["file_name"] == "blood_report.pdf"
    assert record_data["file_type"] == "pdf"

    # Upload invalid file type (e.g. TXT)
    invalid_files = {"file": ("notes.txt", b"some txt notes", "text/plain")}
    upload_resp2 = client.post(
        "/medical-records/upload", 
        data=data, 
        files=invalid_files, 
        headers=admin_headers
    )
    assert upload_resp2.status_code == 400
    assert "Unsupported file format" in upload_resp2.json()["detail"]

    # List patient records
    list_resp = client.get(f"/medical-records/{patient_id}", headers=admin_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Download record
    rec_id = record_data["id"]
    download_resp = client.get(f"/medical-records/download/{rec_id}", headers=admin_headers)
    assert download_resp.status_code == 200
    assert download_resp.content == b"test pdf content"

    # Link a patient account to this profile and allow access to its own record
    patient_account = client.post("/auth/register", json={
        "email": "bob@clinic.com",
        "password": "patientpassword123",
        "full_name": "Bob Vance",
        "role": "patient",
        "accept_terms": True
    }).json()
    link_resp = client.put(
        f"/patients/{patient_id}",
        json={"user_id": patient_account["id"]},
        headers=admin_headers
    )
    assert link_resp.status_code == 200
    patient_token = client.post("/auth/login", json={
        "email": "bob@clinic.com",
        "password": "patientpassword123"
    }).json()["access_token"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}
    assert client.get(f"/medical-records/{patient_id}", headers=patient_headers).status_code == 200
    assert client.get(f"/medical-records/download/{rec_id}", headers=patient_headers).status_code == 200

    # Patient cannot access another profile's records
    other_patient = client.post("/patients", json={
        "full_name": "Other Patient",
        "age": 38,
        "gender": "Female",
        "phone_number": "5556667799",
        "address": "Scranton, PA",
        "blood_group": "O-positive",
        "emergency_contact": "5556667788"
    }, headers=admin_headers).json()
    other_record = client.post(
        "/medical-records/upload",
        data={"patient_id": other_patient["id"]},
        files={"file": ("other_report.pdf", b"other patient content", "application/pdf")},
        headers=admin_headers
    ).json()
    assert client.get(f"/medical-records/{other_patient['id']}", headers=patient_headers).status_code == 403
    assert client.get(f"/medical-records/download/{other_record['id']}", headers=patient_headers).status_code == 403
