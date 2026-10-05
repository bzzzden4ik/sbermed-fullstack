import { useEffect } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { SiteHeader } from '@/widgets/site-header'
import { SiteFooter } from '@/shared/ui/common.jsx'
import { OrbitBackground } from '@/shared/ui/icons.jsx'
import { LEGAL_DOCUMENTS, LEGAL_LINKS, LEGAL_UPDATED, LEGAL_VERSION } from '../model/documents.js'
import './legal.css'

export function LegalPage() {
    const { doc } = useParams()
    const document = LEGAL_DOCUMENTS[doc]

    useEffect(() => {
        if (document) window.document.title = `${document.title} — SIRIUS`
        return () => { window.document.title = 'SIRIUS — университетская клиника нового поколения' }
    }, [document])

    if (!document) return <Navigate to="/legal/terms" replace />

    return (
        <div className="page p-legal">
            <SiteHeader links={[['/', 'Главная']]} />
            <main>
                <div className="lg-hero">
                    <OrbitBackground />
                    <div className="wrap">
                        <div className="eyebrow">Правовая информация</div>
                        <h1>{document.title}</h1>
                        <p className="lg-lead">{document.lead}</p>
                        <div className="lg-meta">
                            <span>Редакция от {LEGAL_UPDATED}</span>
                            <span>Версия {LEGAL_VERSION}</span>
                            <button className="alink" onClick={() => window.print()}>Распечатать</button>
                        </div>
                        <nav className="tabs lg-tabs" aria-label="Документы">
                            {LEGAL_LINKS.map(([key, label]) => (
                                <Link key={key} to={`/legal/${key}`} className={key === doc ? 'on' : undefined} aria-current={key === doc ? 'page' : undefined}>{label}</Link>
                            ))}
                        </nav>
                    </div>
                </div>

                <div className="wrap lg-body">
                    <aside className="lg-toc" aria-label="Содержание">
                        <div className="lg-toc-t">Содержание</div>
                        <ol>
                            {document.sections.map((section) => (
                                <li key={section.id}><a href={`#${section.id}`}>{section.title}</a></li>
                            ))}
                        </ol>
                    </aside>
                    <article className="lg-doc">
                        <p className="lg-draft">
                            Проект документа. Реквизиты в квадратных скобках будут заменены на действующие; текст подлежит проверке юристом.
                        </p>
                        {document.sections.map((section, index) => (
                            <section key={section.id} id={section.id} className="lg-sec">
                                <h2><span>{index + 1}.</span> {section.title}</h2>
                                {section.list && (
                                    <ul>{section.list.map((item, i) => <li key={i}>{item}</li>)}</ul>
                                )}
                                {section.paragraphs?.map((text, i) => <p key={i}>{text}</p>)}
                            </section>
                        ))}
                    </article>
                </div>
            </main>
            <SiteFooter />
        </div>
    )
}
