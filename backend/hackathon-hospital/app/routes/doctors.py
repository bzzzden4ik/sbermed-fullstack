import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from app.config import settings
from app.database import get_db
from app.models import Appointment, Doctor, PatientCase, Prescription, User
from app.schemas import DoctorCreate, DoctorResponse, DoctorUpdate
from app.routes.auth import RoleChecker, get_current_user
from app.security import get_password_hash
from app.utils.images import read_validated_photo

router = APIRouter(prefix="/doctors", tags=["Doctors"])

# Role checkers
admin_only = RoleChecker(["admin"])

PHOTO_DIR = os.path.join(settings.UPLOAD_DIR, "doctors")


def remove_photo_file(photo_url: Optional[str]) -> None:
    """Delete a stored doctor photo; only files inside the doctors photo folder are ever touched."""
    if not photo_url:
        return
    path = os.path.join(PHOTO_DIR, os.path.basename(photo_url))
    if os.path.isfile(path):
        os.remove(path)

@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    doctor_in: DoctorCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Create a doctor profile and, when needed, its linked doctor account; admin access is required."""
    # Check if doctor email already exists
    existing_doc = db.query(Doctor).filter(Doctor.email == doctor_in.email).first()
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor email already registered"
        )
        
    # Check if user account exists, if not create one
    user = db.query(User).filter(User.email == doctor_in.email).first()
    if not user:
        hashed_password = get_password_hash("doctor123")  # Default password
        user = User(
            email=doctor_in.email,
            password_hash=hashed_password,
            full_name=doctor_in.full_name,
            role="doctor"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    new_doc = Doctor(
        user_id=user.id,
        full_name=doctor_in.full_name,
        specialization=doctor_in.specialization,
        qualification=doctor_in.qualification,
        phone_number=doctor_in.phone_number,
        email=doctor_in.email,
        consultation_fee=doctor_in.consultation_fee,
        available_timings=doctor_in.available_timings
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc

@router.get("", response_model=List[DoctorResponse], operation_id="list_doctors")
def get_doctors(
    specialization: Optional[str] = None,
    name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "id",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    """List doctor profiles with optional name or specialization filters, sorting, and pagination."""
    query = db.query(Doctor)
    
    # Search/Filters
    if name:
        query = query.filter(Doctor.full_name.ilike(f"%{name}%"))
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        
    # Sorting
    if sort_by in ["id", "full_name", "specialization", "consultation_fee"]:
        field = getattr(Doctor, sort_by)
        if order.lower() == "desc":
            query = query.order_by(field.desc())
        else:
            query = query.order_by(field.asc())
    else:
        query = query.order_by(Doctor.id.asc())
        
    # Pagination
    return query.offset(skip).limit(limit).all()

@router.get("/{id}", response_model=DoctorResponse)
def get_doctor_by_id(id: int, db: Session = Depends(get_db)):
    """Return the public profile for the requested doctor."""
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    return doctor

@router.put("/{id}", response_model=DoctorResponse)
def update_doctor(
    id: int, 
    doctor_update: DoctorUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Update a doctor's profile fields; admin access is required."""
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
        
    # Apply updates
    update_data = doctor_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doctor, key, value)
        
    db.commit()
    db.refresh(doctor)
    return doctor

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Delete a doctor profile with no medical history; admin access is required.

    Appointments and prescriptions require a doctor, and open cases still need one to decide,
    so a doctor who has any of them cannot be deleted (409) and patients never lose records.
    """
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    blockers = {
        "appointments": db.query(Appointment).filter(Appointment.doctor_id == doctor.id).count(),
        "prescriptions": db.query(Prescription).filter(Prescription.doctor_id == doctor.id).count(),
        "open patient cases": db.query(PatientCase).filter(
            PatientCase.doctor_id == doctor.id,
            PatientCase.status.in_(["READY_FOR_DOCTOR", "REFERRED", "UNDER_REVIEW"]),
        ).count(),
    }
    found = [f"{count} {name}" for name, count in blockers.items() if count]
    if found:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Doctor {doctor.full_name} cannot be deleted: they have {', '.join(found)}. "
                   "Patient medical history must be kept.",
        )

    # Finished cases stay with the patient; only the link to the removed doctor is cleared.
    db.query(PatientCase).filter(PatientCase.doctor_id == doctor.id).update({PatientCase.doctor_id: None}, synchronize_session=False)
    db.query(PatientCase).filter(PatientCase.referred_from_doctor_id == doctor.id).update(
        {PatientCase.referred_from_doctor_id: None}, synchronize_session=False
    )

    photo_url = doctor.photo_url
    db.delete(doctor)
    db.commit()
    remove_photo_file(photo_url)
    return None


@router.post("/{id}/photo", response_model=DoctorResponse)
def upload_doctor_photo(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Upload or replace a doctor's photo (JPEG, PNG or WebP, up to 5 MB); admin access is required."""
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    content, ext = read_validated_photo(file)

    os.makedirs(PHOTO_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    try:
        with open(os.path.join(PHOTO_DIR, filename), "wb") as f:
            f.write(content)
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save photo: {e}")

    old_photo = doctor.photo_url
    doctor.photo_url = f"/{settings.UPLOAD_DIR}/doctors/{filename}"
    db.commit()
    db.refresh(doctor)
    remove_photo_file(old_photo)
    return doctor


@router.delete("/{id}/photo", response_model=DoctorResponse)
def delete_doctor_photo(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Remove a doctor's photo; admin access is required."""
    doctor = db.query(Doctor).filter(Doctor.id == id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    old_photo = doctor.photo_url
    doctor.photo_url = None
    db.commit()
    db.refresh(doctor)
    remove_photo_file(old_photo)
    return doctor
