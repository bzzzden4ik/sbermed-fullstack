import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { HeartLogoIcon, CloseIcon } from './icons.jsx'

export const Logo = ({ to = '/' }) => (
    <Link className="logo" to={to}>
        <i><HeartLogoIcon /></i>SIRIUS
    </Link>
)

export const Loader = ({ label = 'Загрузка' }) => (
    <div className="loader" role="status" aria-label={label}><i></i><i></i><i></i></div>
)

/** Chip for an enum value looked up in a labels map ({ label, tone }). */
export const StatusChip = ({ map, value }) => {
    if (!value) return null
    const item = map[value] || { label: value, tone: '' }
    return <span className={`st ${item.tone}`}>{item.label}</span>
}

export const Modal = ({ title, onClose, children, width }) => {
    useEffect(() => {
        const onKey = (e) => { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [onClose])

    return (
        <div className="mod" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
            <div className="box" role="dialog" aria-modal="true" aria-label={title} style={width ? { width: `min(${width}px, 100%)` } : undefined}>
                <div className="mt">
                    <span>{title}</span>
                    <button className="ibtn" type="button" onClick={onClose} aria-label="Закрыть"><CloseIcon /></button>
                </div>
                {children}
            </div>
        </div>
    )
}

export const SiteFooter = () => (
    <footer className="site-footer">
        <div className="wrap">
            <p>Имеются противопоказания, необходима консультация специалиста. ИИ-ассистент собирает информацию для врача и не ставит диагнозов. © 2026 SIRIUS.</p>
            <p className="sf-links">
                <Link to="/legal/terms">Соглашение</Link> · <Link to="/legal/privacy">Конфиденциальность</Link> · <Link to="/legal/consent">Согласие на обработку данных</Link>
                <br />+7 915 163-07-01
            </p>
        </div>
    </footer>
)
