from app.main import mcp
from app.utils.ai_runner import ADMIN_TOOLS, ALL_AGENT_TOOLS, DOCTOR_TOOLS, PATIENT_TOOLS
from tests.conftest import register_and_login


def test_every_agent_tool_is_exposed_through_mcp():
    exposed = {tool.name for tool in mcp.tools}
    assert set(ALL_AGENT_TOOLS) == exposed


def test_agents_only_get_their_own_tools():
    # Patients never see staff data tools; staff never get the case-submission tool.
    assert not {"list_patients", "list_doctors", "list_appointments", "get_clinic_dashboard", "get_case"} & set(PATIENT_TOOLS)
    assert "submit_patient_case" not in DOCTOR_TOOLS + ADMIN_TOOLS
    assert not {"list_patients", "get_clinic_dashboard", "get_doctors_workload"} & set(DOCTOR_TOOLS)


def test_patient_messages_go_to_patient_agent(client, make_patient, fake_ai):
    headers, _ = make_patient("role-patient@clinic.com", "9000000080")
    conversation = client.post("/conversations", json={"message": "Болит голова"}, headers=headers).json()["conversation"]
    assert conversation["case_status"] == "AI_COLLECTING"
    assert fake_ai[0]["agent_name"] == "SIRIUS Patient Assistant"
    assert fake_ai[0]["allowed_tools"] == PATIENT_TOOLS


def test_doctor_messages_go_to_doctor_agent_without_cases(client, fake_ai):
    headers = register_and_login(client, "role-doctor@clinic.com", "doctor", "Dr Role")
    created = client.post("/conversations", json={"message": "Покажи мою очередь"}, headers=headers)
    assert created.status_code == 201
    conversation = created.json()["conversation"]
    assert conversation["case_id"] is None and conversation["case_status"] is None
    assert fake_ai[0]["agent_name"] == "SIRIUS Doctor Assistant"
    assert fake_ai[0]["allowed_tools"] == DOCTOR_TOOLS
    assert "Dr Role, General Medicine" in fake_ai[0]["instructions"]

    reply = client.post(f"/conversations/{conversation['id']}/messages", json={"content": "Открой обращение 1"}, headers=headers)
    assert reply.status_code == 201
    assert reply.json()["case_id"] is None
    assert [m["role"] for m in fake_ai[1]["context"]] == ["user", "assistant", "user"]
    assert fake_ai[1]["allowed_tools"] == DOCTOR_TOOLS

    # Staff conversations never create patient cases, and are private to their owner.
    assert client.get("/cases", headers=headers).json() == []
    other = register_and_login(client, "role-doctor2@clinic.com", "doctor", "Dr Other")
    assert client.get(f"/conversations/{conversation['id']}", headers=other).status_code == 404
    assert client.post(f"/conversations/{conversation['id']}/messages", json={"content": "x"}, headers=other).status_code == 404
    assert len(fake_ai) == 2


def test_admin_messages_go_to_admin_agent(client, admin_headers, fake_ai):
    created = client.post("/conversations", json={"message": "Сводка по клинике"}, headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["conversation"]["case_id"] is None
    assert fake_ai[0]["agent_name"] == "SIRIUS Admin Assistant"
    assert fake_ai[0]["allowed_tools"] == ADMIN_TOOLS
    assert "Clinic Admin (admin@clinic.com)" in fake_ai[0]["instructions"]


def test_doctor_without_profile_is_refused_before_anything_is_stored(client, admin_headers, fake_ai):
    headers = register_and_login(client, "orphan@clinic.com", "doctor", "Dr Orphan")
    doctor_id = next(d["id"] for d in client.get("/doctors").json() if d["email"] == "orphan@clinic.com")
    assert client.delete(f"/doctors/{doctor_id}", headers=admin_headers).status_code == 204
    response = client.post("/conversations", json={"message": "Привет"}, headers=headers)
    assert response.status_code == 404
    assert client.get("/conversations", headers=headers).json() == []
    assert fake_ai == []


def test_assistant_requires_authentication(client, fake_ai):
    assert client.post("/conversations", json={"message": "Привет"}).status_code == 401
    assert fake_ai == []
