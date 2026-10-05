from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Patient, User
from app.schemas import PatientCreate, PatientResponse, PatientUpdate
from app.routes.auth import RoleChecker, get_patient_profile

router = APIRouter(prefix="/patients", tags=["Patients"])

# Role check dependencies
admin_or_patient = RoleChecker(["admin", "patient"])
all_roles = RoleChecker(["admin", "doctor", "patient"])
admin_only = RoleChecker(["admin"])

@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_patient)
):
    """Create a patient profile for the signed-in patient or an unlinked profile as an admin."""
    if current_user.role == "patient" and current_user.patient_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient profile already exists")

    # Check if patient phone number is already registered
    existing_patient = db.query(Patient).filter(Patient.phone_number == patient_in.phone_number).first()
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient phone number already registered"
        )
        
    patient = Patient(
        user_id=current_user.id if current_user.role == "patient" else None,
        full_name=patient_in.full_name,
        age=patient_in.age,
        gender=patient_in.gender,
        phone_number=patient_in.phone_number,
        address=patient_in.address,
        blood_group=patient_in.blood_group,
        emergency_contact=patient_in.emergency_contact
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

@router.get("", response_model=List[PatientResponse], operation_id="list_patients")
def get_patients(
    name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "id",
    order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """List patient profiles; patient accounts receive only their own profile."""
    query = db.query(Patient)
    
    # Search
    if current_user.role == "patient":
        patient = get_patient_profile(db, current_user)
        query = query.filter(Patient.id == patient.id)
    if name:
        query = query.filter(Patient.full_name.ilike(f"%{name}%"))
        
    # Sorting
    if sort_by in ["id", "full_name", "age", "created_at"]:
        field = getattr(Patient, sort_by)
        if order.lower() == "desc":
            query = query.order_by(field.desc())
        else:
            query = query.order_by(field.asc())
    else:
        query = query.order_by(Patient.id.asc())
        
    # Pagination
    return query.offset(skip).limit(limit).all()

@router.get("/{id}", response_model=PatientResponse)
def get_patient_by_id(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    """Return a patient profile, limited to the owner's profile for patient accounts."""
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's profile")
    return patient

@router.put("/{id}", response_model=PatientResponse)
def update_patient(
    id: int,
    patient_update: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_patient)
):
    """Update a patient's own profile or manage another profile as an admin."""
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another patient's profile")
        
    update_data = patient_update.model_dump(exclude_unset=True)
    if current_user.role == "patient" and "user_id" in update_data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients cannot change account links")
    if "user_id" in update_data and update_data["user_id"] is not None:
        linked_user = db.query(User).filter(
            User.id == update_data["user_id"],
            User.role == "patient"
        ).first()
        if not linked_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient user account not found")
        existing_profile = db.query(Patient).filter(
            Patient.user_id == update_data["user_id"],
            Patient.id != patient.id
        ).first()
        if existing_profile:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is already linked to another patient profile")

    for key, value in update_data.items():
        setattr(patient, key, value)
        
    db.commit()
    db.refresh(patient)
    return patient

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Delete a patient profile and its dependent records; admin access is required."""
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
        
    db.delete(patient)
    db.commit()
    return None
