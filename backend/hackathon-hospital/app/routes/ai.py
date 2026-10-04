import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Conversation, Message, Patient, PatientCase, User
from app.routes.auth import RoleChecker, bearer_scheme, get_current_user, get_patient_profile
from app.routes.cases import COLLECTING_STATUSES, available_specializations, latest_submitted_case
from app.utils.ai_runner import ai_runner, build_intake_instructions

router = APIRouter(tags=["AI"])
logger = logging.getLogger(__name__)
MAX_CONTEXT_MESSAGES = 20
patient_only = RoleChecker(["patient"])


class CreateConversationRequest(BaseModel):
    message: str = Field(..., min_length=1)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str | None
    created_at: datetime
    case_id: int | None = None
    case_status: str | None = None
    messages: list[ChatMessageResponse]

    class Config:
        from_attributes = True


class ConversationCreatedResponse(BaseModel):
    conversation: ConversationResponse


class ConversationMessageCreatedResponse(BaseModel):
    conversation_id: int
    case_id: int | None = None
    case_status: str | None = None
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


def get_last_context_messages(db: Session, conversation_id: int) -> list[Message]:
    """Return up to 20 messages in chronological order for the agent."""
    newest_first = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(MAX_CONTEXT_MESSAGES)
        .all()
    )
    return list(reversed(newest_first))


def to_agent_messages(messages: list[Message]) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": message.content or ""}
        for message in messages
    ]


def get_owned_conversation(db: Session, conversation_id: int, user_id: int) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def get_conversation_case(db: Session, conversation_id: int) -> PatientCase | None:
    return db.query(PatientCase).filter(PatientCase.conversation_id == conversation_id).first()


