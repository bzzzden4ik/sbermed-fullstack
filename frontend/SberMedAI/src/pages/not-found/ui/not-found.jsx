import { Link } from 'react-router-dom'
import { SiteHeader } from '@/widgets/site-header'
import { OrbitBackground } from '@/shared/ui/icons.jsx'

export const NotFound = () => {
    return (
        <div className="page" style={{ display: 'flex', flexDirection: 'column' }}>
            <SiteHeader links={[['/', 'Главная']]} />
            <main style={{ position: 'relative', overflow: 'hidden', flex: 1, display: 'grid', alignItems: 'center' }}>
                <OrbitBackground />
                <div className="wrap" style={{ position: 'relative', padding: '80px 0' }}>
                    <div className="eyebrow">Ошибка 404</div>
                    <h1>Страница <i>не найдена</i></h1>
                    <p className="muted" style={{ margin: '24px 0 32px', maxWidth: 420 }}>Возможно, ссылка устарела. Вернитесь на главную или в личный кабинет.</p>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                        <Link className="btn" to="/">На главную</Link>
                        <Link className="btn ghost" to="/cabinet">Личный кабинет</Link>
                    </div>
                </div>
            </main>
        </div>
    )
}
