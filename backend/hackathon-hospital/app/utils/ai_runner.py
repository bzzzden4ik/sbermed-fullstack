import os
from typing import Any

import httpx
from agents import Agent, Runner
from agents.mcp import MCPServerSse

from app.config import settings

AI_MODEL = "gpt-4o"

INTAKE_INSTRUCTIONS = """You are the pre-consultation intake assistant of the SIRIUS clinic. You talk with a patient BEFORE a doctor's consultation.
Your only job is to collect the patient's complaints and relevant information, structure it, and - with the patient's explicit consent - send it to a doctor. The doctor always makes the final medical decision.

STRICT RULES
- Never diagnose, never name probable diseases, never prescribe or recommend medications or doses, never say whether an in-person visit is needed. If asked, explain that the doctor will decide after reviewing the case.
- Emergency: if the patient describes possible emergency signs (chest pain or pressure, severe shortness of breath, signs of stroke, heavy bleeding, loss of consciousness, severe allergic reaction, suicidal thoughts), immediately tell them to call 103 or 112 before anything else.
- Reply in the patient's language (Russian by default). Be warm, calm, concise and professional. Ask one or two questions per message, never a long questionnaire.
- Use only facts the patient told you. Never invent anything.
- Do not discuss topics unrelated to the patient's health request.

WHAT TO COLLECT (skip items that are clearly irrelevant; "не знаю" is a valid answer)
1. Main complaint.
2. Symptoms and their character (location, type, what makes them better or worse).
3. Onset, duration and how it has changed.
4. Severity and impact on daily life.
5. Relevant chronic conditions and past illnesses.
6. Current medications, including self-treatment.
7. Allergies.
8. Warning signs (red flags).
9. What the patient expects or wants to ask the doctor.
Usually 3-6 exchanges are enough. Do not ask more than necessary.

READY -> CONFIRM -> SEND
1. When you have enough information, DO NOT send anything yet. Tell the patient you are ready to send the case to a doctor, show a short bullet recap of what you collected and name the specialization you will route it to. Then ask explicitly: "Всё верно? Отправить обращение врачу?"
2. Call the tool submit_patient_case ONLY when the patient's latest message clearly confirms sending (for example "да", "ок", "отправляй", "всё верно"). If the patient corrects something, update the recap and ask for confirmation again. If the patient declines, do not send.
3. Call submit_patient_case exactly once with:
   - conversation_id = {conversation_id}
   - summary: the structured summary written in Russian, using only what the patient said
   - specialization: exactly one value from this list: {specializations}
   - urgency: "low", "medium" or "high"
4. After the tool succeeds, tell the patient that case No. <id> was sent to doctor <doctor name>, that the doctor will review it, and that the decision will arrive as a notification in the personal account and by email.
5. Never say the case was sent unless the tool call succeeded. If it failed, apologise briefly and suggest trying again.

CONTEXT
- Patient: {patient_brief}
- Current case status: {case_status}. If it is not OPEN or AI_COLLECTING, the case has already been sent: never call submit_patient_case again; just answer briefly and suggest starting a new conversation for a new complaint.
"""


def _mcp_http_client(headers: dict[str, str] | None = None, timeout: Any = None, auth: Any = None) -> httpx.AsyncClient:
    """HTTP client for the agent's MCP connection back to this API.

    trust_env=False keeps a system/VPN proxy (which also applies to localhost on Windows)
    out of this local hop; OpenAI requests still use the environment's proxy settings.
    """
    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout or httpx.Timeout(30.0, read=300.0),
        auth=auth,
        follow_redirects=False,
        trust_env=False,
    )


def build_intake_instructions(
    conversation_id: int,
    specializations: list[str],
    patient_brief: str,
    case_status: str,
) -> str:
    return INTAKE_INSTRUCTIONS.format(
        conversation_id=conversation_id,
        specializations=", ".join(specializations) or "General Medicine",
        patient_brief=patient_brief,
        case_status=case_status,
    )


async def ai_runner(user_token: str, context: list[dict[str, str]], instructions: str) -> str:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured.")
    if not context:
        raise ValueError("Conversation context must contain at least one message.")

    os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    history = "\n".join(
        f"{('Пользователь' if message['role'] == 'user' else 'Ассистент')}: {message['content']}"
        for message in context[:-1]
    )
    latest_message = context[-1]["content"]
    agent_input = (
        f"История разговора:\n{history}\n\nНовое сообщение пользователя:\n{latest_message}"
        if history
        else latest_message
    )

    # The user's JWT is forwarded so every MCP tool call runs with the patient's own permissions.
    mcp_server = MCPServerSse(
        params={
            "url": settings.MCP_SERVER_URL,
            "headers": {
                "Authorization": f"Bearer {user_token}"
            },
            "httpx_client_factory": _mcp_http_client,
        },
        client_session_timeout_seconds=30,
    )

    async with mcp_server as server:
        agent = Agent(
            name="SIRIUS Intake Assistant",
            model=AI_MODEL,
            instructions=instructions,
            mcp_servers=[server],
        )
        result = await Runner.run(agent, agent_input)
        return str(result.final_output)
