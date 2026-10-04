import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Patient, Doctor, Appointment, User
from app.schemas import DashboardReport, AppointmentsReport, DoctorsReport, DoctorReportItem
from app.routes.auth import RoleChecker

router = APIRouter(prefix="/reports", tags=["Reports"])

admin_only = RoleChecker(["admin"])

@router.get("/dashboard", response_model=DashboardReport)
def get_dashboard_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Return clinic-wide patient, doctor, and appointment summary metrics; admin access is required."""
    today = datetime.date.today()
    
    total_patients = db.query(func.count(Patient.id)).scalar() or 0
    total_doctors = db.query(func.count(Doctor.id)).scalar() or 0
    
    today_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_date == today
    ).scalar() or 0
    
    upcoming_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_date > today,
        Appointment.status.in_(["Scheduled", "Confirmed"])
    ).scalar() or 0
    
    completed_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.status == "Completed"
    ).scalar() or 0
    
    cancelled_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.status == "Cancelled"
    ).scalar() or 0
    
    # Most Visited Doctor calculation
    most_visited_doc_query = db.query(
        Appointment.doctor_id, 
        func.count(Appointment.id).label("cnt")
    ).group_by(
        Appointment.doctor_id
    ).order_by(
        func.count(Appointment.id).desc()
    ).first()
    
    most_visited_doctor_name = "N/A"
    if most_visited_doc_query:
        doc_id = most_visited_doc_query[0]
        doc = db.query(Doctor).filter(Doctor.id == doc_id).first()
        if doc:
            most_visited_doctor_name = doc.full_name
            
    # Average Daily Appointments calculation
    total_appointments = db.query(func.count(Appointment.id)).scalar() or 0
    distinct_dates_count = db.query(func.count(func.distinct(Appointment.appointment_date))).scalar() or 0
    
    avg_daily_appts = 0.0
    if distinct_dates_count > 0:
        avg_daily_appts = round(float(total_appointments) / distinct_dates_count, 2)
        
    return DashboardReport(
        total_patients=total_patients,
        total_doctors=total_doctors,
        today_appointments=today_appointments,
        upcoming_appointments=upcoming_appointments,
        completed_appointments=completed_appointments,
        cancelled_appointments=cancelled_appointments,
        most_visited_doctor=most_visited_doctor_name,
        average_daily_appointments=avg_daily_appts
    )

@router.get("/appointments", response_model=AppointmentsReport)
def get_appointments_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Return clinic-wide appointment counts grouped by status; admin access is required."""
    total = db.query(func.count(Appointment.id)).scalar() or 0
    scheduled = db.query(func.count(Appointment.id)).filter(Appointment.status == "Scheduled").scalar() or 0
    confirmed = db.query(func.count(Appointment.id)).filter(Appointment.status == "Confirmed").scalar() or 0
    completed = db.query(func.count(Appointment.id)).filter(Appointment.status == "Completed").scalar() or 0
    cancelled = db.query(func.count(Appointment.id)).filter(Appointment.status == "Cancelled").scalar() or 0
    no_show = db.query(func.count(Appointment.id)).filter(Appointment.status == "No Show").scalar() or 0
    
    return AppointmentsReport(
        total_appointments=total,
        scheduled=scheduled,
        confirmed=confirmed,
        completed=completed,
        cancelled=cancelled,
        no_show=no_show
    )

@router.get("/doctors", response_model=DoctorsReport)
def get_doctors_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Return appointment counts for each doctor; admin access is required."""
    # Fetch appointment counts per doctor
    results = db.query(
        Doctor.id,
        Doctor.full_name,
        func.count(Appointment.id).label("cnt")
    ).outerjoin(
        Appointment, Doctor.id == Appointment.doctor_id
    ).group_by(
        Doctor.id, Doctor.full_name
    ).order_by(
        func.count(Appointment.id).desc()
    ).all()
    
    doctor_items = []
    for r in results:
        doctor_items.append(
            DoctorReportItem(
                doctor_id=r[0],
                doctor_name=r[1],
                appointment_count=r[2]
            )
        )
        
    return DoctorsReport(doctors=doctor_items)
