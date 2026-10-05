import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.config import settings
from app.models import User
from app.security import get_password_hash

# Create in-memory SQLite database engine for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def disable_smtp_delivery(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")

@pytest.fixture(autouse=True, scope="function")
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after test completes
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def admin_headers(client):
    db = TestingSessionLocal()
    db.add(User(
        email="admin@clinic.com",
        password_hash=get_password_hash("adminpassword123"),
        full_name="Clinic Admin",
        role="admin"
    ))
    db.commit()
    db.close()

    login_response = client.post("/auth/login", json={
        "email": "admin@clinic.com",
        "password": "adminpassword123"
    })
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email, role, full_name="Test User", password="password123"):
    client.post("/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name,
        "role": role,
        "accept_terms": True,
    })
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_patient(client):
    """Create a patient account with a linked patient profile; returns (headers, profile)."""
    def _make(email, phone, full_name="Test Patient"):
        headers = register_and_login(client, email, "patient", full_name)
        response = client.post("/patients", json={
            "full_name": full_name,
            "age": 35,
            "gender": "Female",
            "phone_number": phone,
            "address": "1 Test Street, Moscow",
            "blood_group": "A+",
            "emergency_contact": "+7 900 000-00-00",
        }, headers=headers)
        assert response.status_code == 201
        return headers, response.json()
    return _make


@pytest.fixture
def fake_ai(monkeypatch):
    """Replace the paid AI agent with a deterministic stub and record its calls."""
    from app.routes import ai

    calls = []

    async def fake_ai_runner(*, user_token, context, instructions, allowed_tools, agent_name="SIRIUS Assistant"):
        calls.append({
            "user_token": user_token, "context": context, "instructions": instructions,
            "allowed_tools": allowed_tools, "agent_name": agent_name,
        })
        return f"Ответ {len(calls)}"

    monkeypatch.setattr(ai, "ai_runner", fake_ai_runner)
    return calls
