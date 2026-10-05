from app.config import settings
from app.models import User
from app.security import get_password_hash
from tests.conftest import TestingSessionLocal

REGISTRATION = {"email": "consent@clinic.com", "password": "password123", "full_name": "Consent Patient", "role": "patient"}
PROFILE = {
    "full_name": "Consent Patient", "age": 30, "gender": "female", "phone_number": "9000000100",
    "address": "1 Test Street, Moscow", "blood_group": "A+", "emergency_contact": "+7 900 000-00-00",
}


def login(client, email="consent@clinic.com", password="password123"):
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_registration_requires_consent(client):
    missing = client.post("/auth/register", json=REGISTRATION)
    assert missing.status_code == 422
    declined = client.post("/auth/register", json={**REGISTRATION, "accept_terms": False})
    assert declined.status_code == 422
    assert client.post("/auth/login", json={"email": REGISTRATION["email"], "password": "password123"}).status_code == 401


def test_registration_records_consent_version_and_time(client):
    response = client.post("/auth/register", json={**REGISTRATION, "accept_terms": True})
    assert response.status_code == 201
    user = response.json()
    assert user["terms_version"] == settings.LEGAL_DOCS_VERSION
    assert user["terms_accepted_at"] is not None
    assert user["needs_consent"] is False
    headers = login(client)
    assert client.post("/patients", json=PROFILE, headers=headers).status_code == 201


def test_existing_patient_without_consent_is_blocked_until_accepting(client, fake_ai):
    # A patient account created before consent existed (no record).
    db = TestingSessionLocal()
    db.add(User(email="legacy@clinic.com", password_hash=get_password_hash("password123"), full_name="Legacy", role="patient"))
    db.commit()
    db.close()
    headers = login(client, "legacy@clinic.com")

    me = client.get("/auth/me", headers=headers).json()
    assert me["needs_consent"] is True and me["terms_accepted_at"] is None
    # Platform actions and anything that reaches the AI are refused.
    blocked = client.post("/patients", json=PROFILE, headers=headers)
    assert blocked.status_code == 403 and "Consent" in blocked.json()["detail"]
    assert client.post("/conversations", json={"message": "Болит голова"}, headers=headers).status_code == 403
    assert client.post("/convert_audio_to_text", files={"file": ("a.webm", b"x", "audio/webm")}, headers=headers).status_code == 403
    assert fake_ai == []

    assert client.post("/auth/accept-terms", json={"accept_terms": False}, headers=headers).status_code == 422
    accepted = client.post("/auth/accept-terms", json={"accept_terms": True}, headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["needs_consent"] is False
    assert accepted.json()["terms_version"] == settings.LEGAL_DOCS_VERSION
    assert client.post("/patients", json=PROFILE, headers=headers).status_code == 201


def test_new_document_version_asks_patients_again_but_not_staff(client, admin_headers, monkeypatch):
    client.post("/auth/register", json={**REGISTRATION, "accept_terms": True})
    headers = login(client)
    monkeypatch.setattr(settings, "LEGAL_DOCS_VERSION", "2099-01-01")
    assert client.get("/auth/me", headers=headers).json()["needs_consent"] is True
    assert client.get("/patients", headers=headers).status_code == 403
    # Doctors and admins are not blocked by patient consent.
    assert client.get("/reports/dashboard", headers=admin_headers).status_code == 200
