import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useSession } from '@/entities/session'
import { ConsentCheckbox } from '@/features/legal-consent'
import { SiteHeader } from '@/widgets/site-header'
import { OrbitBackground } from '@/shared/ui/icons.jsx'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import '../../auth/ui/auth.css'

/** One-time screen for patients who registered before consent was recorded (or after the documents changed). */
export function ConsentPage() {
    const { user, acceptTerms, logout } = useSession()
    const navigate = useNavigate()
    const location = useLocation()
    const next = location.state?.from || '/profile'
    const [accepted, setAccepted] = useState(false)
    const [pending, setPending] = useState(false)
    const [error, setError] = useState('')

    if (!user.needs_consent) return <Navigate to={next} replace />

    const submit = async (e) => {
        e.preventDefault()
        if (!accepted || pending) return
        setPending(true)
        setError('')
        try {
            await acceptTerms()
            navigate(next, { replace: true })
        } catch (err) {
            setError(getErrorMessage(err))
            setPending(false)
        }
    }

    return (
        <div className="page p-auth">
            <SiteHeader />
            <main className="auth-hero">
                <OrbitBackground />
                <div className="wrap auth-grid">
                    <div className="auth-intro">
                        <div className="eyebrow">Правовая информация</div>
                        <h1>Ещё один <i>шаг</i></h1>
                        <p className="muted" style={{ marginTop: 24, maxWidth: 440 }}>
                            {user.full_name}, мы обновили правила работы платформы. Чтобы продолжить пользоваться личным кабинетом
                            и ИИ-ассистентом, ознакомьтесь с документами и подтвердите согласие.
                        </p>
                    </div>
                    <form className="auth-card auth-form" onSubmit={submit}>
                        <h2>Документы <i>платформы</i></h2>
                        <p className="muted">Каждый документ откроется в новой вкладке.</p>
                        <ul className="consent-docs">
                            <li><Link to="/legal/terms" target="_blank" rel="noopener noreferrer">Пользовательское соглашение</Link></li>
                            <li><Link to="/legal/privacy" target="_blank" rel="noopener noreferrer">Политика конфиденциальности</Link></li>
                            <li><Link to="/legal/consent" target="_blank" rel="noopener noreferrer">Согласие на обработку персональных данных</Link></li>
                        </ul>
                        {error && <div className="form-error" role="alert">{error}</div>}
                        <ConsentCheckbox checked={accepted} onChange={setAccepted} id="consent-page" />
                        <button type="submit" className="btn" disabled={!accepted || pending} style={{ width: '100%', marginTop: 14 }}>
                            {pending ? 'Сохраняем…' : 'Принять и продолжить'}
                        </button>
                        <button type="button" className="alink" style={{ marginTop: 16 }} onClick={() => { logout(); navigate('/') }}>
                            Выйти без принятия
                        </button>
                    </form>
                </div>
            </main>
        </div>
    )
}
