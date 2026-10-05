import logging
import smtplib
import ssl
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
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
    # Display name so the inbox shows "SIRIUS" instead of a bare address.
    message["From"] = formataddr((settings.CLINIC_NAME, settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME))
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


# --- Shared SIRIUS email layout ---------------------------------------------------------------
# Email clients only support table layouts and inline styles; web fonts and images are often
# blocked, so the brand is rendered as styled text with Georgia as the serif.

SERIF = "Georgia, 'Times New Roman', serif"
SANS = "-apple-system, 'Segoe UI', Roboto, Arial, Helvetica, sans-serif"
INK, INK2, LINE, ACCENT = "#1C2227", "#6A7279", "#E9E5DD", "#0F5B68"
BADGE_TONES = {
    "info": ("#E3EEEE", "#0F5B68"),
    "ok": ("#E3F3EC", "#1B7A5A"),
    "warn": ("#FBF1D9", "#8A5F00"),
    "bad": ("#FBE9E7", "#B3322A"),
}


def _clinic_location() -> str:
    return ", ".join(part for part in (settings.CLINIC_CITY, settings.CLINIC_ADDRESS) if part)


def _cabinet_url(path: str = "/profile") -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def _format_fee(consultation_fee: float | None) -> str:
    if consultation_fee is None:
        return "Не указана"
    return f"{consultation_fee:,.2f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",") + " ₽"


def _doctor_display(doctor_name: str, specialization: str = "", qualification: str = "") -> str:
    details = ", ".join(
        detail for detail in (specialization, f"квалификация: {qualification}" if qualification else "") if detail
    )
    return f"{doctor_name} ({details})" if details else doctor_name


def _multiline(text: str) -> str:
    return escape(text).replace("\n", "<br>")


