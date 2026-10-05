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


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def test_patient_profile_photo_is_private(client, admin_headers, make_patient, tmp_path, monkeypatch):
    from app.routes import patients
    from tests.conftest import register_and_login

    monkeypatch.setattr(patients, "PATIENT_PHOTO_DIR", str(tmp_path))
    headers, profile = make_patient("photo-patient@clinic.com", "9000000090")
    other_headers, _ = make_patient("photo-other@clinic.com", "9000000091")
    doctor_headers = register_and_login(client, "photo-doc@clinic.com", "doctor", "Dr Viewer")
    url = f"/patients/{profile['id']}/photo"
    assert profile["has_photo"] is False
    assert client.get(url, headers=headers).status_code == 404

    # The patient uploads their own photo; the profile only says that a photo exists.
    uploaded = client.post(url, files={"file": ("me.png", PNG_BYTES, "image/png")}, headers=headers)
    assert uploaded.status_code == 200
    assert uploaded.json()["has_photo"] is True
    assert "photo_filename" not in uploaded.json()
    stored = list(tmp_path.iterdir())
    assert len(stored) == 1 and stored[0].read_bytes() == PNG_BYTES

    # Owner, doctors and admins can view it; other patients and anonymous users cannot.
    own = client.get(url, headers=headers)
    assert own.status_code == 200 and own.content == PNG_BYTES and own.headers["content-type"] == "image/png"
    assert "no-store" in own.headers["cache-control"]
    assert client.get(url, headers=doctor_headers).status_code == 200
    assert client.get(url, headers=admin_headers).status_code == 200
    assert client.get(url, headers=other_headers).status_code == 403
    assert client.get(url).status_code == 401
    # Not reachable through the public static folder.
    assert client.get(f"/uploads/patients/{stored[0].name}").status_code == 404

    # Only the owner and admins can change it; doctors and other patients cannot.
    assert client.post(url, files={"file": ("x.png", PNG_BYTES, "image/png")}, headers=other_headers).status_code == 403
    assert client.post(url, files={"file": ("x.png", PNG_BYTES, "image/png")}, headers=doctor_headers).status_code == 403
    assert client.delete(url, headers=other_headers).status_code == 403
    assert client.post(url, files={"file": ("x.png", b"<html>not an image</html>", "image/png")}, headers=headers).status_code == 400

    # Replacing removes the old file; an admin may replace it too.
    replaced = client.post(url, files={"file": ("me.jpg", JPEG_BYTES, "image/jpeg")}, headers=admin_headers)
    assert replaced.status_code == 200
    files = list(tmp_path.iterdir())
    assert len(files) == 1 and files[0].suffix == ".jpg"
    assert client.get(url, headers=headers).headers["content-type"] == "image/jpeg"

    removed = client.delete(url, headers=headers)
    assert removed.status_code == 200 and removed.json()["has_photo"] is False
    assert list(tmp_path.iterdir()) == []
    assert client.get(url, headers=headers).status_code == 404
