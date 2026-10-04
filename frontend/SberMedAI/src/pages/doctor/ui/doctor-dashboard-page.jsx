import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSession } from '@/entities/session'
import { listCases } from '@/entities/case'
import { SiteHeader } from '@/widgets/site-header'
import { Loader, SiteFooter, StatusChip } from '@/shared/ui/common.jsx'
import { ArrowRightIcon, OrbitBackground } from '@/shared/ui/icons.jsx'
import { useToast } from '@/shared/ui/toast-context.js'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { CASE_DECISION, CASE_STATUS, URGENCY } from '@/shared/lib/labels.js'
import { formatDateTime, initials, pluralYears } from '@/shared/lib/format.js'
import '../../profile/ui/cabinet.css'

const ACTIVE = ['READY_FOR_DOCTOR', 'REFERRED', 'UNDER_REVIEW']
const URGENCY_ORDER = { high: 0, medium: 1, low: 2 }
const FILTERS = [['active', 'Ожидают решения'], ['resolved', 'Решённые'], ['all', 'Все']]

export function DoctorDashboardPage() {
    const { user, profile } = useSession()
    const toast = useToast()
    const [cases, setCases] = useState(null)
    const [filter, setFilter] = useState('active')

    // Stored cases and summaries only — the dashboard never triggers AI.
    useEffect(() => {
        listCases().then(setCases).catch((err) => { setCases([]); toast.error(getErrorMessage(err)) })
    }, [toast])

    // Cases transferred away by this doctor stay readable but are not this doctor's queue.
    const mine = useMemo(() => (cases || []).filter((c) => c.doctor?.id === profile?.id), [cases, profile])
    const visible = useMemo(() => {
        const list = filter === 'all' ? cases || []
            : filter === 'resolved' ? mine.filter((c) => c.status === 'RESOLVED')
                : mine.filter((c) => ACTIVE.includes(c.status))
        return filter === 'active'
            ? [...list].sort((a, b) => (URGENCY_ORDER[a.urgency] ?? 3) - (URGENCY_ORDER[b.urgency] ?? 3))
            : list
    }, [cases, mine, filter])

    const counts = {
        fresh: mine.filter((c) => ['READY_FOR_DOCTOR', 'REFERRED'].includes(c.status)).length,
        review: mine.filter((c) => c.status === 'UNDER_REVIEW').length,
        urgent: mine.filter((c) => ACTIVE.includes(c.status) && c.urgency === 'high').length,
        resolved: mine.filter((c) => c.status === 'RESOLVED').length,
    }

    return (
        <div className="page p-cabinet">
            <SiteHeader />
            <main>
                <div className="hero">
                    <OrbitBackground />
                    <div className="wrap">
                        <div className="crumbs"><span>Кабинет врача</span><span>/</span><b>Обращения</b></div>
                        <div className="who">
                            <div className="ava" aria-hidden="true">{initials(profile?.full_name || user.full_name)}</div>
                            <div>
                                <h1>{profile?.full_name || user.full_name}</h1>
                                <div className="sub">
                                    <span className="chip">Врач</span>
                                    {profile && <span>{profile.specialization}</span>}
                                    {profile && <span>{profile.qualification}</span>}
                                    <span>{user.email}</span>
                                </div>
                                {!profile && <div className="form-error">Профиль врача не найден. Обратитесь к администратору.</div>}
                            </div>
                        </div>
                        <div className="float"><div className="dot">✦</div><div><b>Сводки готовит ИИ-ассистент</b><small>Решение всегда за врачом</small></div></div>
                    </div>
                </div>

                <section className="s bg2">
                    <div className="wrap stats">
                        <div><button onClick={() => setFilter('active')}><div className="l">Новые</div><b>{cases ? counts.fresh : '—'}</b></button><span className="st info">ждут рассмотрения</span></div>
                        <div><button onClick={() => setFilter('active')}><div className="l">В работе</div><b>{cases ? counts.review : '—'}</b></button><span className="st warn">на рассмотрении</span></div>
                        <div><button onClick={() => setFilter('active')}><div className="l">Срочные</div><b>{cases ? counts.urgent : '—'}</b></button><span className="st bad">высокая срочность</span></div>
                        <div><button onClick={() => setFilter('resolved')}><div className="l">Решено</div><b>{cases ? counts.resolved : '—'}</b></button><span className="st ok">пациенты уведомлены</span></div>
                    </div>
                </section>

                <section className="s">
                    <div className="wrap">
                        <div className="shead">
                            <h2>Обращения <i>пациентов</i></h2>
                            <div className="tabs" role="tablist">
                                {FILTERS.map(([value, label]) => (
                                    <button key={value} role="tab" aria-selected={filter === value} className={filter === value ? 'on' : ''} onClick={() => setFilter(value)}>{label}</button>
                                ))}
                            </div>
                        </div>
                        {cases === null ? <Loader /> : visible.length === 0 ? (
                            <div className="empty">
                                <h3>{filter === 'active' ? 'Новых обращений нет' : 'Здесь пока пусто'}</h3>
                                Обращения появятся, когда пациенты отправят их через ИИ-ассистента.
                            </div>
                        ) : (
                            <ul className="vis">
                                {visible.map((c) => (
                                    <li key={c.id}>
                                        <Link className="vrow" to={`/doctor/cases/${c.id}`}>
                                            <span className="d">№{c.id} · {formatDateTime(c.submitted_at || c.created_at)}</span>
                                            <h3>{c.complaint}<small>{c.patient.full_name} · {pluralYears(c.patient.age)}{c.doctor?.id !== profile?.id && c.doctor ? ` · передано: ${c.doctor.full_name}` : ''}</small></h3>
                                            <span className="chips">
                                                <StatusChip map={CASE_STATUS} value={c.status} />
                                                {c.status === 'RESOLVED'
                                                    ? <StatusChip map={CASE_DECISION} value={c.decision} />
                                                    : <StatusChip map={URGENCY} value={c.urgency} />}
                                            </span>
                                            <span className="dl"><ArrowRightIcon /></span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </section>
            </main>
            <SiteFooter />
        </div>
    )
}
