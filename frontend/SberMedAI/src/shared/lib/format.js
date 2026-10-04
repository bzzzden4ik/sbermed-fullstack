const parseDate = (value) => {
    if (!value) return null
    // Backend timestamps are UTC; SQLite may drop the offset, so treat naive values as UTC.
    const normalized = typeof value === 'string' && !/[zZ]|[+-]\d\d:?\d\d$/.test(value) && value.includes('T')
        ? `${value}Z`
        : value
    const date = new Date(normalized)
    return Number.isNaN(date.getTime()) ? null : date
}

export const formatDate = (value) => {
    const date = parseDate(value)
    return date ? date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
}

export const formatDateTime = (value) => {
    const date = parseDate(value)
    return date
        ? date.toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
        : '—'
}

export const formatTime = (value) => {
    const date = parseDate(value)
    return date ? date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : ''
}

/** "Сегодня" / "Вчера" / "Ранее" grouping used in the assistant history. */
export const dayGroup = (value) => {
    const date = parseDate(value)
    if (!date) return 'Ранее'
    const startOfToday = new Date()
    startOfToday.setHours(0, 0, 0, 0)
    const diffDays = Math.floor((startOfToday - date) / 86400000)
    if (date >= startOfToday) return 'Сегодня'
    if (diffDays < 1) return 'Вчера'
    return 'Ранее'
}

export const pluralYears = (age) => {
    const m = age % 10
    const h = age % 100
    return `${age} ${h > 10 && h < 15 ? 'лет' : m === 1 ? 'год' : m > 1 && m < 5 ? 'года' : 'лет'}`
}

export const initials = (name = '') =>
    name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join('') || '•'

const GENDERS = { male: 'Мужской', female: 'Женский', other: 'Другой' }
export const formatGender = (value) => GENDERS[value?.toLowerCase?.()] || value || '—'
