import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.config import settings
from app.database import get_db
from app.models import MedicalRecord, Patient, User
from app.schemas import MedicalRecordResponse
from app.routes.auth import RoleChecker, get_patient_profile

router = APIRouter(prefix="/medical-records", tags=["Medical Records"])

# Role permissions
admin_or_patient = RoleChecker(["admin", "patient"])
all_roles = RoleChecker(["admin", "doctor", "patient"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

@router.post("/upload", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def upload_medical_record(
    patient_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_patient)
):
    """Upload a PDF or image record; patients upload to their own profile and admins may choose a patient."""
    if current_user.role == "patient":
        patient_profile = get_patient_profile(db, current_user)
        if patient_id is not None and patient_id != patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients can only upload records to their own profile")
        patient_id = patient_profile.id
    elif patient_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="patient_id is required")

    # Validate patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's records")
        
    # Validate file extension
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Supported extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    # Create unique filename to prevent overwrite/collision
    unique_filename = f"{uuid.uuid4()}{ext}"
    dest_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Save the file content locally
    try:
        with open(dest_path, "wb") as f:
            content = file.file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
        
    # Register medical record
    record = MedicalRecord(
        patient_id=patient_id,
        file_name=file.filename,
        file_path=dest_path,
        file_type=ext.replace(".", ""),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return record

@router.get("/{patient_id}", response_model=List[MedicalRecordResponse])
def get_patient_records(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """List a patient's medical records; patient accounts may access only their own records."""
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's records")
        
    records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).all()
    return records

@router.get("/download/{record_id}")
def download_medical_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """Download a medical record visible to the signed-in user under their role's ownership rules."""
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found"
        )
    if current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        if record.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's record")
        
    if not os.path.exists(record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical file not found on server"
        )
        
    return FileResponse(
        path=record.file_path,
        filename=record.file_name,
        media_type="application/octet-stream"
    )
