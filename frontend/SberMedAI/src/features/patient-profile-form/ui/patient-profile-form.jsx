import { useState } from 'react'
import { useSession } from '@/entities/session'
import { createPatientProfile, updatePatientProfile } from '@/entities/patient/api/patient-api.js'
import { getErrorMessage } from '@/shared/api/axios-client.js'

const BLOOD_GROUPS = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'Не знаю']

/** Creates the patient's own profile (onboarding) or updates it; the backend ties it to the signed-in account. */
export const PatientProfileForm = ({ onSaved, submitLabel = 'Сохранить' }) => {
    const { user, profile, setProfile } = useSession()
    const [form, setForm] = useState(() => ({
        full_name: profile?.full_name || user?.full_name || '',
        age: profile?.age ?? '',
        gender: profile?.gender || '',
        phone_number: profile?.phone_number || '',
        address: profile?.address || '',
        blood_group: profile?.blood_group || '',
        emergency_contact: profile?.emergency_contact || '',
    }))
    const [error, setError] = useState('')
    const [pending, setPending] = useState(false)

    const field = (name) => ({
        id: `pf-${name}`,
        name,
        value: form[name],
        onChange: (e) => setForm((f) => ({ ...f, [name]: e.target.value })),
    })

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (pending) return
        setPending(true)
        setError('')
        const payload = { ...form, age: Number(form.age) }
        try {
            const saved = profile
                ? await updatePatientProfile(profile.id, payload)
                : await createPatientProfile(payload)
            setProfile(saved)
            onSaved?.(saved)
        } catch (err) {
            setError(getErrorMessage(err))
            setPending(false)
        }
    }

    return (
        <form onSubmit={handleSubmit}>
            {error && <div className="form-error" role="alert">{error}</div>}
            <div className="fg">
                <label htmlFor="pf-full_name">Имя и фамилия</label>
                <input className="input" required minLength={2} autoComplete="name" {...field('full_name')} />
            </div>
            <div className="grid2">
                <div className="fg">
                    <label htmlFor="pf-age">Возраст</label>
                    <input className="input" type="number" required min={1} max={149} {...field('age')} />
                </div>
                <div className="fg">
                    <label htmlFor="pf-gender">Пол</label>
                    <select className="input" required {...field('gender')}>
                        <option value="" disabled>Выберите</option>
                        <option value="female">Женский</option>
                        <option value="male">Мужской</option>
                    </select>
                </div>
                <div className="fg">
                    <label htmlFor="pf-phone_number">Телефон</label>
                    <input className="input" type="tel" required minLength={5} autoComplete="tel" placeholder="+7 900 123-45-67" {...field('phone_number')} />
                </div>
                <div className="fg">
                    <label htmlFor="pf-blood_group">Группа крови</label>
                    <select className="input" required {...field('blood_group')}>
                        <option value="" disabled>Выберите</option>
                        {BLOOD_GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}
                    </select>
                </div>
            </div>
            <div className="fg">
                <label htmlFor="pf-address">Адрес</label>
                <input className="input" required minLength={5} autoComplete="street-address" placeholder="г. Москва, ул. Ленина, д. 10" {...field('address')} />
            </div>
            <div className="fg">
                <label htmlFor="pf-emergency_contact">Экстренный контакт</label>
                <input className="input" required minLength={5} placeholder="Анна Иванова, +7 900 987-65-43" {...field('emergency_contact')} />
            </div>
            <button type="submit" className="btn" disabled={pending} style={{ width: '100%', marginTop: 6 }}>
                {pending ? 'Сохраняем…' : submitLabel}
            </button>
        </form>
    )
}
