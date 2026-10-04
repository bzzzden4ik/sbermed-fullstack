def test_reports_dashboard_access_and_metrics(client, admin_headers):
    # Register and login patient
    client.post("/auth/register", json={
        "email": "patient@clinic.com",
        "password": "patientpassword123",
        "full_name": "Clinic Patient",
        "role": "patient"
    })
    patient_login = client.post("/auth/login", json={
        "email": "patient@clinic.com",
        "password": "patientpassword123"
    })
    patient_token = patient_login.json()["access_token"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    # Patients cannot access reports dashboard
    resp_patient = client.get("/reports/dashboard", headers=patient_headers)
    assert resp_patient.status_code == 403

    # Access reports dashboard as admin (expecting 200 Success)
    resp_admin = client.get("/reports/dashboard", headers=admin_headers)
    assert resp_admin.status_code == 200
    metrics = resp_admin.json()
    assert "total_patients" in metrics
    assert "total_doctors" in metrics
    assert "today_appointments" in metrics
    assert "upcoming_appointments" in metrics
    assert "completed_appointments" in metrics
    assert "cancelled_appointments" in metrics
    assert "average_daily_appointments" in metrics

    # Access appointments summary report
    resp_appts = client.get("/reports/appointments", headers=admin_headers)
    assert resp_appts.status_code == 200
    assert "total_appointments" in resp_appts.json()

    # Access doctors performance report
    resp_docs = client.get("/reports/doctors", headers=admin_headers)
    assert resp_docs.status_code == 200
    assert "doctors" in resp_docs.json()
