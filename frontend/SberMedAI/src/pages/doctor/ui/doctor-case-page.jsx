import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useSession } from '@/entities/session'
import { getCase, startCaseReview, CaseSummary, AiDisclaimer } from '@/entities/case'
import { CaseDecisionForm } from '@/features/case-decision'
import { SiteHeader } from '@/widgets/site-header'
import { Loader, SiteFooter, StatusChip } from '@/shared/ui/common.jsx'
import { OrbitBackground } from '@/shared/ui/icons.jsx'
import { useToast } from '@/shared/ui/toast-context.js'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { CASE_DECISION, CASE_STATUS, URGENCY } from '@/shared/lib/labels.js'
import { formatDateTime, formatGender, pluralYears } from '@/shared/lib/format.js'
import '../../profile/ui/cabinet.css'

const DECIDABLE = ['READY_FOR_DOCTOR', 'REFERRED', 'UNDER_REVIEW']

export function DoctorCasePage() {
    const { caseId } = useParams()
    const { profile } = useSession()
    const toast = useToast()
    const [item, setItem] = useState(null)
    const [error, setError] = useState('')
    const [taking, setTaking] = useState(false)

    // Reads the stored case and AI summary; nothing is regenerated.
    useEffect(() => {
        getCase(caseId).then(setItem).catch((err) => setError(getErrorMessage(err, 'Обращение не найдено')))
    }, [caseId])

    const takeIntoWork = async () => {
        setTaking(true)
        try {
            setItem(await startCaseReview(item.id))
        } catch (err) {
            toast.error(getErrorMessage(err))
        } finally {
            setTaking(false)
        }
    }

    const onDecided = (updated) => {
        setItem(updated)
        toast.show(updated.status === 'REFERRED'
            ? `Обращение передано: ${updated.doctor.full_name}. Пациент уведомлён.`
            : 'Решение сохранено. Пациент получит уведомление и письмо.')
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    const isAssigned = item && profile && item.doctor?.id === profile.id
    const canDecide = isAssigned && DECIDABLE.includes(item.status)
    const patient = item?.patient

    return (
        <div className="page p-cabinet">
            <SiteHeader />
            <main>
                {error ? (
                    <div className="wrap" style={{ padding: '80px 0' }}>
                        <div className="empty"><h3>{error}</h3><Link className="btn" to="/doctor">К списку обращений</Link></div>
                    </div>
                ) : !item ? <Loader /> : (
                    <>
                        <div className="hero">
                            <OrbitBackground />
                            <div className="wrap">
                                <div className="crumbs"><Link to="/doctor">Обращения</Link><span>/</span><b>№{item.id}</b></div>
                                <div className="sub" style={{ marginTop: 0 }}>
                                    <StatusChip map={CASE_STATUS} value={item.status} />
                                    <StatusChip map={URGENCY} value={item.urgency} />
                                    {item.specialization && <span>Профиль: {item.specialization}</span>}
                                    <span>Отправлено {formatDateTime(item.submitted_at)}</span>
                                </div>
                                <h1 style={{ fontSize: 'clamp(36px, 5vw, 72px)', maxWidth: '20ch' }}>{item.complaint}</h1>
                                {item.referred_from_doctor && (
                                    <p className="muted" style={{ marginTop: 18 }}>
                                        Направлено врачом {item.referred_from_doctor.full_name} ({item.referred_from_doctor.specialization})
                                        {isAssigned ? '' : ` → ${item.doctor?.full_name}`}
                                    </p>
                                )}
                                {isAssigned && ['READY_FOR_DOCTOR', 'REFERRED'].includes(item.status) && (
                                    <div className="acts" style={{ marginTop: 28 }}>
                                        <button className="btn" onClick={takeIntoWork} disabled={taking}>Взять в работу</button>
                                    </div>
                                )}
                            </div>
                        </div>

                        <section className="s bg2">
                            <div className="wrap split">
                                <div className="sticky">
                                    <h2>Пациент</h2>
                                    <p>{patient.full_name}, {pluralYears(patient.age)}. Данные из профиля пациента.</p>
                                </div>
                                <div className="pr">
                                    <div>ФИО<b>{patient.full_name}</b></div>
                                    <div>Возраст<b>{pluralYears(patient.age)}</b></div>
                                    <div>Пол<b>{formatGender(patient.gender)}</b></div>
                                    <div>Группа крови<b>{patient.blood_group}</b></div>
                                    <div>Телефон<b>{patient.phone_number}</b></div>
                                    <div>Экстренный контакт<b>{patient.emergency_contact}</b></div>
                                    <div style={{ gridColumn: '1 / -1' }}>Адрес<b>{patient.address}</b></div>
                                </div>
                            </div>
                        </section>

                        <section className="s">
                            <div className="wrap">
                                <div className="shead"><h2>Сводка <i>ассистента</i></h2><p>Структурировано ИИ по словам пациента</p></div>
                                <CaseSummary summary={item.ai_summary} />
                                <AiDisclaimer />
                            </div>
                        </section>

                        <section className="s bg2" id="decision">
                            <div className="wrap">
                                <div className="shead"><h2>Решение <i>врача</i></h2><p>Пациент получит уведомление и письмо</p></div>
                                {canDecide ? (
                                    <CaseDecisionForm caseItem={item} currentDoctorId={profile.id} onDecided={onDecided} />
                                ) : item.decision ? (
                                    <div className="decision">
                                        <b>{CASE_DECISION[item.decision]?.label}</b>
                                        {item.status === 'REFERRED' || (item.decision === 'REFER_TO_SPECIALIST' && !isAssigned)
                                            ? <p>Передано: {item.doctor?.full_name} ({item.doctor?.specialization})</p>
                                            : <p>{item.resolved_at ? `Решение принято ${formatDateTime(item.resolved_at)}` : ''}</p>}
                                        {item.doctor_comment && <blockquote>{item.doctor_comment}</blockquote>}
                                    </div>
                                ) : (
                                    <div className="decision wait">Обращение ведёт {item.doctor?.full_name}.</div>
                                )}
                            </div>
                        </section>
                    </>
                )}
            </main>
            <SiteFooter />
        </div>
    )
}
