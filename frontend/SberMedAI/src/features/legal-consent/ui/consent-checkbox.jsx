import { Link } from 'react-router-dom'
import './consent-checkbox.css'

const DocLink = ({ to, children }) => (
    <Link to={to} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>{children}</Link>
)

/** Required consent to the platform's legal documents (they open in a new tab so the form is not lost). */
export const ConsentCheckbox = ({ checked, onChange, id = 'consent' }) => (
    <label className={`consent${checked ? ' on' : ''}`} htmlFor={id}>
        <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} required />
        <span className="consent-box" aria-hidden="true">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5 10 17.5 19 7" /></svg>
        </span>
        <span className="consent-text">
            Я принимаю <DocLink to="/legal/terms">Пользовательское соглашение</DocLink>, ознакомлен(а)
            с <DocLink to="/legal/privacy">Политикой конфиденциальности</DocLink> и даю{' '}
            <DocLink to="/legal/consent">согласие на обработку персональных данных</DocLink>, включая сведения
            о состоянии здоровья и их обработку ИИ-ассистентом.
        </span>
    </label>
)
