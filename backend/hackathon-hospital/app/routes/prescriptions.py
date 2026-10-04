from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Prescription, Appointment, Doctor, Patient, User
from app.schemas import PrescriptionCreate, PrescriptionResponse, PrescriptionUpdate
from app.routes.auth import RoleChecker, get_patient_profile
from app.utils.background import notify_patient_prescription_created

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

doctor_only = RoleChecker(["doctor"])
all_roles = RoleChecker(["admin", "doctor", "patient"])

@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    prescription_in: PrescriptionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """Create a prescription for an appointment assigned to the signed-in doctor and mark it completed."""
    # Find doctor profile from user
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for current user"
        )
        
    # Check if appointment exists
    appt = db.query(Appointment).filter(Appointment.id == prescription_in.appointment_id).first()
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
        
    # Check if the doctor is assigned to this appointment
    if appt.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create a prescription for this appointment"
        )
        
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
        
    # Create prescription
    new_prescription = Prescription(
        appointment_id=appt.id,
        doctor_id=doctor.id,
        patient_id=patient.id,
        diagnosis=prescription_in.diagnosis,
        medicines=prescription_in.medicines,
        dosage=prescription_in.dosage,
        instructions=prescription_in.instructions,
        follow_up_date=prescription_in.follow_up_date
    )
    db.add(new_prescription)
    
    # Automatically complete the appointment
    appt.status = "Completed"
    
    db.commit()
    db.refresh(new_prescription)
    
    # Background Notification
    if patient.user:
        background_tasks.add_task(
            notify_patient_prescription_created,
            patient_email=patient.user.email,
            patient_name=patient.full_name,
            diagnosis=new_prescription.diagnosis,
            doctor_name=doctor.full_name
        )
    
    return new_prescription

@router.get("", response_model=List[PrescriptionResponse])
def get_prescriptions(
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    appointment_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """List prescriptions with optional filters; doctors and patients are limited to their own records."""
    query = db.query(Prescription)
    
    # Apply filters
    if patient_id:
        query = query.filter(Prescription.patient_id == patient_id)
    if doctor_id:
        query = query.filter(Prescription.doctor_id == doctor_id)
    if appointment_id:
        query = query.filter(Prescription.appointment_id == appointment_id)
        
    # Doctor role restriction
    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        # Doctors can only see their own prescriptions
        query = query.filter(Prescription.doctor_id == doctor.id)
    elif current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        query = query.filter(Prescription.patient_id == patient.id)
        
    return query.offset(skip).limit(limit).all()

@router.get("/{id}", response_model=PrescriptionResponse)
def get_prescription_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """Return a prescription visible to the signed-in user under their role's ownership rules."""
    prescription = db.query(Prescription).filter(Prescription.id == id).first()
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
        
    # Doctor role restriction
    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or prescription.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to view other doctor's prescriptions"
            )
    elif current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        if prescription.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's prescription")
            
    return prescription

@router.put("/{id}", response_model=PrescriptionResponse)
def update_prescription(
    id: int,
    prescription_update: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """Update a prescription created by the signed-in doctor."""
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
        
    prescription = db.query(Prescription).filter(Prescription.id == id).first()
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
        
    # Verify owner
    if prescription.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this prescription"
        )
        
    # Update fields
    update_data = prescription_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prescription, key, value)
        
    db.commit()
    db.refresh(prescription)
    return prescription
