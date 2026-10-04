import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useSession } from '@/entities/session'
import { listCases, CaseSummary, AiDisclaimer } from '@/entities/case'
import { listAppointments, updateAppointment } from '@/entities/appointment/api/appointment-api.js'
import { PatientProfileForm } from '@/features/patient-profile-form'
import { BookAppointmentForm } from '@/features/book-appointment'
import { SiteHeader } from '@/widgets/site-header'
import { Loader, Modal, SiteFooter, StatusChip } from '@/shared/ui/common.jsx'
import { ArrowRightIcon, OrbitBackground } from '@/shared/ui/icons.jsx'
import { useToast } from '@/shared/ui/toast-context.js'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { APPOINTMENT_STATUS, CASE_DECISION, CASE_STATUS, URGENCY } from '@/shared/lib/labels.js'
import { formatDate, formatGender, initials, pluralYears } from '@/shared/lib/format.js'
import './cabinet.css'

const ChevronDown = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
)

const CaseDetail = ({ item, onBook }) => {
    const decision = item.decision && CASE_DECISION[item.decision]
    const isFinal = item.status === 'RESOLVED'
    return (
        <div className="detail">
            {item.related_case_id && (
                <p className="muted" style={{ marginTop: 4 }}>
                    Повторное обращение по <Link className="alink" to={`/profile?case=${item.related_case_id}#cases`}>обращению №{item.related_case_id}</Link>
                </p>
            )}
            <h4>Решение врача</h4>
            {decision ? (
                <div className="decision">
                    <b>{isFinal ? decision.label : 'Направлено специалисту'}</b>
                    <p>{isFinal ? decision.hint : `Специалист ${item.doctor?.full_name} (${item.doctor?.specialization}) изучит обращение и примет решение.`}</p>
                    {item.doctor_comment && <blockquote>{item.doctor_comment}</blockquote>}
                    {item.referred_from_doctor && <p>Направил: {item.referred_from_doctor.full_name}</p>}
                </div>
            ) : (
                <div className="decision wait">
                    {item.status === 'AI_COLLECTING' || item.status === 'OPEN'
                        ? 'Обращение ещё не отправлено — продолжите диалог с ассистентом и подтвердите отправку.'
                        : `Врач ${item.doctor?.full_name || ''} изучает обращение. Мы пришлём уведомление и письмо, когда решение будет принято.`}
                </div>
            )}

            {item.ai_summary && (
                <>
                    <h4>Сводка для врача</h4>
                    <CaseSummary summary={item.ai_summary} />
                    <AiDisclaimer />
                </>
            )}

            <div className="acts">
                {item.decision === 'NEEDS_EXAMINATION' && isFinal && (
                    <button className="btn" onClick={() => onBook(item)}>Записаться на приём <ArrowRightIcon /></button>
                )}
                {item.conversation_id && (
                    <Link className="btn ghost" to={`/assistant/${item.conversation_id}`}>
                        {item.status === 'AI_COLLECTING' || item.status === 'OPEN' ? 'Продолжить диалог' : 'Открыть переписку'}
                    </Link>
                )}
            </div>
        </div>
    )
}

