import datetime
import random
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Appointment, Patient, Doctor, AuditLog, User
from app.schemas import AppointmentCreate, AppointmentResponse, AppointmentUpdate, AppointmentStatusUpdate
from app.routes.auth import RoleChecker, get_patient_profile
from app.utils.background import send_appointment_confirmation_email, send_appointment_reminder_email
from app.utils.csv_export import export_appointments_to_csv

router = APIRouter(prefix="/appointments", tags=["Appointments"])

# Role checkers
admin_or_patient = RoleChecker(["admin", "patient"])
all_roles = RoleChecker(["admin", "doctor", "patient"])
admin_only = RoleChecker(["admin"])

def generate_appointment_number() -> str:
    today_str = datetime.date.today().strftime("%Y%m%d")
    rand_num = random.randint(1000, 9999)
    return f"APT-{today_str}-{rand_num}"

def check_double_booking(doctor_id: int, date: datetime.date, time_slot: str, db: Session, exclude_appt_id: Optional[int] = None) -> bool:
    """
    Returns True if a double booking is detected.
    Double booking occurs if the same doctor has an active appointment (Scheduled/Confirmed/Completed)
    at the same date and time slot.
    """
    query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == date,
        Appointment.time_slot == time_slot,
        Appointment.status.in_(["Scheduled", "Confirmed", "Completed"])
    )
    if exclude_appt_id:
        query = query.filter(Appointment.id != exclude_appt_id)
        
    return query.first() is not None

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    appt_in: AppointmentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_patient)
):
    """Book an appointment; patients book for themselves and admins may book for any patient."""
    if current_user.role == "patient":
        patient_profile = get_patient_profile(db, current_user)
        if appt_in.patient_id is not None and appt_in.patient_id != patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients can only book appointments for themselves")
        patient_id = patient_profile.id
    else:
        if appt_in.patient_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="patient_id is required")
        patient_id = appt_in.patient_id

    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
        
    # Check if doctor exists
    doctor = db.query(Doctor).filter(Doctor.id == appt_in.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
        
    # Check for double booking
    if check_double_booking(appt_in.doctor_id, appt_in.appointment_date, appt_in.time_slot, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Double booking: Dr. {doctor.full_name} is already booked for {appt_in.appointment_date} at {appt_in.time_slot}"
        )
        
    # Generate unique appointment number
    appt_num = generate_appointment_number()
    while db.query(Appointment).filter(Appointment.appointment_number == appt_num).first() is not None:
        appt_num = generate_appointment_number()
        
    new_appt = Appointment(
        appointment_number=appt_num,
        patient_id=patient_id,
        doctor_id=appt_in.doctor_id,
        appointment_date=appt_in.appointment_date,
        time_slot=appt_in.time_slot,
        reason_for_visit=appt_in.reason_for_visit,
        status="Scheduled"
    )
    
    db.add(new_appt)
    db.commit()
    db.refresh(new_appt)
    
    # Write Audit Log
    log = AuditLog(
        appointment_id=new_appt.id,
        action="Booked",
        changed_by=f"{current_user.role}: {current_user.full_name}",
        previous_status=None,
        new_status="Scheduled"
    )
    db.add(log)
    db.commit()
    
    # Background Tasks
    if patient.user:
        patient_email = patient.user.email
        background_tasks.add_task(
            send_appointment_confirmation_email,
            patient_email=patient_email,
            patient_name=patient.full_name,
            appointment_number=new_appt.appointment_number,
            appointment_date=new_appt.appointment_date,
            time_slot=new_appt.time_slot,
            doctor_name=doctor.full_name,
            reason_for_visit=new_appt.reason_for_visit,
            doctor_specialization=doctor.specialization,
            doctor_qualification=doctor.qualification,
            consultation_fee=doctor.consultation_fee
        )
        
        background_tasks.add_task(
            send_appointment_reminder_email,
            patient_email=patient_email,
            patient_name=patient.full_name,
            appointment_number=new_appt.appointment_number,
            appointment_date=new_appt.appointment_date,
            time_slot=new_appt.time_slot,
            doctor_name=doctor.full_name,
            reason_for_visit=new_appt.reason_for_visit,
            doctor_specialization=doctor.specialization,
            doctor_qualification=doctor.qualification,
            consultation_fee=doctor.consultation_fee
        )
    
    return new_appt

# Support search and filtering of appointments
def get_filtered_appointments_query(
    patient_name: Optional[str] = None,
    doctor_name: Optional[str] = None,
    appointment_number: Optional[str] = None,
    status: Optional[str] = None,
    appointment_date: Optional[datetime.date] = None,
    specialization: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Appointment).join(Patient).join(Doctor)
    
    if patient_name:
        query = query.filter(Patient.full_name.ilike(f"%{patient_name}%"))
    if doctor_name:
        query = query.filter(Doctor.full_name.ilike(f"%{doctor_name}%"))
    if appointment_number:
        query = query.filter(Appointment.appointment_number.ilike(f"%{appointment_number}%"))
    if status:
        query = query.filter(Appointment.status.ilike(f"%{status}%"))
    if appointment_date:
        query = query.filter(Appointment.appointment_date == appointment_date)
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        
    return query

@router.get("/export/csv")
def export_csv(
    patient_name: Optional[str] = None,
    doctor_name: Optional[str] = None,
    appointment_number: Optional[str] = None,
    status: Optional[str] = None,
    appointment_date: Optional[datetime.date] = None,
    specialization: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """Export filtered appointments as CSV, scoped to the signed-in doctor's or patient's own records."""
    query = get_filtered_appointments_query(
        patient_name=patient_name,
        doctor_name=doctor_name,
        appointment_number=appointment_number,
        status=status,
        appointment_date=appointment_date,
        specialization=specialization,
        db=db
    )
    
    # If role is doctor, only return their own appointments
    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        query = query.filter(Appointment.doctor_id == doctor.id if doctor else -1)
    elif current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        query = query.filter(Appointment.patient_id == patient.id)
        
    appointments = query.all()
    csv_content = export_appointments_to_csv(appointments)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=appointments.csv"}
    )

@router.get("", response_model=List[AppointmentResponse])
def get_appointments(
    patient_name: Optional[str] = None,
    doctor_name: Optional[str] = None,
    appointment_number: Optional[str] = None,
    status: Optional[str] = None,
    appointment_date: Optional[datetime.date] = None,
    specialization: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "appointment_date",
    order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """List and filter appointments; doctors and patients see only their own records."""
    query = get_filtered_appointments_query(
        patient_name=patient_name,
        doctor_name=doctor_name,
        appointment_number=appointment_number,
        status=status,
        appointment_date=appointment_date,
        specialization=specialization,
        db=db
    )
    
    # Role-based restriction: Doctor can only see their own appointments
    if current_user.role == "doctor":
        # Find doctor profile
        doc = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
        query = query.filter(Appointment.doctor_id == doc.id)
    elif current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        query = query.filter(Appointment.patient_id == patient.id)
        
    # Sorting
    if sort_by in ["id", "appointment_date", "status", "appointment_number"]:
        field = getattr(Appointment, sort_by)
        if order.lower() == "desc":
            query = query.order_by(field.desc())
        else:
            query = query.order_by(field.asc())
    else:
        query = query.order_by(Appointment.appointment_date.asc())
        
    # Pagination
    return query.offset(skip).limit(limit).all()

@router.get("/{id}", response_model=AppointmentResponse)
def get_appointment_by_id(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """Return an appointment visible to the signed-in user under their role's ownership rules."""
    appt = db.query(Appointment).filter(Appointment.id == id).first()
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
        
    # Doctor restriction
    if current_user.role == "doctor":
        doc = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc or appt.doctor_id != doc.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to other doctors' appointments"
            )
    elif current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        if appt.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's appointment")
            
    return appt

@router.put("/{id}", response_model=AppointmentResponse)
def update_appointment(
    id: int,
    appt_update: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """Update or reschedule an appointment; doctors may update their own status and patients may manage their own appointment."""
    appt = db.query(Appointment).filter(Appointment.id == id).first()
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
        
    # Authorization check
    if current_user.role == "doctor":
        # Doctor can only update status of their own appointments
        doc = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doc or appt.doctor_id != doc.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to modify other doctors' appointments"
            )
        # Doctor can only update status
        update_dict = appt_update.model_dump(exclude_unset=True)
        if any(k != "status" for k in update_dict.keys()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors are only allowed to update the appointment status"
            )
            
    elif current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        if appt.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to modify another patient's appointment")
        update_dict = appt_update.model_dump(exclude_unset=True)
        if "status" in update_dict and update_dict["status"] == "Completed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients cannot complete appointments. Only doctors can do so"
            )
            
    # Business logic updates
    previous_status = appt.status
    update_data = appt_update.model_dump(exclude_unset=True)
    
    # Check double booking if date/time slot is modified
    if "appointment_date" in update_data or "time_slot" in update_data:
        new_date = update_data.get("appointment_date", appt.appointment_date)
        new_slot = update_data.get("time_slot", appt.time_slot)
        if check_double_booking(appt.doctor_id, new_date, new_slot, db, exclude_appt_id=appt.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Double booking: Doctor is already booked for this date and time slot"
            )
            
    # Apply changes
    for key, value in update_data.items():
        setattr(appt, key, value)
        
    db.commit()
    db.refresh(appt)
    
    # Write Audit Log
    action = "Status Updated"
    if "appointment_date" in update_data or "time_slot" in update_data:
        action = "Rescheduled"
    elif "status" in update_data:
        if update_data["status"] == "Cancelled":
            action = "Cancelled"
        elif update_data["status"] == "Completed":
            action = "Completed"
            
    log = AuditLog(
        appointment_id=appt.id,
        action=action,
        changed_by=f"{current_user.role}: {current_user.full_name}",
        previous_status=previous_status,
        new_status=appt.status
    )
    db.add(log)
    db.commit()
    
    return appt

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Permanently delete an appointment; admin access is required."""
    appt = db.query(Appointment).filter(Appointment.id == id).first()
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    db.delete(appt)
    db.commit()
    return None
