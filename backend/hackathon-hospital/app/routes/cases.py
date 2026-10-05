import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import PatientCase, Conversation, Doctor, Notification, User
from app.schemas import CaseSubmit, CaseDecisionCreate, PatientCaseResponse, CASE_STATUSES
from app.routes.auth import RoleChecker, get_patient_profile, get_doctor_profile
from app.utils.background import send_case_decision_email, CASE_DECISION_TEXT

router = APIRouter(prefix="/cases", tags=["Patient Cases"])

# Role checkers
patient_only = RoleChecker(["patient"])
doctor_only = RoleChecker(["doctor"])
all_roles = RoleChecker(["admin", "doctor", "patient"])

COLLECTING_STATUSES = ["OPEN", "AI_COLLECTING"]
DECIDABLE_STATUSES = ["READY_FOR_DOCTOR", "REFERRED", "UNDER_REVIEW"]
# General practice, used when no doctor of the requested specialization exists.
FALLBACK_SPECIALIZATIONS = ("General Medicine", "Терапия")


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def notify(db: Session, user_id: Optional[int], case_id: int, title: str, message: str) -> None:
    """Queue an in-app notification; committed together with the caller's changes."""
    if user_id is None:
        return
    db.add(Notification(user_id=user_id, case_id=case_id, title=title, message=message))


def available_specializations(db: Session) -> list[str]:
    """Specializations of doctors that have an account and can review cases."""
    rows = (
        db.query(Doctor.specialization)
        .filter(Doctor.user_id.isnot(None))
        .distinct()
        .order_by(Doctor.specialization)
        .all()
    )
    return [row[0] for row in rows]


def assign_doctor(db: Session, specialization: str) -> Optional[Doctor]:
    """Pick the least-loaded doctor for the specialization, falling back to general medicine, then anyone."""
    open_cases = (
        db.query(PatientCase.doctor_id, func.count(PatientCase.id).label("load"))
        .filter(PatientCase.status.in_(DECIDABLE_STATUSES))
        .group_by(PatientCase.doctor_id)
        .subquery()
    )
    base = (
        db.query(Doctor)
        .outerjoin(open_cases, open_cases.c.doctor_id == Doctor.id)
        .filter(Doctor.user_id.isnot(None))
        .order_by(func.coalesce(open_cases.c.load, 0).asc(), Doctor.id.asc())
    )
    for spec in (specialization, *FALLBACK_SPECIALIZATIONS):
        spec = spec.strip()
        # Exact match too: SQLite's lower() only folds ASCII, so Cyrillic names need it.
        doctor = base.filter(or_(Doctor.specialization == spec, func.lower(Doctor.specialization) == spec.lower())).first()
        if doctor:
            return doctor
    return base.first()


def latest_submitted_case(db: Session, patient_id: int) -> Optional[PatientCase]:
    """The patient's most recently sent case (drafts still being collected are ignored)."""
    return (
        db.query(PatientCase)
        .filter(PatientCase.patient_id == patient_id, PatientCase.status.notin_(COLLECTING_STATUSES))
        .order_by(PatientCase.submitted_at.desc(), PatientCase.id.desc())
        .first()
    )


def get_case_for_user(db: Session, case_id: int, current_user: User) -> PatientCase:
    """Load a case and enforce role-based access: patients own cases, doctors assigned or referring cases."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        if case.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's case")
    elif current_user.role == "doctor":
        doctor = get_doctor_profile(db, current_user)
        involved = doctor.id in (case.doctor_id, case.referred_from_doctor_id)
        # Read access to the earlier case when this doctor handles its follow-up.
        follow_up_of_mine = db.query(PatientCase).filter(
            PatientCase.related_case_id == case.id,
            PatientCase.doctor_id == doctor.id,
            PatientCase.status.notin_(COLLECTING_STATUSES),
        ).first() is not None
        if case.status in COLLECTING_STATUSES or not (involved or follow_up_of_mine):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to cases of other doctors")
    return case


@router.get("", response_model=List[PatientCaseResponse], operation_id="list_my_cases")
def list_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """List patient cases: patients see their own, doctors see cases assigned to them, admins see all."""
    query = db.query(PatientCase)

    if current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        query = query.filter(PatientCase.patient_id == patient.id)
    elif current_user.role == "doctor":
        doctor = get_doctor_profile(db, current_user)
        query = query.filter(
            PatientCase.status.notin_(COLLECTING_STATUSES),
            (PatientCase.doctor_id == doctor.id) | (PatientCase.referred_from_doctor_id == doctor.id),
        )

    if status_filter:
        if status_filter not in CASE_STATUSES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status must be one of: {', '.join(CASE_STATUSES)}")
        query = query.filter(PatientCase.status == status_filter)

    return query.order_by(PatientCase.updated_at.desc(), PatientCase.id.desc()).offset(skip).limit(limit).all()


@router.get("/latest", response_model=Optional[PatientCaseResponse], operation_id="get_my_latest_case")
def get_latest_case(
    db: Session = Depends(get_db),
    current_user: User = Depends(patient_only)
):
    """Return the patient's most recently submitted case: complaint, AI summary, status,
    the doctor's decision and comment. Returns null if the patient has never sent a case."""
    patient = get_patient_profile(db, current_user)
    return latest_submitted_case(db, patient.id)


