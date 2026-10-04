import { useEffect, useState } from 'react'
import { decideCase } from '@/entities/case'
import { listDoctors } from '@/entities/doctor/api/doctor-api.js'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { CASE_DECISION } from '@/shared/lib/labels.js'
import './case-decision.css'

const OPTIONS = [
    ['NEEDS_EXAMINATION', 'Пациент получит рекомендацию записаться на очный приём.'],
    ['NO_EXAMINATION_NEEDED', 'Очный визит не нужен. Объясните рекомендации в комментарии.'],
    ['REFER_TO_SPECIALIST', 'Передать обращение другому врачу — он примет окончательное решение.'],
]

/** The doctor's final decision. Saving it notifies the patient in-app and by email (done by the backend). */
export const CaseDecisionForm = ({ caseItem, currentDoctorId, onDecided }) => {
    const [decision, setDecision] = useState('')
    const [comment, setComment] = useState('')
    const [referredDoctorId, setReferredDoctorId] = useState('')
    const [doctors, setDoctors] = useState([])
    const [error, setError] = useState('')
    const [pending, setPending] = useState(false)

    useEffect(() => {
        listDoctors({ sort_by: 'specialization', limit: 1000 })
            .then((list) => setDoctors(list.filter((d) => d.id !== currentDoctorId && d.user_id)))
            .catch(() => setDoctors([]))
    }, [currentDoctorId])

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (pending || !decision) return
        setPending(true)
        setError('')
        try {
            const updated = await decideCase(caseItem.id, {
                decision,
                comment: comment.trim() || null,
                referred_doctor_id: decision === 'REFER_TO_SPECIALIST' ? Number(referredDoctorId) : null,
            })
            onDecided(updated)
        } catch (err) {
            setError(getErrorMessage(err))
            setPending(false)
        }
    }

    return (
        <form className="decide" onSubmit={handleSubmit}>
            {error && <div className="form-error" role="alert">{error}</div>}
            <fieldset className="opts">
                <legend className="sr-only">Решение</legend>
                {OPTIONS.map(([value, hint]) => (
                    <label key={value} className={`opt${decision === value ? ' on' : ''}`}>
                        <input type="radio" name="decision" value={value} checked={decision === value} onChange={() => setDecision(value)} required />
                        <b>{CASE_DECISION[value].label}</b>
                        <span>{hint}</span>
                    </label>
                ))}
            </fieldset>

            {decision === 'REFER_TO_SPECIALIST' && (
                <div className="fg">
                    <label htmlFor="cd-doctor">Специалист</label>
                    <select id="cd-doctor" className="input" required value={referredDoctorId} onChange={(e) => setReferredDoctorId(e.target.value)}>
                        <option value="" disabled>Выберите врача</option>
                        {doctors.map((d) => <option key={d.id} value={d.id}>{d.specialization} — {d.full_name}</option>)}
                    </select>
                </div>
            )}

            <div className="fg">
                <label htmlFor="cd-comment">Комментарий для пациента{decision === 'NO_EXAMINATION_NEEDED' ? '' : ' (необязательно)'}</label>
                <textarea id="cd-comment" className="input" maxLength={4000} required={decision === 'NO_EXAMINATION_NEEDED'}
                    placeholder="Рекомендации, что подготовить к приёму, на что обратить внимание…"
                    value={comment} onChange={(e) => setComment(e.target.value)} />
            </div>

            <button type="submit" className="btn" disabled={pending || !decision}>
                {pending ? 'Сохраняем…' : 'Сохранить решение и уведомить пациента'}
            </button>
        </form>
    )
}