def _render_email(
    *,
    subject: str,
    preheader: str,
    eyebrow: str,
    title: str,
    patient_name: str,
    intro: str,
    badge: tuple[str, str] | None = None,
    details: list[tuple[str, str]] | None = None,
    note: tuple[str, str] | None = None,
    cta: tuple[str, str] | None = None,
    closing: str = "Желаем вам крепкого здоровья!",
) -> str:
    """Render the branded HTML email. All text arguments are plain text and are escaped here."""
    clinic = escape(settings.CLINIC_NAME)
    phone = escape(settings.CLINIC_CONTACT_PHONE)
    location = escape(_clinic_location())

    badge_html = ""
    if badge:
        label, tone = badge
        bg, fg = BADGE_TONES.get(tone, BADGE_TONES["info"])
        badge_html = (
            f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:18px 0 0;"><tr>'
            f'<td style="background:{bg}; color:{fg}; border-radius:99px; padding:7px 16px; font:600 13px/18px {SANS};">'
            f'&#9679;&nbsp; {escape(label)}</td></tr></table>'
        )

    details_html = ""
    if details:
        rows = []
        for index, (label, value) in enumerate(details):
            border = "" if index == len(details) - 1 else f"border-bottom:1px solid {LINE};"
            rows.append(
                f'<tr><td class="dl" width="40%" style="padding:13px 18px; {border} color:{INK2}; font:400 13px/20px {SANS}; vertical-align:top;">{escape(label)}</td>'
                f'<td class="dv" style="padding:13px 18px; {border} color:{INK}; font:500 15px/22px {SANS}; vertical-align:top;">{_multiline(value)}</td></tr>'
            )
        details_html = (
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" '
            f'style="margin:26px 0 0; background:#FAF8F4; border:1px solid {LINE}; border-radius:16px; border-collapse:separate;">'
            f'{"".join(rows)}</table>'
        )

    note_html = ""
    if note:
        note_title, note_text = note
        note_html = (
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:22px 0 0;"><tr>'
            f'<td style="background:#E3EEEE; border-left:3px solid {ACCENT}; border-radius:4px 14px 14px 4px; padding:16px 20px;">'
            f'<div style="color:{ACCENT}; font:700 12px/18px {SANS}; letter-spacing:.08em; text-transform:uppercase;">{escape(note_title)}</div>'
            f'<div style="margin-top:6px; color:{INK}; font:400 15px/24px {SANS};">{_multiline(note_text)}</div></td></tr></table>'
        )

    cta_html = ""
    if cta:
        label, url = cta
        cta_html = (
            f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:28px 0 0;"><tr>'
            f'<td style="background:{INK}; border-radius:99px;">'
            f'<a href="{escape(url, quote=True)}" target="_blank" style="display:inline-block; padding:14px 28px; color:#ffffff; '
            f'font:600 15px/20px {SANS}; text-decoration:none; border-radius:99px;">{escape(label)}&nbsp;&nbsp;&rarr;</a>'
            f'</td></tr></table>'
        )

    return f"""\
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{escape(subject)}</title>
<style>
  @media only screen and (max-width: 620px) {{
    .shell {{ width: 100% !important; }}
    .px {{ padding-left: 22px !important; padding-right: 22px !important; }}
    .title {{ font-size: 26px !important; line-height: 32px !important; }}
    .dl, .dv {{ display: block !important; width: auto !important; }}
    .dl {{ padding-bottom: 2px !important; border-bottom: 0 !important; }}
    .dv {{ padding-top: 0 !important; }}
  }}
</style>
</head>
<body style="margin:0; padding:0; background:#F2F0EA; -webkit-text-size-adjust:100%;">
<div style="display:none; max-height:0; overflow:hidden; opacity:0; color:transparent;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#F2F0EA;">
<tr><td align="center" style="padding:36px 12px;">
  <table role="presentation" class="shell" width="600" cellspacing="0" cellpadding="0" border="0" style="width:600px; max-width:600px;">
    <tr><td class="px" style="padding:0 8px 18px;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr>
        <td style="font:400 26px/30px {SERIF}; letter-spacing:6px; color:{INK};">{clinic}<span style="color:{ACCENT}; font-size:20px; letter-spacing:0;">&nbsp;&#10022;</span></td>
        <td align="right" style="font:500 11px/16px {SANS}; letter-spacing:.14em; text-transform:uppercase; color:{INK2};">Университетская<br>клиника</td>
      </tr></table>
    </td></tr>
    <tr><td style="background:#ffffff; border:1px solid {LINE}; border-radius:24px; overflow:hidden;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr><td style="height:5px; line-height:5px; font-size:0; background:{ACCENT}; background-image:linear-gradient(90deg,#0F5B68,#2A8796,#8FD9C4); border-radius:24px 24px 0 0;">&nbsp;</td></tr>
        <tr><td class="px" style="padding:34px 40px 8px;">
          <div style="color:{ACCENT}; font:600 12px/16px {SANS}; letter-spacing:.14em; text-transform:uppercase;">{escape(eyebrow)}</div>
          <div class="title" style="margin-top:10px; color:{INK}; font:400 32px/38px {SERIF};">{escape(title)}</div>
          {badge_html}
        </td></tr>
        <tr><td class="px" style="padding:22px 40px 38px;">
          <div style="color:{INK}; font:400 17px/26px {SANS};">Здравствуйте, <strong>{escape(patient_name)}</strong>!</div>
          <div style="margin-top:10px; color:#435057; font:400 15px/24px {SANS};">{_multiline(intro)}</div>
          {details_html}
          {note_html}
          {cta_html}
          <div style="margin-top:30px; color:#435057; font:400 15px/24px {SANS};">{escape(closing)}<br><span style="color:{INK}; font-weight:600;">Команда клиники «{clinic}»</span></div>
        </td></tr>
      </table>
    </td></tr>
    <tr><td class="px" style="padding:22px 12px 0; color:{INK2}; font:400 12px/19px {SANS}; text-align:center;">
      <strong style="color:{INK};">{clinic}</strong> &middot; {location}<br>
      <a href="tel:{phone}" style="color:{ACCENT}; text-decoration:none;">{phone}</a> &middot; Ежедневно 8:00–21:00<br>
      <span style="color:#9AA1A6;">Это автоматическое письмо, отвечать на него не нужно. ИИ-ассистент клиники не ставит диагнозов — решения принимает врач.</span>
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>
"""