def ensure_conversation_case(db: Session, conversation: Conversation, patient: Patient, complaint: str) -> PatientCase:
    """Every patient conversation is the intake of one case; create it lazily for older conversations."""
    case = get_conversation_case(db, conversation.id)
    if not case:
        case = PatientCase(
            patient_id=patient.id,
            conversation_id=conversation.id,
            complaint=complaint.strip()[:2000],
            status="OPEN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)
    return case


def build_instructions(
    db: Session, conversation_id: int, patient: Patient, case: PatientCase, is_first_message: bool = False
) -> str:
    return build_intake_instructions(
        conversation_id=conversation_id,
        specializations=available_specializations(db),
        patient_brief=f"{patient.full_name}, возраст {patient.age}, пол: {patient.gender}",
        case_status=case.status,
        is_first_message=is_first_message,
        latest_case_brief=describe_latest_case(db, patient, case),
    )


def describe_latest_case(db: Session, patient: Patient, current_case: PatientCase) -> str:
    """One-line pointer to the patient's earlier case, so its id survives between turns (tool results are not stored)."""
    latest = latest_submitted_case(db, patient.id)
    if not latest or latest.id == current_case.id:
        return "none"
    return f"case No. {latest.id}, status {latest.status}, complaint: {latest.complaint[:200]}"


def build_conversation_response(conversation: Conversation, case: PatientCase | None = None) -> ConversationResponse:
    messages = sorted(
        conversation.messages,
        key=lambda message: (message.created_at, message.id),
    )
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        case_id=case.id if case else None,
        case_status=case.status if case else None,
        messages=[
            ChatMessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content or "",
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


def get_request_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def create_assistant_message(
    db: Session,
    conversation_id: int,
    context: list[Message],
    user_token: str,
    instructions: str,
) -> Message:
    try:
        response_text = await ai_runner(
            user_token=user_token,
            context=to_agent_messages(context),
            instructions=instructions,
        )
    except Exception as exc:
        logger.exception("AI conversation response generation failed.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI response generation failed.",
        ) from exc

    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=str(response_text),
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return assistant_message


def ensure_case_accepts_messages(case: PatientCase) -> None:
    if case.status not in COLLECTING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Case #{case.id} has already been sent to a doctor. Start a new conversation for a new complaint.",
        )


@router.post(
    "/conversations",
    response_model=ConversationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    data: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(patient_only),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """Start a patient intake conversation (one conversation = one case) and return the first exchange."""
    patient = get_patient_profile(db, current_user)
    user_token = get_request_token(credentials)
    conversation = Conversation(
        user_id=current_user.id,
        title=data.message.strip()[:255],
    )
    db.add(conversation)
    db.flush()

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
    )
    db.add(user_message)
    db.commit()
    db.refresh(conversation)
    case = ensure_conversation_case(db, conversation, patient, data.message)

    context = get_last_context_messages(db, conversation.id)
    try:
        await create_assistant_message(
            db=db,
            conversation_id=conversation.id,
            context=context,
            user_token=user_token,
            instructions=build_instructions(db, conversation.id, patient, case, is_first_message=True),
        )
    except HTTPException:
        # Do not leave a half-created conversation behind, so a retry does not duplicate it.
        db.rollback()
        db.delete(case)
        db.delete(conversation)
        db.commit()
        raise

    db.expire_all()  # the agent may have submitted the case through MCP in another session
    case = get_conversation_case(db, conversation.id)
    if case and case.status == "OPEN":
        case.status = "AI_COLLECTING"
        db.commit()
    return ConversationCreatedResponse(
        conversation=build_conversation_response(conversation, case)
    )


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List conversations owned by the authenticated user, newest first."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .all()
    )
    cases = {
        case.conversation_id: case
        for case in db.query(PatientCase).filter(
            PatientCase.conversation_id.in_([conversation.id for conversation in conversations])
        )
    }
    return [build_conversation_response(conversation, cases.get(conversation.id)) for conversation in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a conversation and its messages if the user owns it."""
    conversation = get_owned_conversation(db, conversation_id, current_user.id)
    return build_conversation_response(conversation, get_conversation_case(db, conversation.id))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessageCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_conversation_message(
    conversation_id: int,
    data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(patient_only),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """Append a patient message to an intake conversation and return the assistant's reply."""
    conversation = get_owned_conversation(db, conversation_id, current_user.id)
    patient = get_patient_profile(db, current_user)
    user_token = get_request_token(credentials)
    case = ensure_conversation_case(db, conversation, patient, conversation.title or data.content)
    ensure_case_accepts_messages(case)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.content,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    context = get_last_context_messages(db, conversation.id)
    try:
        assistant_message = await create_assistant_message(
            db=db,
            conversation_id=conversation.id,
            context=context,
            user_token=user_token,
            instructions=build_instructions(db, conversation.id, patient, case, is_first_message=len(context) == 1),
        )
    except HTTPException:
        # Drop the unanswered message so the patient can resend it without duplicates.
        db.rollback()
        db.delete(user_message)
        db.commit()
        raise

    db.expire_all()  # the agent may have submitted the case through MCP in another session
    case = get_conversation_case(db, conversation.id)
    if case and case.status == "OPEN":
        case.status = "AI_COLLECTING"
        db.commit()
    return ConversationMessageCreatedResponse(
        conversation_id=conversation.id,
        case_id=case.id if case else None,
        case_status=case.status if case else None,
        user_message=user_message,
        assistant_message=assistant_message,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an owned conversation; an unsent draft case is removed, a submitted case is kept for the doctor."""
    conversation = get_owned_conversation(db, conversation_id, current_user.id)
    case = get_conversation_case(db, conversation.id)
    if case:
        if case.status in COLLECTING_STATUSES:
            db.delete(case)
        else:
            case.conversation_id = None
    db.delete(conversation)
    db.commit()
    return None


@router.post("/convert_audio_to_text")
async def convert_audio_to_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Transcribe an uploaded audio file in Russian using OpenAI Whisper."""
    if not settings.OPENAI_API_KEY:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio transcription is not configured.",
        )

    try:
        async with AsyncOpenAI(api_key=settings.OPENAI_API_KEY) as client:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=(file.filename or "audio", file.file, file.content_type),
                response_format="text",
                language="ru",
            )
    except OpenAIError as exc:
        logger.exception("OpenAI audio transcription failed.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Audio transcription failed.",
        ) from exc
    finally:
        await file.close()

    return {"text": transcription}
