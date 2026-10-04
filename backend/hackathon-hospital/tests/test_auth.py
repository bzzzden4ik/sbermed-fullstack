from app.security import get_password_hash, verify_password


def test_register_patient(client):
    payload = {
        "email": "patient@clinic.com",
        "password": "patientpassword123",
        "full_name": "Clinic Patient",
        "role": "patient"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "patient@clinic.com"
    assert data["role"] == "patient"
    assert "id" in data

def test_register_doctor(client):
    response = client.post("/auth/register", json={
        "email": "doctor@clinic.com",
        "password": "doctorpassword123",
        "full_name": "Clinic Doctor",
        "role": "doctor"
    })
    assert response.status_code == 201
    doctors = client.get("/doctors").json()
    assert any(doctor["email"] == "doctor@clinic.com" for doctor in doctors)

def test_register_existing_user(client):
    payload = {
        "email": "patient@clinic.com",
        "password": "patientpassword123",
        "full_name": "Clinic Patient",
        "role": "patient"
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_admin_registration_is_rejected(client):
    response = client.post("/auth/register", json={
        "email": "admin@clinic.com",
        "password": "adminpassword123",
        "full_name": "Clinic Admin",
        "role": "admin"
    })
    assert response.status_code == 422
    login_response = client.post("/auth/login", json={
        "email": "admin@clinic.com",
        "password": "adminpassword123"
    })
    assert login_response.status_code == 401

def test_unsupported_role_is_not_supported(client):
    response = client.post("/auth/register", json={
        "email": "unsupported@clinic.com",
        "password": "password123",
        "full_name": "Unsupported User",
        "role": "unsupported"
    })
    assert response.status_code == 422

def test_login_success(client):
    # Register user
    client.post("/auth/register", json={
        "email": "patient@clinic.com",
        "password": "patientpassword123",
        "full_name": "Clinic Patient",
        "role": "patient"
    })
    
    # Login
    response = client.post("/auth/login", json={
        "email": "patient@clinic.com",
        "password": "patientpassword123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_current_user_profile(client):
    client.post("/auth/register", json={
        "email": "patient@clinic.com",
        "password": "patientpassword123",
        "full_name": "Clinic Patient",
        "role": "patient"
    })
    login_response = client.post("/auth/login", json={
        "email": "patient@clinic.com",
        "password": "patientpassword123"
    })
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "patient@clinic.com"
    assert response.json()["full_name"] == "Clinic Patient"
    assert response.json()["role"] == "patient"
    assert "id" in response.json()
    assert "created_at" in response.json()
    assert "password_hash" not in response.json()

def test_get_current_user_profile_requires_authentication(client):
    response = client.get("/auth/me")

    assert response.status_code == 401

def test_login_wrong_credentials(client):
    response = client.post("/auth/login", json={
        "email": "nonexistent@clinic.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "detail" in response.json()

def test_argon2_password_hashing_supports_long_passwords():
    password = "long-password-" * 10
    password_hash = get_password_hash(password)

    assert password_hash.startswith("$argon2id$")
    assert verify_password(password, password_hash)
    assert not verify_password("different-password", password_hash)
