/** Russian labels and chip tones for backend enums. */

export const CASE_STATUS = {
    OPEN: { label: 'Новое', tone: '' },
    AI_COLLECTING: { label: 'Сбор информации', tone: 'warn' },
    READY_FOR_DOCTOR: { label: 'Передано врачу', tone: 'info' },
    REFERRED: { label: 'Направлено специалисту', tone: 'info' },
    UNDER_REVIEW: { label: 'На рассмотрении', tone: 'info' },
    RESOLVED: { label: 'Решение принято', tone: 'ok' },
}

export const CASE_DECISION = {
    NEEDS_EXAMINATION: { label: 'Требуется очный осмотр', tone: 'warn', hint: 'Врач рекомендует очный приём. Запишитесь на удобное время.' },
    NO_EXAMINATION_NEEDED: { label: 'Осмотр не требуется', tone: 'ok', hint: 'Врач считает, что очный осмотр сейчас не нужен.' },
    REFER_TO_SPECIALIST: { label: 'Направление к специалисту', tone: 'info', hint: 'Обращение передано профильному специалисту.' },
}

export const URGENCY = {
    low: { label: 'Низкая срочность', tone: 'ok' },
    medium: { label: 'Средняя срочность', tone: 'warn' },
    high: { label: 'Высокая срочность', tone: 'bad' },
}

export const APPOINTMENT_STATUS = {
    Scheduled: { label: 'Запланирован', tone: 'info' },
    Confirmed: { label: 'Подтверждён', tone: 'info' },
    Completed: { label: 'Завершён', tone: 'ok' },
    Cancelled: { label: 'Отменён', tone: 'bad' },
    'No Show': { label: 'Неявка', tone: 'bad' },
}

export const ROLE = {
    patient: 'Пациент',
    doctor: 'Врач',
    admin: 'Администратор',
}

export const SUMMARY_FIELDS = [
    ['chief_complaint', 'Основная жалоба'],
    ['symptoms', 'Симптомы'],
    ['onset_and_duration', 'Начало и длительность'],
    ['severity', 'Выраженность'],
    ['medical_history', 'Анамнез'],
    ['current_medications', 'Принимаемые препараты'],
    ['allergies', 'Аллергии'],
    ['red_flags', 'Тревожные признаки'],
    ['patient_questions', 'Вопросы пациента'],
]

export const TIME_SLOTS = [
    '09:00 - 09:30', '09:30 - 10:00', '10:00 - 10:30', '10:30 - 11:00', '11:00 - 11:30', '11:30 - 12:00',
    '14:00 - 14:30', '14:30 - 15:00', '15:00 - 15:30', '15:30 - 16:00', '16:00 - 16:30', '16:30 - 17:00',
]
