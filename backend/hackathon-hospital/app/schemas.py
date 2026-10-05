import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, EmailStr, Field, field_validator

# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: str = Field(..., description="doctor or patient")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["doctor", "patient" ]:
            raise ValueError("Role must be one of: doctor, patient")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# --- Doctor Schemas ---
class DoctorCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    specialization: str = Field(..., min_length=2)
    qualification: str = Field(..., min_length=2)
    phone_number: str = Field(..., min_length=5)
    email: EmailStr
    consultation_fee: float = Field(..., gt=0)
    available_timings: str = Field(..., min_length=5, description="e.g. 'Mon-Fri 09:00 - 17:00'")

class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    consultation_fee: Optional[float] = None
    available_timings: Optional[str] = None

class DoctorResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    full_name: str
    specialization: str
    qualification: str
    phone_number: str
    email: str
    consultation_fee: float
    available_timings: str
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


# --- Patient Schemas ---
class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    age: int = Field(..., gt=0, lt=150)
    gender: str = Field(...)
    phone_number: str = Field(..., min_length=5)
    address: str = Field(..., min_length=5)
    blood_group: str = Field(...)
    emergency_contact: str = Field(..., min_length=5)

class PatientUpdate(BaseModel):
    user_id: Optional[int] = None
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None

class PatientResponse(BaseModel):
    id: int
    full_name: str
    age: int
    gender: str
    phone_number: str
    address: str
    blood_group: str
    emergency_contact: str
    has_photo: bool = False
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# --- Appointment Schemas ---
class AppointmentCreate(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: int
    appointment_date: datetime.date
    time_slot: str = Field(..., description="e.g. '09:00 - 09:30'")
    reason_for_visit: str = Field(..., min_length=3)

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[datetime.date] = None
    time_slot: Optional[str] = None
    reason_for_visit: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["Scheduled", "Confirmed", "Completed", "Cancelled", "No Show"]:
            raise ValueError("Status must be one of: Scheduled, Confirmed, Completed, Cancelled, No Show")
        return v

class AppointmentStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ["Scheduled", "Confirmed", "Completed", "Cancelled", "No Show"]:
            raise ValueError("Status must be one of: Scheduled, Confirmed, Completed, Cancelled, No Show")
        return v

class AppointmentResponse(BaseModel):
    id: int
    appointment_number: str
    patient_id: int
    doctor_id: int
    appointment_date: datetime.date
    time_slot: str
    reason_for_visit: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    patient: PatientResponse
    doctor: DoctorResponse

    class Config:
        from_attributes = True


# --- Prescription Schemas ---
class PrescriptionCreate(BaseModel):
    appointment_id: int
    diagnosis: str = Field(..., min_length=3)
    medicines: List[Any] = Field(..., description="List of medicines, e.g. details, name, strength, dosage")
    dosage: str = Field(...)
    instructions: str = Field(...)
    follow_up_date: Optional[datetime.date] = None

class PrescriptionUpdate(BaseModel):
    diagnosis: Optional[str] = None
    medicines: Optional[List[Any]] = None
    dosage: Optional[str] = None
    instructions: Optional[str] = None
    follow_up_date: Optional[datetime.date] = None

class PrescriptionResponse(BaseModel):
    id: int
    appointment_id: int
    doctor_id: int
    patient_id: int
    diagnosis: str
    medicines: List[Any]
    dosage: str
    instructions: str
    follow_up_date: Optional[datetime.date] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# --- Medical Record Schemas ---
class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    file_name: str
    file_path: str
    file_type: str
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True


# --- Audit Log Schemas ---
class AuditLogResponse(BaseModel):
    id: int
    appointment_id: int
    action: str
    changed_by: str
    previous_status: Optional[str] = None
    new_status: str
    timestamp: datetime.datetime

    class Config:
        from_attributes = True


# --- Report Schemas ---
class DashboardReport(BaseModel):
    total_patients: int
    total_doctors: int
    today_appointments: int
    upcoming_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    most_visited_doctor: Optional[str] = None
    average_daily_appointments: float

class AppointmentsReport(BaseModel):
    total_appointments: int
    scheduled: int
    confirmed: int
    completed: int
    cancelled: int
    no_show: int

class DoctorReportItem(BaseModel):
    doctor_id: int
    doctor_name: str
    appointment_count: int

class DoctorsReport(BaseModel):
    doctors: List[DoctorReportItem]


# --- Patient Case Schemas ---
CASE_STATUSES = ["OPEN", "AI_COLLECTING", "READY_FOR_DOCTOR", "REFERRED", "UNDER_REVIEW", "RESOLVED"]
CASE_DECISIONS = ["NEEDS_EXAMINATION", "NO_EXAMINATION_NEEDED", "REFER_TO_SPECIALIST"]

class CaseSummary(BaseModel):
    """Structured pre-consultation summary prepared by the AI assistant. Not a diagnosis."""
    chief_complaint: str = Field(..., min_length=2, description="Main complaint in the patient's words, one sentence")
    symptoms: List[str] = Field(default_factory=list, description="Each reported symptom with its character")
    onset_and_duration: Optional[str] = Field(None, description="When it started and how it changed")
    severity: Optional[str] = Field(None, description="Patient-reported severity, e.g. 6/10, impact on daily life")
    medical_history: Optional[str] = Field(None, description="Chronic conditions, surgeries, relevant past illnesses")
    current_medications: Optional[str] = Field(None, description="Medications the patient takes, including self-treatment")
    allergies: Optional[str] = Field(None, description="Known allergies or 'none reported'")
    red_flags: List[str] = Field(default_factory=list, description="Warning signs mentioned by the patient that need doctor attention")
    patient_questions: Optional[str] = Field(None, description="What the patient wants to ask or expects from the doctor")

class CaseSubmit(BaseModel):
    conversation_id: int = Field(..., description="ID of the current AI conversation")
    summary: CaseSummary
    specialization: str = Field(..., min_length=2, description="Most appropriate doctor specialization, chosen from the clinic's list")
    urgency: str = Field(..., description="low, medium or high")
    related_case_id: Optional[int] = Field(None, description="ID of the patient's earlier case when this complaint is a follow-up of it (worsening or no improvement)")

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        v = v.lower()
        if v not in ["low", "medium", "high"]:
            raise ValueError("Urgency must be one of: low, medium, high")
        return v

class CaseDecisionCreate(BaseModel):
    decision: str
    comment: Optional[str] = Field(None, max_length=4000)
    referred_doctor_id: Optional[int] = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in CASE_DECISIONS:
            raise ValueError(f"Decision must be one of: {', '.join(CASE_DECISIONS)}")
        return v

class DoctorBrief(BaseModel):
    id: int
    full_name: str
    specialization: str

    class Config:
        from_attributes = True

class PatientCaseResponse(BaseModel):
    id: int
    status: str
    complaint: str
    ai_summary: Optional[dict] = None
    specialization: Optional[str] = None
    urgency: Optional[str] = None
    decision: Optional[str] = None
    doctor_comment: Optional[str] = None
    conversation_id: Optional[int] = None
    related_case_id: Optional[int] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    submitted_at: Optional[datetime.datetime] = None
    resolved_at: Optional[datetime.datetime] = None
    patient: PatientResponse
    doctor: Optional[DoctorBrief] = None
    referred_from_doctor: Optional[DoctorBrief] = None

    class Config:
        from_attributes = True


# --- Notification Schemas ---
class NotificationResponse(BaseModel):
    id: int
    case_id: Optional[int] = None
    title: str
    message: str
    is_read: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True