# --- Emails -------------------------------------------------------------------------------------

def _appointment_details(
    appointment_number: str,
    appointment_date: date | datetime | str,
    time_slot: str,
    doctor_name: str,
    reason_for_visit: str,
    doctor_specialization: str,
    doctor_qualification: str,
    consultation_fee: float | None,
) -> list[tuple[str, str]]:
    return [
        ("Номер записи", appointment_number),
        ("Дата приёма", _format_russian_date(appointment_date)),
        ("Время приёма", time_slot.replace(" - ", " – ")),
        ("Врач", _doctor_display(doctor_name, doctor_specialization, doctor_qualification)),
        ("Причина визита", reason_for_visit or "Не указана"),
        ("Стоимость", _format_fee(consultation_fee)),
        ("Место", _clinic_location() or "Адрес необходимо уточнить у клиники"),
    ]


def _plain_details(details: list[tuple[str, str]]) -> str:
    return "\n".join(f"{label}: {value}" for label, value in details)


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
    details = _appointment_details(
        appointment_number, appointment_date, time_slot, doctor_name, reason_for_visit,
        doctor_specialization, doctor_qualification, consultation_fee,
    )
    before_visit = (
        "Подойдите за 10–15 минут до приёма и возьмите паспорт или другой документ, удостоверяющий личность. "
        "Если планы изменятся, пожалуйста, предупредите нас заранее."
    )
    subject = f"Подтверждение записи к врачу в клинику «{clinic_name}» 🩺"
    body = (
        f"Здравствуйте, {patient_name}!\n\n"
        f"Ваша запись на приём в клинику «{clinic_name}» подтверждена. Ждём вас!\n\n"
        f"{_plain_details(details)}\n\n"
        f"Перед визитом: {before_visit}\n"
        f"Контакты клиники: {settings.CLINIC_CONTACT_PHONE}\n"
        f"Личный кабинет: {_cabinet_url('/profile#appointments')}\n\n"
        f"Желаем крепкого здоровья!\nКоманда клиники «{clinic_name}»"
    )
    html_body = _render_email(
        subject=subject,
        preheader=f"Запись {appointment_number} подтверждена: {details[1][1]}, {details[2][1]}.",
        eyebrow="Запись на приём",
        title="Запись подтверждена 🩺",
        badge=(f"{details[1][1]} · {details[2][1]}", "info"),
        patient_name=patient_name,
        intro="Ваша запись на приём успешно подтверждена. Будем ждать вас в клинике.",
        details=details,
        note=("Перед визитом", before_visit),
        cta=("Открыть личный кабинет", _cabinet_url("/profile#appointments")),
        closing="Желаем вам крепкого здоровья и хорошего дня!",
    )
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
    details = _appointment_details(
        appointment_number, appointment_date, time_slot, doctor_name, reason_for_visit,
        doctor_specialization, doctor_qualification, consultation_fee,
    )
    before_visit = (
        "Подойдите за 10–15 минут до приёма и возьмите паспорт или другой документ, удостоверяющий личность. "
        "Если планы изменились, сообщите нам заранее."
    )
    subject = f"Напоминание о приёме в клинике «{clinic_name}» 🩺"
    body = (
        f"Здравствуйте, {patient_name}!\n\n"
        f"Напоминаем о вашем предстоящем приёме в клинике «{clinic_name}».\n\n"
        f"{_plain_details(details)}\n\n"
        f"Перед визитом: {before_visit}\n"
        f"Контакты клиники: {settings.CLINIC_CONTACT_PHONE}\n\n"
        f"До встречи!\nКоманда клиники «{clinic_name}»"
    )
    html_body = _render_email(
        subject=subject,
        preheader=f"Скоро приём: {details[1][1]}, {details[2][1]}.",
        eyebrow="Напоминание",
        title="Скоро увидимся 🩺",
        badge=(f"{details[1][1]} · {details[2][1]}", "warn"),
        patient_name=patient_name,
        intro="Напоминаем о вашем предстоящем приёме. Мы будем ждать вас в клинике.",
        details=details,
        note=("Перед визитом", before_visit),
        cta=("Мои записи", _cabinet_url("/profile#appointments")),
        closing="До встречи!",
    )
    _send_email(patient_email, subject, body, html_body)


