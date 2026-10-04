import logging
import smtplib
import ssl
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackgroundTasks")

def _send_email(recipient: str, subject: str, body: str, html_body: str | None = None) -> None:
    if not recipient:
        logger.warning("Skipping email delivery because the recipient has no email address.")
        return
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning("Skipping email delivery because SMTP credentials are not configured.")
        return

    message = MIMEMultipart("alternative")
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    if html_body:
        message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.SMTP_PORT == 465:
            smtp_client = smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
                context=ssl.create_default_context(),
            )
        else:
            smtp_client = smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )

        with smtp_client as server:
            if settings.SMTP_PORT != 465:
                server.starttls(context=ssl.create_default_context())
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("SMTP delivery failed for an outgoing notification.")


def _format_russian_date(appointment_date: date | datetime | str) -> str:
        if isinstance(appointment_date, str):
                appointment_date = date.fromisoformat(appointment_date)
        if isinstance(appointment_date, datetime):
                appointment_date = appointment_date.date()

        months = (
                "января", "февраля", "марта", "апреля", "мая", "июня",
                "июля", "августа", "сентября", "октября", "ноября", "декабря",
        )
        weekdays = (
                "понедельник", "вторник", "среда", "четверг", "пятница",
                "суббота", "воскресенье",
        )
        return (
                f"{appointment_date.day:02d} {months[appointment_date.month - 1]} "
                f"{appointment_date.year} г. ({weekdays[appointment_date.weekday()]})"
        )


