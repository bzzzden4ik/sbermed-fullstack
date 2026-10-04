import { useEffect, useState } from 'react'
import { listDoctors } from '@/entities/doctor/api/doctor-api.js'
import { bookAppointment } from '@/entities/appointment/api/appointment-api.js'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { TIME_SLOTS } from '@/shared/lib/labels.js'

const today = () => {
    const d = new Date()
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
    return d.toISOString().slice(0, 10)
}

/** Patient books an appointment through the existing /appointments endpoint (the backend resolves the patient). */
export const BookAppointmentForm = ({ initialDoctorId, initialReason = '', onBooked }) => {
    const [doctors, setDoctors] = useState([])
    const [form, setForm] = useState({
        doctor_id: initialDoctorId ? String(initialDoctorId) : '',
        appointment_date: '',
        time_slot: '',
        reason_for_visit: initialReason,
    })
    const [error, setError] = useState('')
    const [pending, setPending] = useState(false)

    useEffect(() => {
        listDoctors({ sort_by: 'full_name' }).then(setDoctors).catch(() => setDoctors([]))
    }, [])

    const field = (name) => ({
        id: `ba-${name}`,
        value: form[name],
        onChange: (e) => setForm((f) => ({ ...f, [name]: e.target.value })),
    })

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (pending) return
        setPending(true)
        setError('')
        try {
            const appointment = await bookAppointment({ ...form, doctor_id: Number(form.doctor_id) })
            onBooked?.(appointment)
        } catch (err) {
            setError(getErrorMessage(err))
            setPending(false)
        }
    }

    return (
        <form onSubmit={handleSubmit}>
            {error && <div className="form-error" role="alert">{error}</div>}
            <div className="fg">
                <label htmlFor="ba-doctor_id">Врач</label>
                <select className="input" required {...field('doctor_id')}>
                    <option value="" disabled>Выберите врача</option>
                    {doctors.map((d) => <option key={d.id} value={d.id}>{d.full_name} — {d.specialization}</option>)}
                </select>
            </div>
            <div className="grid2">
                <div className="fg">
                    <label htmlFor="ba-appointment_date">Дата</label>
                    <input className="input" type="date" required min={today()} {...field('appointment_date')} />
                </div>
                <div className="fg">
                    <label htmlFor="ba-time_slot">Время</label>
                    <select className="input" required {...field('time_slot')}>
                        <option value="" disabled>Выберите</option>
                        {TIME_SLOTS.map((slot) => <option key={slot} value={slot}>{slot}</option>)}
                    </select>
                </div>
            </div>
            <div className="fg">
                <label htmlFor="ba-reason_for_visit">Причина визита</label>
                <textarea className="input" required minLength={3} maxLength={500} {...field('reason_for_visit')} />
            </div>
            <button type="submit" className="btn" disabled={pending} style={{ width: '100%' }}>
                {pending ? 'Записываем…' : 'Записаться'}
            </button>
        </form>
    )
}
