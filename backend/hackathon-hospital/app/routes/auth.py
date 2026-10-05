from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timezone
from app.config import settings
from app.database import get_db
from app.models import User, Doctor, Patient
from app.schemas import UserRegister, UserResponse, UserLogin, Token, AcceptTerms
from app.security import get_password_hash, verify_password, create_access_token
router = APIRouter(prefix="/auth", tags=["Authentication"])

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' does not have permission to access this resource"
            )
        require_consent(current_user)
        return current_user


CONSENT_REQUIRED_DETAIL = "Consent to the user agreement and personal data processing is required"


def require_consent(current_user: User) -> None:
    """Patients may not use the platform (or send data to the AI) before accepting the current legal documents."""
    if current_user.needs_consent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CONSENT_REQUIRED_DETAIL)

def get_patient_profile(db: Session, current_user: User) -> Patient:
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found for current user"
        )
    return patient

def get_doctor_profile(db: Session, current_user: User) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for current user"
        )
    return doctor

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """Create a public patient or doctor account; doctor registration also creates a basic doctor profile."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        password_hash=hashed_password,
        full_name=user_in.full_name,
        role=user_in.role,
        terms_accepted_at=datetime.now(timezone.utc),
        terms_version=settings.LEGAL_DOCS_VERSION,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # If role is doctor, automatically pre-create doctor profile
    if user.role == "doctor":
        existing_doctor = db.query(Doctor).filter(Doctor.email == user.email).first()
        if not existing_doctor:
            doctor = Doctor(
                user_id=user.id,
                full_name=user.full_name,
                specialization="General Medicine",
                qualification="MBBS",
                phone_number="0000000000",
                email=user.email,
                consultation_fee=500.0,
                available_timings="Mon-Fri 09:00-17:00"
            )
            db.add(doctor)
            db.commit()
        
    return user

@router.post("/login", response_model=Token)
def login(
    login_in: UserLogin,
    db: Session = Depends(get_db),
):
    """Validate account credentials and return a bearer access token."""

    user = db.query(User).filter(User.email == login_in.email).first()
    
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/accept-terms", response_model=UserResponse)
def accept_terms(
    data: AcceptTerms,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record the user's consent to the current user agreement, privacy policy and data-processing consent."""
    current_user.terms_accepted_at = datetime.now(timezone.utc)
    current_user.terms_version = settings.LEGAL_DOCS_VERSION
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the authenticated user."""
    return current_user