def notify_patient_prescription_created(patient_email: str, patient_name: str, diagnosis: str, doctor_name: str):
    clinic_name = settings.CLINIC_NAME
    subject = f"Новое назначение от врача — клиника «{clinic_name}»"
    details = [("Врач", doctor_name), ("Диагноз", diagnosis)]
    body = (
        f"Здравствуйте, {patient_name}!\n\n"
        f"Врач {doctor_name} оформил для вас новое назначение.\n"
        f"Диагноз: {diagnosis}\n\n"
        "Полное назначение с препаратами и дозировкой доступно в личном кабинете или в клинике.\n"
        f"Контакты клиники: {settings.CLINIC_CONTACT_PHONE}\n\n"
        f"Команда клиники «{clinic_name}»"
    )
    html_body = _render_email(
        subject=subject,
        preheader=f"Врач {doctor_name} оформил для вас новое назначение.",
        eyebrow="Назначение врача",
        title="Новое назначение",
        badge=("Назначение оформлено", "ok"),
        patient_name=patient_name,
        intro=f"Врач {doctor_name} оформил для вас новое назначение по итогам приёма.",
        details=details,
        note=("Что дальше", "Полное назначение с препаратами, дозировкой и рекомендациями доступно в личном кабинете. "
                            "Если что-то непонятно, свяжитесь с клиникой."),
        cta=("Открыть личный кабинет", _cabinet_url("/profile")),
    )
    _send_email(patient_email, subject, body, html_body)


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
CASE_DECISION_TONE = {"NEEDS_EXAMINATION": "warn", "NO_EXAMINATION_NEEDED": "ok", "REFER_TO_SPECIALIST": "info"}


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
    title, explanation = CASE_DECISION_TEXT.get(decision, ("Решение врача", "Врач рассмотрел ваше обращение."))
    comment = doctor_comment or "Без комментария"
    details = [("Обращение", f"№{case_id}"), ("Врач", doctor_name)]
    if referred_doctor_name:
        details.append(("Специалист", referred_doctor_name))
    cta_label = "Записаться на приём" if decision == "NEEDS_EXAMINATION" else "Открыть обращение"

    subject = f"Обращение №{case_id}: {title} — клиника «{clinic_name}»"
    body = (
        f"Здравствуйте, {patient_name}!\n\n"
        f"По вашему обращению №{case_id} принято решение: {title}.\n"
        f"{explanation}\n\n"
        f"{_plain_details(details)}\n"
        f"Комментарий врача: {comment}\n\n"
        f"Подробности в личном кабинете: {_cabinet_url(f'/profile?case={case_id}#cases')}\n"
        f"Контакты клиники: {settings.CLINIC_CONTACT_PHONE}\n\n"
        f"Команда клиники «{clinic_name}»"
    )
    html_body = _render_email(
        subject=subject,
        preheader=f"Обращение №{case_id}: {title}.",
        eyebrow=f"Обращение №{case_id}",
        title="Врач рассмотрел ваше обращение",
        badge=(title, CASE_DECISION_TONE.get(decision, "info")),
        patient_name=patient_name,
        intro=explanation,
        details=details,
        note=("Комментарий врача", comment),
        cta=(cta_label, _cabinet_url(f"/profile?case={case_id}#cases")),
    )
    _send_email(patient_email, subject, body, html_body)