@router.get("/specializations", response_model=List[str])
def list_specializations(db: Session = Depends(get_db)):
    """Return the specializations of doctors who can review cases."""
    return available_specializations(db)


@router.get("/{id}", response_model=PatientCaseResponse, operation_id="get_case")
def get_case(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """Return a single case if the signed-in user may access it."""
    return get_case_for_user(db, id, current_user)


@router.post("/submit", response_model=PatientCaseResponse, status_code=status.HTTP_201_CREATED, operation_id="submit_patient_case")
def submit_case(
    case_in: CaseSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(patient_only)
):
    """Send the patient's collected complaint and structured AI summary to a doctor.
    Call only after the patient explicitly confirmed the recap. Returns the case with the assigned doctor."""
    patient = get_patient_profile(db, current_user)
    conversation = db.query(Conversation).filter(
        Conversation.id == case_in.conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if case_in.related_case_id is not None:
        related = db.query(PatientCase).filter(
            PatientCase.id == case_in.related_case_id,
            PatientCase.patient_id == patient.id,
            PatientCase.status.notin_(COLLECTING_STATUSES),
        ).first()
        if not related:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Related case not found")

    case = db.query(PatientCase).filter(PatientCase.conversation_id == conversation.id).first()
    if case and case.status not in COLLECTING_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case #{case.id} has already been sent to a doctor")
    if not case:
        case = PatientCase(patient_id=patient.id, conversation_id=conversation.id, complaint=case_in.summary.chief_complaint)
        db.add(case)

    doctor = assign_doctor(db, case_in.specialization)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No doctors are available to review the case")

    case.complaint = case_in.summary.chief_complaint
    case.ai_summary = case_in.summary.model_dump()
    case.specialization = case_in.specialization
    case.urgency = case_in.urgency
    case.related_case_id = case_in.related_case_id
    case.doctor_id = doctor.id
    case.status = "READY_FOR_DOCTOR"
    case.submitted_at = _utc_now()
    db.flush()

    follow_up = f" (повторное по обращению №{case.related_case_id})" if case.related_case_id else ""
    notify(db, doctor.user_id, case.id, "Новое обращение пациента",
           f"Обращение №{case.id}{follow_up} от {patient.full_name}: {case.complaint}")
    db.commit()
    db.refresh(case)
    return case


@router.post("/{id}/review", response_model=PatientCaseResponse)
def start_review(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """Mark an assigned case as under review by the signed-in doctor."""
    case = get_case_for_user(db, id, current_user)
    doctor = get_doctor_profile(db, current_user)
    if case.doctor_id != doctor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned doctor can review this case")
    if case.status in ("READY_FOR_DOCTOR", "REFERRED"):
        case.status = "UNDER_REVIEW"
        db.commit()
        db.refresh(case)
    elif case.status != "UNDER_REVIEW":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case in status {case.status} cannot be reviewed")
    return case


@router.post("/{id}/decision", response_model=PatientCaseResponse)
def make_decision(
    id: int,
    decision_in: CaseDecisionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """Save the assigned doctor's final decision, notify the patient in-app and by email."""
    case = get_case_for_user(db, id, current_user)
    doctor = get_doctor_profile(db, current_user)
    if case.doctor_id != doctor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned doctor can decide on this case")
    if case.status not in DECIDABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case in status {case.status} cannot be decided")

    referred_doctor = None
    if decision_in.decision == "REFER_TO_SPECIALIST":
        if decision_in.referred_doctor_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="referred_doctor_id is required for a referral")
        if decision_in.referred_doctor_id == doctor.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot refer a case to yourself")
        referred_doctor = db.query(Doctor).filter(Doctor.id == decision_in.referred_doctor_id, Doctor.user_id.isnot(None)).first()
        if not referred_doctor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referred doctor not found")

        case.referred_from_doctor_id = doctor.id
        case.doctor_id = referred_doctor.id
        case.status = "REFERRED"
        notify(db, referred_doctor.user_id, case.id, "Обращение передано вам",
               f"Врач {doctor.full_name} направил вам обращение №{case.id}: {case.complaint}")
    else:
        case.status = "RESOLVED"
        case.resolved_at = _utc_now()

    case.decision = decision_in.decision
    case.doctor_comment = decision_in.comment

    patient = case.patient
    title, explanation = CASE_DECISION_TEXT[decision_in.decision]
    message = explanation
    if referred_doctor:
        message += f" Специалист: {referred_doctor.full_name} ({referred_doctor.specialization})."
    if decision_in.comment:
        message += f" Комментарий врача: {decision_in.comment}"
    notify(db, patient.user_id, case.id, f"Обращение №{case.id}: {title}", message)
    db.commit()
    db.refresh(case)

    if patient.user:
        background_tasks.add_task(
            send_case_decision_email,
            patient_email=patient.user.email,
            patient_name=patient.full_name,
            case_id=case.id,
            decision=case.decision,
            doctor_name=doctor.full_name,
            doctor_comment=case.doctor_comment,
            referred_doctor_name=f"{referred_doctor.full_name} ({referred_doctor.specialization})" if referred_doctor else None,
        )
    return case