def send_appointment_confirmation_email(
        patient_email: str,
        patient_name: str,
        appointment_number: str,
        appointment_date: date | datetime | str,
        time_slot: str,
        doctor_name: str,
        reason_for_visit: str = "",
        doctor_specialization: str = "",
        doctor_qualification: str = "",
        consultation_fee: float | None = None,
):
    clinic_name = settings.CLINIC_NAME
    clinic_city = settings.CLINIC_CITY
    clinic_address = settings.CLINIC_ADDRESS or "Адрес необходимо уточнить у клиники"
    clinic_phone = settings.CLINIC_CONTACT_PHONE
    formatted_date = _format_russian_date(appointment_date)
    formatted_time = time_slot.replace(" - ", " – ")
    doctor_details = ", ".join(
        detail for detail in (doctor_specialization, f"квалификация: {doctor_qualification}" if doctor_qualification else "")
        if detail
    )
    doctor_display = f"{doctor_name} ({doctor_details})" if doctor_details else doctor_name
    fee_display = "Не указана"
    if consultation_fee is not None:
        fee_display = f"{consultation_fee:,.2f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",") + " ₽"

    safe_patient = escape(patient_name)
    safe_clinic = escape(clinic_name)
    safe_city = escape(clinic_city)
    safe_address = escape(clinic_address)
    safe_phone = escape(clinic_phone)
    safe_number = escape(appointment_number)
    safe_date = escape(formatted_date)
    safe_time = escape(formatted_time)
    safe_doctor = escape(doctor_display)
    safe_reason = escape(reason_for_visit or "Не указана")
    safe_fee = escape(fee_display)

    subject = f"Подтверждение записи к врачу в клинику «{clinic_name}» 🩺"
    
    body = (
        f"Здравствуйте, {patient_name}!\n\n"
        f"Ваша запись на прием в клинику «{clinic_name}» подтверждена. Ждем вас!\n\n"
        f"Номер записи: {appointment_number}\nДата приема: {formatted_date}\n"
        f"Время приема: {formatted_time}\nВрач: {doctor_display}\n"
        f"Причина визита: {reason_for_visit or 'Не указана'}\n"
        f"Стоимость консультации: {fee_display}\n\n"
        f"Место проведения: {clinic_city}, {clinic_address}\n"
        "Пожалуйста, подойдите за 10–15 минут до приема и возьмите документ, удостоверяющий личность.\n"
        f"Если планы изменятся, сообщите нам заранее: {clinic_phone}.\n\n"
        f"Желаем крепкого здоровья!\nКоманда клиники «{clinic_name}»"
    )
    
    html_body = f"""\
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light">
    <title>{escape(subject)}</title>
    <style>
        @media only screen and (max-width: 600px) {{
            .email-shell {{ width: 100% !important; }}
            .email-content {{ padding: 24px 18px !important; }}
            .detail-label, .detail-value {{ display: block !important; width: auto !important; }}
            .detail-label {{ padding-bottom: 4px !important; }}
            .detail-value {{ padding-top: 0 !important; }}
        }}
    </style>
</head>
<body style="margin:0; padding:0; background:#f2f6f5; color:#243b3a; font-family:Arial,Helvetica,sans-serif;">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0;">Запись {safe_number} подтверждена.</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f2f6f5;">
        <tr><td align="center" style="padding:32px 12px;">
            <table role="presentation" class="email-shell" width="600" cellspacing="0" cellpadding="0" border="0" style="width:600px; max-width:600px; background:#ffffff; border-radius:12px; overflow:hidden;">
                <tr><td style="padding:30px 34px; background:#145b55; color:#ffffff;">
                    <div style="font-size:13px; line-height:20px; text-transform:uppercase;">Клиника «{safe_clinic}»</div>
                    <h1 style="margin:8px 0 0; font-size:25px; line-height:32px; font-weight:700;">Запись подтверждена 🩺</h1>
                </td></tr>
                <tr><td class="email-content" style="padding:32px 34px;">
                    <p style="margin:0 0 12px; font-size:17px; line-height:26px;">Здравствуйте, <strong>{safe_patient}</strong>!</p>
                    <p style="margin:0 0 24px; color:#536765; font-size:15px; line-height:24px;">Ваша запись на прием успешно подтверждена. Будем ждать вас в клинике.</p>
                    <h2 style="margin:0 0 12px; color:#145b55; font-size:17px; line-height:24px;">Детали записи</h2>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dce8e5; border-radius:8px;">
                        <tr><td class="detail-label" width="38%" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Номер записи</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px; font-weight:700;"><span style="font-family:monospace;">{safe_number}</span></td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Дата приема</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_date}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Время приема</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_time}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Врач</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_doctor}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Причина визита</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_reason}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; color:#657774; font-size:14px;">Стоимость</td><td class="detail-value" style="padding:12px 14px; font-size:14px; font-weight:700;">{safe_fee}</td></tr>
                    </table>
                    <div style="margin-top:22px; padding:16px 18px; background:#edf6f3; border-left:3px solid #42a58e; border-radius:4px;">
                        <p style="margin:0 0 6px; color:#145b55; font-size:15px; font-weight:700;">Перед визитом</p>
                        <p style="margin:0; color:#435a57; font-size:14px; line-height:22px;">Подойдите за 10–15 минут до приема и возьмите паспорт или другой документ, удостоверяющий личность. Если планы изменятся, пожалуйста, предупредите нас заранее.</p>
                    </div>
                    <p style="margin:22px 0 4px; font-size:14px; line-height:22px;"><strong>Место проведения:</strong> {safe_city}, {safe_address}</p>
                    <p style="margin:0; font-size:14px; line-height:22px;"><strong>Контакты:</strong> <a href="tel:{safe_phone}" style="color:#145b55;">{safe_phone}</a></p>
                    <p style="margin:24px 0 0; color:#536765; font-size:14px; line-height:22px;">Желаем вам крепкого здоровья и хорошего дня!<br><strong>Команда клиники «{safe_clinic}»</strong></p>
                </td></tr>
                <tr><td style="padding:16px 34px; background:#f8faf9; color:#80908d; font-size:12px; line-height:18px;">Это автоматическое подтверждение записи. Пожалуйста, сохраните письмо до визита.</td></tr>
            </table>
        </td></tr>
    </table>
</body>
</html>
"""
    _send_email(patient_email, subject, body, html_body)