export function ProfilePage() {
    const { user, profile } = useSession()
    const toast = useToast()
    const navigate = useNavigate()
    const location = useLocation()
    const [params, setParams] = useSearchParams()
    const [cases, setCases] = useState(null)
    const [appointments, setAppointments] = useState(null)
    const [openCaseId, setOpenCaseId] = useState(() => Number(params.get('case')) || null)
    const [editing, setEditing] = useState(false)
    const [booking, setBooking] = useState(() => (params.get('book') ? { doctorId: Number(params.get('book')) } : null))

    // Regular API reads only: opening the cabinet never triggers AI.
    useEffect(() => {
        listCases().then(setCases).catch((err) => { setCases([]); toast.error(getErrorMessage(err)) })
        listAppointments({ sort_by: 'appointment_date', order: 'desc' }).then(setAppointments).catch(() => setAppointments([]))
    }, [toast])

    // Deep links from notifications (?case=ID#cases) and from the landing page (?book=doctorId).
    const [seenParams, setSeenParams] = useState(params.toString())
    if (seenParams !== params.toString()) {
        setSeenParams(params.toString())
        const caseId = Number(params.get('case'))
        if (caseId) setOpenCaseId(caseId)
        if (params.get('book')) setBooking({ doctorId: Number(params.get('book')) })
    }

    useEffect(() => {
        if (!location.hash || cases === null) return
        document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth' })
    }, [location.hash, cases])

    const closeBooking = () => {
        setBooking(null)
        if (params.get('book')) {
            params.delete('book')
            setParams(params, { replace: true })
        }
    }

    const onBooked = (appointment) => {
        setAppointments((list) => [appointment, ...(list || [])])
        closeBooking()
        toast.show(`Вы записаны: ${formatDate(appointment.appointment_date)}, ${appointment.time_slot}`)
        navigate('#appointments', { replace: true })
    }

    const cancelAppointment = async (appointment) => {
        if (!window.confirm(`Отменить запись ${appointment.appointment_number}?`)) return
        try {
            const updated = await updateAppointment(appointment.id, { status: 'Cancelled' })
            setAppointments((list) => list.map((a) => (a.id === updated.id ? updated : a)))
            toast.show('Запись отменена')
        } catch (err) {
            toast.error(getErrorMessage(err))
        }
    }

    const counts = {
        all: cases?.length ?? '—',
        review: cases?.filter((c) => ['READY_FOR_DOCTOR', 'REFERRED', 'UNDER_REVIEW'].includes(c.status)).length ?? '—',
        resolved: cases?.filter((c) => c.status === 'RESOLVED').length ?? '—',
        visits: appointments?.filter((a) => ['Scheduled', 'Confirmed'].includes(a.status)).length ?? '—',
    }

    return (
        <div className="page p-cabinet">
            <SiteHeader />
            <main>
                <div className="hero">
                    <OrbitBackground />
                    <div className="wrap">
                        <div className="crumbs"><span>Личный кабинет</span><span>/</span><b>Профиль</b></div>
                        <div className="who">
                            <div className="ava" aria-hidden="true">{initials(profile.full_name)}</div>
                            <div>
                                <h1>{profile.full_name}</h1>
                                <div className="sub"><span className="chip">Пациент</span><span>{user.email}</span><span>{profile.phone_number}</span></div>
                                <div className="acts">
                                    <Link className="btn" to="/assistant">Новое обращение <ArrowRightIcon /></Link>
                                    <button className="btn ghost" onClick={() => setBooking({})}>Записаться на приём</button>
                                    <button className="btn ghost" onClick={() => setEditing(true)}>Редактировать профиль</button>
                                </div>
                            </div>
                        </div>
                        <div className="float"><div className="dot">✓</div><div><b>Пациент с {formatDate(profile.created_at)}</b><small>Обращений: {counts.all}</small></div></div>
                    </div>
                </div>

                <section className="s bg2">
                    <div className="wrap">
                        <div className="shead"><h2>Мои <i>показатели</i></h2><p>Обращения и записи в клинике</p></div>
                        <div className="stats">
                            <div><div className="l">Всего обращений</div><b>{counts.all}</b><span className="st info">через ИИ-ассистента</span></div>
                            <div><div className="l">У врача</div><b>{counts.review}</b><span className="st warn">ожидают решения</span></div>
                            <div><div className="l">Решения получены</div><b>{counts.resolved}</b><span className="st ok">готово</span></div>
                            <div><div className="l">Предстоящие визиты</div><b>{counts.visits}</b><span className="st info">записи на приём</span></div>
                        </div>
                    </div>
                </section>

                <section className="s" id="cases">
                    <div className="wrap">
                        <div className="shead"><h2>Мои <i>обращения</i></h2><p>Сводки ассистента и решения врачей</p></div>
                        {cases === null ? <Loader /> : cases.length === 0 ? (
                            <div className="empty">
                                <h3>Обращений пока нет</h3>
                                Опишите ассистенту, что вас беспокоит — он подготовит обращение и передаст его врачу.
                                <div><Link className="btn" to="/assistant">Начать диалог <ArrowRightIcon /></Link></div>
                            </div>
                        ) : (
                            <ul className="vis">
                                {cases.map((item) => {
                                    const open = openCaseId === item.id
                                    return (
                                        <li key={item.id} className={Number(params.get('case')) === item.id ? 'hl' : undefined}>
                                            <button className="vrow" aria-expanded={open} onClick={() => setOpenCaseId(open ? null : item.id)}>
                                                <span className="d">№{item.id} · {formatDate(item.submitted_at || item.created_at)}</span>
                                                <h3>{item.complaint}<small>{[item.doctor && `${item.doctor.full_name}, ${item.doctor.specialization}`, item.urgency && URGENCY[item.urgency]?.label].filter(Boolean).join(' · ') || 'Сбор информации ассистентом'}</small></h3>
                                                <span className="chips">
                                                    <StatusChip map={CASE_STATUS} value={item.status} />
                                                    {item.status === 'RESOLVED' && <StatusChip map={CASE_DECISION} value={item.decision} />}
                                                </span>
                                                <span className="dl"><ChevronDown /></span>
                                            </button>
                                            {open && <CaseDetail item={item} onBook={(c) => setBooking({ doctorId: c.doctor?.id, reason: c.complaint })} />}
                                        </li>
                                    )
                                })}
                            </ul>
                        )}
                    </div>
                </section>

                <section className="s bg2" id="appointments">
                    <div className="wrap">
                        <div className="shead"><h2>Записи <i>на приём</i></h2><button className="alink" onClick={() => setBooking({})}>Записаться →</button></div>
                        {appointments === null ? <Loader /> : appointments.length === 0 ? (
                            <div className="empty">
                                <h3>Записей нет</h3>
                                Если врач рекомендует очный осмотр, запишитесь на удобное время.
                            </div>
                        ) : (
                            <ul className="vis">
                                {appointments.map((a) => (
                                    <li key={a.id}>
                                        <div className="vrow static">
                                            <span className="d">{formatDate(a.appointment_date)} · {a.time_slot}</span>
                                            <h3>{a.doctor.full_name}<small>{a.doctor.specialization} · {a.reason_for_visit}</small></h3>
                                            <span className="chips"><StatusChip map={APPOINTMENT_STATUS} value={a.status} /></span>
                                            {['Scheduled', 'Confirmed'].includes(a.status)
                                                ? <button className="btn sm ghost" onClick={() => cancelAppointment(a)}>Отменить</button>
                                                : <span />}
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </section>

                <section className="s">
                    <div className="wrap split">
                        <div className="sticky">
                            <h2>О <i>пациенте</i></h2>
                            <p>Эти данные врач видит вместе с вашим обращением и на приёме. Если что-то изменилось, обновите профиль.</p>
                            <button className="alink" onClick={() => setEditing(true)}>Обновить данные →</button>
                        </div>
                        <div className="pr">
                            <div>Пол<b>{formatGender(profile.gender)}</b></div>
                            <div>Возраст<b>{pluralYears(profile.age)}</b></div>
                            <div>Группа крови<b>{profile.blood_group}</b></div>
                            <div>Дата регистрации<b>{formatDate(profile.created_at)}</b></div>
                            <div>Адрес<b>{profile.address || 'Не указан'}</b></div>
                            <div>Экстренный контакт<b>{profile.emergency_contact || 'Не указан'}</b></div>
                        </div>
                    </div>
                </section>
            </main>
            <SiteFooter />

            {editing && (
                <Modal title="Профиль" onClose={() => setEditing(false)}>
                    <PatientProfileForm onSaved={() => { setEditing(false); toast.show('Профиль обновлён') }} />
                </Modal>
            )}
            {booking && (
                <Modal title="Запись на приём" onClose={closeBooking}>
                    <BookAppointmentForm initialDoctorId={booking.doctorId} initialReason={booking.reason} onBooked={onBooked} />
                </Modal>
            )}
        </div>
    )
}
