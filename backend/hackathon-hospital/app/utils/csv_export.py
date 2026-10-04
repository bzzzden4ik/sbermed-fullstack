import csv
from io import StringIO
from typing import List

def export_appointments_to_csv(appointments) -> str:
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Appointment Number", 
        "Patient Name", 
        "Doctor Name", 
        "Appointment Date", 
        "Time Slot", 
        "Reason for Visit", 
        "Status", 
        "Created At"
    ])
    
    # Data rows
    for appt in appointments:
        writer.writerow([
            appt.appointment_number,
            appt.patient.full_name if appt.patient else "N/A",
            appt.doctor.full_name if appt.doctor else "N/A",
            appt.appointment_date.strftime("%Y-%m-%d") if appt.appointment_date else "",
            appt.time_slot,
            appt.reason_for_visit,
            appt.status,
            appt.created_at.strftime("%Y-%m-%d %H:%M:%S") if appt.created_at else ""
        ])
        
    return output.getvalue()
