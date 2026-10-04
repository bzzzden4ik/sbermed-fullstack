import datetime
from time import timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50))  # admin, doctor, patient
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    doctor_profile: Mapped[Optional["Doctor"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    patient_profile: Mapped[Optional["Patient"]] = relationship(back_populates="user")
    conversations: Mapped[List["Conversation"]] = relationship(
    back_populates="user",
    cascade="all, delete-orphan",
)
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Doctor(Base):
    __tablename__ = "doctors"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    specialization: Mapped[str] = mapped_column(String(255))
    qualification: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    consultation_fee: Mapped[float] = mapped_column(Float)
    available_timings: Mapped[str] = mapped_column(String(255))  # e.g. "Mon-Fri 09:00 - 17:00"

    user: Mapped[Optional["User"]] = relationship(back_populates="doctor_profile")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="doctor")
    prescriptions: Mapped[List["Prescription"]] = relationship(back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(50))
    phone_number: Mapped[str] = mapped_column(String(50))
    address: Mapped[str] = mapped_column(String(500))
    blood_group: Mapped[str] = mapped_column(String(20))
    emergency_contact: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    user: Mapped[Optional["User"]] = relationship(back_populates="patient_profile")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="patient", cascade="all, delete")
    prescriptions: Mapped[List["Prescription"]] = relationship(back_populates="patient", cascade="all, delete")
    medical_records: Mapped[List["MedicalRecord"]] = relationship(back_populates="patient", cascade="all, delete")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    appointment_date: Mapped[datetime.date] = mapped_column(Date)
    time_slot: Mapped[str] = mapped_column(String(100))
    reason_for_visit: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="Scheduled")  # Scheduled, Confirmed, Completed, Cancelled, No Show
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")
    prescription: Mapped[Optional["Prescription"]] = relationship(back_populates="appointment")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="appointment", cascade="all, delete")

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    diagnosis: Mapped[str] = mapped_column(String(500))
    medicines: Mapped[list] = mapped_column(JSON)  # list of dicts/strings
    dosage: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(String(500))
    follow_up_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    appointment: Mapped["Appointment"] = relationship(back_populates="prescription")
    doctor: Mapped["Doctor"] = relationship(back_populates="prescriptions")
    patient: Mapped["Patient"] = relationship(back_populates="prescriptions")

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, jpg, png
    uploaded_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    patient: Mapped["Patient"] = relationship(back_populates="medical_records")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(100))  # Booked, Rescheduled, Cancelled, Completed, Status Updated
    changed_by: Mapped[str] = mapped_column(String(255))  # user role + name
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    appointment: Mapped["Appointment"] = relationship(back_populates="audit_logs")




class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="conversations",
    )

    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
    )


class PatientCase(Base):
    """Patient complaint collected by the AI assistant and decided by a doctor."""
    __tablename__ = "patient_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, index=True)
    referred_from_doctor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), unique=True, nullable=True)
    complaint: Mapped[str] = mapped_column(Text)
    ai_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # low, medium, high
    status: Mapped[str] = mapped_column(String(50), default="OPEN", index=True)  # OPEN, AI_COLLECTING, READY_FOR_DOCTOR, REFERRED, UNDER_REVIEW, RESOLVED
    decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # NEEDS_EXAMINATION, NO_EXAMINATION_NEEDED, REFER_TO_SPECIALIST
    doctor_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)
    submitted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship()
    doctor: Mapped[Optional["Doctor"]] = relationship(foreign_keys=[doctor_id])
    referred_from_doctor: Mapped[Optional["Doctor"]] = relationship(foreign_keys=[referred_from_doctor_id])


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patient_cases.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    user: Mapped["User"] = relationship(back_populates="notifications")