def send_appointment_reminder_email(
    patient_email: str,
    patient_name: str,
    appointment_number: str,
    appointment_date: date | datetime | str,
    time_slot: str,
    doctor_name: str,
    reason_for_visit: str = "",
    doctor_specialization: str = "",
    doctor_qualification: str = "",
    consultation_fee: float | None = None,
):
    clinic_name = settings.CLINIC_NAME
    clinic_city = settings.CLINIC_CITY
    clinic_address = settings.CLINIC_ADDRESS or "Адрес необходимо уточнить у клиники"
    clinic_phone = settings.CLINIC_CONTACT_PHONE
    formatted_date = _format_russian_date(appointment_date)
    formatted_time = time_slot.replace(" - ", " – ")
    doctor_details = ", ".join(
        detail for detail in (
            doctor_specialization,
            f"квалификация: {doctor_qualification}" if doctor_qualification else "",
        )
        if detail
    )
    doctor_display = f"{doctor_name} ({doctor_details})" if doctor_details else doctor_name
    fee_display = "Не указана"
    if consultation_fee is not None:
        fee_display = f"{consultation_fee:,.2f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",") + " ₽"

    safe_subject = escape(f"Напоминание о приёме в клинике «{clinic_name}» 🩺")
    safe_patient = escape(patient_name)
    safe_clinic = escape(clinic_name)
    safe_city = escape(clinic_city)
    safe_address = escape(clinic_address)
    safe_phone = escape(clinic_phone)
    safe_number = escape(appointment_number)
    safe_date = escape(formatted_date)
    safe_time = escape(formatted_time)
    safe_doctor = escape(doctor_display)
    safe_reason = escape(reason_for_visit or "Не указана")
    safe_fee = escape(fee_display)

    body = (
        f"Здравствуйте, {patient_name}!\n\n"
        f"Напоминаем о вашем предстоящем приёме в клинике «{clinic_name}».\n\n"
        f"Номер записи: {appointment_number}\nДата приема: {formatted_date}\n"
        f"Время приема: {formatted_time}\nВрач: {doctor_display}\n"
        f"Причина визита: {reason_for_visit or 'Не указана'}\n"
        f"Стоимость консультации: {fee_display}\n\n"
        f"Место проведения: {clinic_city}, {clinic_address}\n"
        "Пожалуйста, подойдите за 10–15 минут и возьмите документ, удостоверяющий личность.\n"
        f"Контакты клиники: {clinic_phone}.\n\n"
        f"До встречи!\nКоманда клиники «{clinic_name}»"
    )
    html_body = f"""\
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light">
    <title>{safe_subject}</title>
    <style>
        @media only screen and (max-width: 600px) {{
            .email-shell {{ width: 100% !important; }}
            .email-content {{ padding: 24px 18px !important; }}
            .detail-label, .detail-value {{ display: block !important; width: auto !important; }}
            .detail-label {{ padding-bottom: 4px !important; }}
            .detail-value {{ padding-top: 0 !important; }}
        }}
    </style>
</head>
<body style="margin:0; padding:0; background:#f2f6f5; color:#243b3a; font-family:Arial,Helvetica,sans-serif;">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0;">Скоро приём: {safe_date}, {safe_time}.</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f2f6f5;">
        <tr><td align="center" style="padding:32px 12px;">
            <table role="presentation" class="email-shell" width="600" cellspacing="0" cellpadding="0" border="0" style="width:600px; max-width:600px; background:#ffffff; border-radius:12px; overflow:hidden;">
                <tr><td style="padding:30px 34px; background:#145b55; color:#ffffff;">
                    <div style="font-size:13px; line-height:20px; text-transform:uppercase;">Клиника «{safe_clinic}»</div>
                    <h1 style="margin:8px 0 0; font-size:25px; line-height:32px; font-weight:700;">Скоро увидимся 🩺</h1>
                </td></tr>
                <tr><td class="email-content" style="padding:32px 34px;">
                    <p style="margin:0 0 12px; font-size:17px; line-height:26px;">Здравствуйте, <strong>{safe_patient}</strong>!</p>
                    <p style="margin:0 0 24px; color:#536765; font-size:15px; line-height:24px;">Напоминаем о вашем предстоящем приёме. Мы будем ждать вас в клинике.</p>
                    <h2 style="margin:0 0 12px; color:#145b55; font-size:17px; line-height:24px;">Детали вашего визита</h2>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dce8e5; border-radius:8px;">
                        <tr><td class="detail-label" width="38%" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Номер записи</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px; font-weight:700;"><span style="font-family:monospace;">{safe_number}</span></td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Дата приема</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_date}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Время приема</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_time}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Врач</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_doctor}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-bottom:1px solid #e8efed; color:#657774; font-size:14px;">Причина визита</td><td class="detail-value" style="padding:12px 14px; border-bottom:1px solid #e8efed; font-size:14px;">{safe_reason}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; color:#657774; font-size:14px;">Стоимость</td><td class="detail-value" style="padding:12px 14px; font-size:14px; font-weight:700;">{safe_fee}</td></tr>
                    </table>
                    <div style="margin-top:22px; padding:16px 18px; background:#edf6f3; border-left:3px solid #42a58e; border-radius:4px;">
                        <p style="margin:0 0 6px; color:#145b55; font-size:15px; font-weight:700;">Перед визитом</p>
                        <p style="margin:0; color:#435a57; font-size:14px; line-height:22px;">Подойдите за 10–15 минут до приема и возьмите паспорт или другой документ, удостоверяющий личность. Если планы изменились, сообщите нам заранее.</p>
                    </div>
                    <p style="margin:22px 0 4px; font-size:14px; line-height:22px;"><strong>Место проведения:</strong> {safe_city}, {safe_address}</p>
                    <p style="margin:0; font-size:14px; line-height:22px;"><strong>Контакты:</strong> <a href="tel:{safe_phone}" style="color:#145b55;">{safe_phone}</a></p>
                    <p style="margin:24px 0 0; color:#536765; font-size:14px; line-height:22px;">До встречи!<br><strong>Команда клиники «{safe_clinic}»</strong></p>
                </td></tr>
                <tr><td style="padding:16px 34px; background:#f8faf9; color:#80908d; font-size:12px; line-height:18px;">Это автоматическое напоминание о вашей записи.</td></tr>
            </table>
        </td></tr>
    </table>
</body>
</html>
"""
    _send_email(
        patient_email,
        f"Напоминание о приёме в клинике «{clinic_name}» 🩺",
        body,
        html_body,
    )


