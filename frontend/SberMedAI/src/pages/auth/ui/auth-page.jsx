import { AuthForm } from "@/features/auth-by-email"
import { SiteHeader } from "@/widgets/site-header"
import { OrbitBackground } from "@/shared/ui/icons.jsx"
import "./auth.css"


export const AuthPage = () => {
    return (
        <div className="page p-auth">
            <SiteHeader links={[['/', 'Главная']]} />
            <main className="auth-hero">
                <OrbitBackground />
                <div className="wrap auth-grid">
                    <div className="auth-intro">
                        <div className="eyebrow">Личный кабинет</div>
                        <h1>Ваш путь <i>к врачу</i> начинается здесь</h1>
                        <ol className="auth-steps">
                            <li>Расскажите ИИ-ассистенту, что беспокоит</li>
                            <li>Подтвердите сводку — она уйдёт профильному врачу</li>
                            <li>Получите решение врача в кабинете и на почте</li>
                        </ol>
                    </div>
                    <div className="auth-card">
                        <AuthForm />
                    </div>
                </div>
            </main>
        </div>
    )
}
