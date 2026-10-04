import { SUMMARY_FIELDS } from '@/shared/lib/labels.js'
import './case.css'

/** Structured AI pre-consultation summary. It is stored with the case, so rendering it never calls the AI. */
export const CaseSummary = ({ summary, compact = false }) => {
    if (!summary) {
        return <p className="muted">Сводка ещё не сформирована — ассистент собирает информацию.</p>
    }
    const rows = SUMMARY_FIELDS
        .filter(([key]) => !compact || key !== 'chief_complaint')
        .map(([key, label]) => [key, label, summary[key]])
        .filter(([, , value]) => (Array.isArray(value) ? value.length : value))

    return (
        <dl className="csum">
            {rows.map(([key, label, value]) => (
                <div key={key} className={key === 'red_flags' ? 'flag' : undefined}>
                    <dt>{label}</dt>
                    <dd>
                        {Array.isArray(value)
                            ? <ul>{value.map((item, idx) => <li key={idx}>{item}</li>)}</ul>
                            : value}
                    </dd>
                </div>
            ))}
        </dl>
    )
}

export const AiDisclaimer = () => (
    <p className="ai-note">Сводка подготовлена ИИ-ассистентом по словам пациента. Это не диагноз — решение принимает врач.</p>
)
