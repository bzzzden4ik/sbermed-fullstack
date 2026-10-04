from email import message_from_bytes
from email.header import decode_header, make_header

from app.config import settings
from app.utils import background


def test_notifications_send_email_through_authenticated_smtp(monkeypatch):
    sent_messages = []
    login_credentials = []

    class FakeSMTP:
        def __init__(self, host, port, timeout, context):
            assert host == "smtp.test.example"
            assert port == 465
            assert timeout == 3
            assert context is not None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def login(self, username, password):
            login_credentials.append((username, password))

        def send_message(self, message):
            sent_messages.append(message_from_bytes(message.as_bytes()))

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.example")
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "clinic@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "test-app-password")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 3)
    monkeypatch.setattr(background.smtplib, "SMTP_SSL", FakeSMTP)

    monkeypatch.setattr(settings, "CLINIC_NAME", "Клиника Тест")
    monkeypatch.setattr(settings, "CLINIC_CITY", "Казань")
    monkeypatch.setattr(settings, "CLINIC_ADDRESS", "ул. Тестовая, 1")
    monkeypatch.setattr(settings, "CLINIC_CONTACT_PHONE", "+7 (900) 000-00-00")

    background.send_appointment_confirmation_email(
        "patient@example.com",
        "Пациент Тестовый",
        "APT-20261003-9138",
        "2026-10-03",
        "10:00 - 10:30",
        "Кирилл",
        reason_for_visit="Жалобы на головную боль",
        doctor_specialization="General Medicine",
        doctor_qualification="MBBS",
        consultation_fee=500,
    )
    background.send_appointment_reminder_email(
        "patient@example.com",
        "Пациент Тестовый",
        "APT-20261003-9138",
        "2026-10-03",
        "10:00 - 10:30",
        "Кирилл",
        reason_for_visit="Жалобы на головную боль",
        doctor_specialization="General Medicine",
        doctor_qualification="MBBS",
        consultation_fee=500,
    )
    background.notify_patient_prescription_created(
        "patient@example.com", "Patient", "Diagnosis", "Doctor"
    )

    assert login_credentials == [("clinic@example.com", "test-app-password")] * 3
    assert [message["To"] for message in sent_messages] == ["patient@example.com"] * 3
    assert [str(make_header(decode_header(message["Subject"]))) for message in sent_messages] == [
        "Подтверждение записи к врачу в клинику «Клиника Тест» 🩺",
        "Напоминание о приёме в клинике «Клиника Тест» 🩺",
        "New Prescription Issued",
    ]
    confirmation_parts = sent_messages[0].get_payload()
    assert confirmation_parts[0].get_content_type() == "text/plain"
    assert confirmation_parts[1].get_content_type() == "text/html"
    html_body = confirmation_parts[1].get_payload(decode=True).decode("utf-8")
    assert "Пациент Тестовый" in html_body
    assert "03 октября 2026 г. (суббота)" in html_body
    assert "APT-20261003-9138" in html_body
    assert "10:00 – 10:30" in html_body
    assert "Кирилл (General Medicine, квалификация: MBBS)" in html_body
    assert "Жалобы на головную боль" in html_body
    assert "500 ₽" in html_body
    assert "Казань, ул. Тестовая, 1" in html_body

    reminder_parts = sent_messages[1].get_payload()
    assert reminder_parts[0].get_content_type() == "text/plain"
    assert reminder_parts[1].get_content_type() == "text/html"
    reminder_html = reminder_parts[1].get_payload(decode=True).decode("utf-8")
    assert "Скоро увидимся" in reminder_html
    assert "03 октября 2026 г. (суббота)" in reminder_html
    assert "APT-20261003-9138" in reminder_html
    assert "10:00 – 10:30" in reminder_html
    assert "Кирилл (General Medicine, квалификация: MBBS)" in reminder_html
    assert "Жалобы на головную боль" in reminder_html
    assert "500 ₽" in reminder_html