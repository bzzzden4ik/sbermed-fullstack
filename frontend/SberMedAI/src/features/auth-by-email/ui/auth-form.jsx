import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSession, homePathFor } from '@/entities/session'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { useToast } from '@/shared/ui/toast-context.js'

export function AuthForm() {
    const [mode, setMode] = useState('login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [fullName, setFullName] = useState('')
    const [error, setError] = useState('')
    const [pending, setPending] = useState(false)

    const navigate = useNavigate()
    const location = useLocation()
    const { login, register } = useSession()
    const toast = useToast()
    const isLogin = mode === 'login'

    const switchMode = (next) => {
        setMode(next)
        setError('')
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (pending) return
        setError('')
        setPending(true)
        try {
            const user = isLogin
                ? await login(email.trim(), password)
                : await register(email.trim(), password, fullName.trim())
            const from = location.state?.from
            // Only follow the redirect if it belongs to this role's interface.
            const allowed = user.role === 'patient'
                ? from && !from.startsWith('/doctor') && !from.startsWith('/admin')
                : from?.startsWith(homePathFor(user.role))
            navigate(isLogin ? (allowed ? from : homePathFor(user.role)) : '/onboarding', {
                replace: true,
                state: isLogin ? undefined : { from: allowed ? from : undefined },
            })
        } catch (err) {
            setError(err.response?.status === 401 ? 'Неверная почта или пароль' : getErrorMessage(err))
            setPending(false)
        }
    }

    return (
        <form className="auth-form" onSubmit={handleSubmit} noValidate={false}>
            <div className="tabs" role="tablist">
                <button type="button" role="tab" aria-selected={isLogin} className={isLogin ? 'on' : ''} onClick={() => switchMode('login')}>Вход</button>
                <button type="button" role="tab" aria-selected={!isLogin} className={!isLogin ? 'on' : ''} onClick={() => switchMode('register')}>Регистрация</button>
            </div>
            <h2>{isLogin ? <>Добро <i>пожаловать</i></> : <>Создайте <i>кабинет</i></>}</h2>
            <p className="muted">
                {isLogin
                    ? 'Войдите, чтобы открыть личный кабинет, обращения и ИИ-ассистента.'
                    : 'Регистрация для пациентов. Учётные записи врачей выдаёт администратор клиники.'}
            </p>

            {error && <div className="form-error" role="alert">{error}</div>}

            {!isLogin && (
                <div className="fg">
                    <label htmlFor="auth-name">Имя и фамилия</label>
                    <input id="auth-name" className="input" autoComplete="name" required minLength={2}
                        placeholder="Мария Иванова" value={fullName} onChange={(e) => setFullName(e.target.value)} />
                </div>
            )}
            <div className="fg">
                <label htmlFor="auth-email">Электронная почта</label>
                <input id="auth-email" className="input" type="email" autoComplete="email" required
                    placeholder="m.ivanova@example.ru" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="fg">
                <label htmlFor="auth-password">Пароль</label>
                <input id="auth-password" className="input" type="password" required minLength={6}
                    autoComplete={isLogin ? 'current-password' : 'new-password'}
                    placeholder={isLogin ? 'Ваш пароль' : 'Не менее 6 символов'} value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <button type="submit" className="btn" disabled={pending} style={{ width: '100%', marginTop: 8 }}>
                {pending ? 'Подождите…' : isLogin ? 'Войти' : 'Зарегистрироваться'}
            </button>
            <div className="auth-or"><span>или</span></div>
            <button
                type="button"
                className="btn ghost gosuslugi"
                onClick={() => {
                    // Placeholder: ESIA (Госуслуги) sign-in is not connected yet.
                    switchMode('register')
                    toast.show('Вход через Госуслуги скоро будет доступен. Пока, пожалуйста, зарегистрируйтесь самостоятельно.')
                }}
            >
                Войти через Госуслуги
                <span className="soon">скоро</span>
            </button>
        </form>
    )
}
