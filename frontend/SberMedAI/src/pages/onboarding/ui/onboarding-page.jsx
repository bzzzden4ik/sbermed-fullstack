import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useSession } from '@/entities/session'
import { PatientProfileForm } from '@/features/patient-profile-form'
import { SiteHeader } from '@/widgets/site-header'
import { OrbitBackground } from '@/shared/ui/icons.jsx'
import '../../auth/ui/auth.css'

export const OnboardingPage = () => {
    const { profile, user } = useSession()
    const navigate = useNavigate()
    const location = useLocation()
    const next = location.state?.from || '/profile'

    if (profile) return <Navigate to={next} replace />

    return (
        <div className="page p-auth">
            <SiteHeader />
            <main className="auth-hero">
                <OrbitBackground />
                <div className="wrap auth-grid">
                    <div className="auth-intro">
                        <div className="eyebrow">Шаг 2 из 2</div>
                        <h1>Расскажите <i>о себе</i></h1>
                        <p className="muted" style={{ marginTop: 24, maxWidth: 420 }}>
                            {user?.full_name}, эти данные врач увидит вместе с вашим обращением. Их можно изменить в личном кабинете.
                        </p>
                    </div>
                    <div className="auth-card">
                        <PatientProfileForm submitLabel="Создать кабинет" onSaved={() => navigate(next, { replace: true })} />
                    </div>
                </div>
            </main>
        </div>
    )
}