def notify_patient_prescription_created(patient_email: str, patient_name: str, diagnosis: str, doctor_name: str):
    body = (
        f"Dear {patient_name},\n\n"
        f"Dr. {doctor_name} has issued a new prescription for you.\n"
        f"Diagnosis: {diagnosis}\n\n"
        "Log in to your patient portal or contact the clinic to view the full prescription."
    )
    _send_email(patient_email, "New Prescription Issued", body)


CASE_DECISION_TEXT = {
    "NEEDS_EXAMINATION": (
        "Требуется очный осмотр",
        "Врач изучил ваше обращение и рекомендует очный приём. Запишитесь на удобное время в личном кабинете.",
    ),
    "NO_EXAMINATION_NEEDED": (
        "Очный осмотр не требуется",
        "Врач изучил ваше обращение и считает, что очный осмотр сейчас не нужен. Ознакомьтесь с комментарием врача.",
    ),
    "REFER_TO_SPECIALIST": (
        "Направление к специалисту",
        "Врач направил ваше обращение профильному специалисту. Он изучит его и примет решение.",
    ),
}


def send_case_decision_email(
        patient_email: str,
        patient_name: str,
        case_id: int,
        decision: str,
        doctor_name: str,
        doctor_comment: str | None = None,
        referred_doctor_name: str | None = None,
):
    clinic_name = settings.CLINIC_NAME
    clinic_phone = settings.CLINIC_CONTACT_PHONE
    title, explanation = CASE_DECISION_TEXT.get(decision, ("Решение врача", "Врач рассмотрел ваше обращение."))
    comment = doctor_comment or "Без комментария"

    safe_clinic = escape(clinic_name)
    safe_patient = escape(patient_name)
    safe_title = escape(title)
    safe_explanation = escape(explanation)
    safe_doctor = escape(doctor_name)
    safe_comment = escape(comment).replace("\n", "<br>")
    safe_phone = escape(clinic_phone)
    referred_row = ""
    if referred_doctor_name:
        referred_row = (
            '<tr><td class="detail-label" style="padding:12px 14px; border-top:1px solid #e8efed; color:#657774; font-size:14px;">Специалист</td>'
            f'<td class="detail-value" style="padding:12px 14px; border-top:1px solid #e8efed; font-size:14px;">{escape(referred_doctor_name)}</td></tr>'
        )

    subject = f"Обращение №{case_id}: {title} — клиника «{clinic_name}»"
    body = (
        f"Здравствуйте, {patient_name}!\n\n"
        f"По вашему обращению №{case_id} принято решение: {title}.\n"
        f"{explanation}\n\n"
        f"Врач: {doctor_name}\n"
        + (f"Специалист: {referred_doctor_name}\n" if referred_doctor_name else "")
        + f"Комментарий врача: {comment}\n\n"
        "Подробности доступны в личном кабинете.\n"
        f"Контакты клиники: {clinic_phone}\n\n"
        f"Команда клиники «{clinic_name}»"
    )
    html_body = f"""\
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light">
    <title>{escape(subject)}</title>
    <style>
        @media only screen and (max-width: 600px) {{
            .email-shell {{ width: 100% !important; }}
            .email-content {{ padding: 24px 18px !important; }}
            .detail-label, .detail-value {{ display: block !important; width: auto !important; }}
        }}
    </style>
</head>
<body style="margin:0; padding:0; background:#f2f6f5; color:#243b3a; font-family:Arial,Helvetica,sans-serif;">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0;">Обращение №{case_id}: {safe_title}.</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f2f6f5;">
        <tr><td align="center" style="padding:32px 12px;">
            <table role="presentation" class="email-shell" width="600" cellspacing="0" cellpadding="0" border="0" style="width:600px; max-width:600px; background:#ffffff; border-radius:12px; overflow:hidden;">
                <tr><td style="padding:30px 34px; background:#0F5B68; color:#ffffff;">
                    <div style="font-size:13px; line-height:20px; text-transform:uppercase;">Клиника «{safe_clinic}»</div>
                    <h1 style="margin:8px 0 0; font-size:25px; line-height:32px; font-weight:700;">{safe_title}</h1>
                </td></tr>
                <tr><td class="email-content" style="padding:32px 34px;">
                    <p style="margin:0 0 12px; font-size:17px; line-height:26px;">Здравствуйте, <strong>{safe_patient}</strong>!</p>
                    <p style="margin:0 0 24px; color:#536765; font-size:15px; line-height:24px;">{safe_explanation}</p>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dce8e5; border-radius:8px;">
                        <tr><td class="detail-label" width="38%" style="padding:12px 14px; color:#657774; font-size:14px;">Обращение</td><td class="detail-value" style="padding:12px 14px; font-size:14px; font-weight:700;">№{case_id}</td></tr>
                        <tr><td class="detail-label" style="padding:12px 14px; border-top:1px solid #e8efed; color:#657774; font-size:14px;">Врач</td><td class="detail-value" style="padding:12px 14px; border-top:1px solid #e8efed; font-size:14px;">{safe_doctor}</td></tr>
                        {referred_row}
                    </table>
                    <div style="margin-top:22px; padding:16px 18px; background:#edf6f3; border-left:3px solid #42a58e; border-radius:4px;">
                        <p style="margin:0 0 6px; color:#0F5B68; font-size:15px; font-weight:700;">Комментарий врача</p>
                        <p style="margin:0; color:#435a57; font-size:14px; line-height:22px;">{safe_comment}</p>
                    </div>
                    <p style="margin:22px 0 0; font-size:14px; line-height:22px;">Подробности доступны в личном кабинете. Контакты клиники: <a href="tel:{safe_phone}" style="color:#0F5B68;">{safe_phone}</a></p>
                    <p style="margin:24px 0 0; color:#536765; font-size:14px; line-height:22px;">Желаем вам крепкого здоровья!<br><strong>Команда клиники «{safe_clinic}»</strong></p>
                </td></tr>
                <tr><td style="padding:16px 34px; background:#f8faf9; color:#80908d; font-size:12px; line-height:18px;">Решение принято врачом. ИИ-ассистент только собирает информацию и не ставит диагнозов.</td></tr>
            </table>
        </td></tr>
    </table>
</body>
</html>
"""
    _send_email(patient_email, subject, body, html_body)
