import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSession, homePathFor } from '@/entities/session'
import { listDoctors } from '@/entities/doctor/api/doctor-api.js'
import { SiteHeader } from '@/widgets/site-header'
import { Logo } from '@/shared/ui/common.jsx'
import { ArrowRightIcon, ArrowUpRightIcon } from '@/shared/ui/icons.jsx'
import { initials } from '@/shared/lib/format.js'
import { mediaUrl } from '@/shared/api/axios-client.js'
import './landing.css'

const LANDING_LINKS = [['#services', 'Направления'], ['#doctors', 'Врачи'], ['#about', 'О нас'], ['#ai', 'ИИ-ассистент'], ['#contacts', 'Контакты']]

const DEPARTMENTS = [
    ['Офтальмология', 'Диагностика зрения, лечение и коррекция'],
    ['Кардиология', 'Сердце и сосуды: обследование и профилактика'],
    ['Неврология', 'Головная боль, сон, нервная система'],
    ['Диагностика', 'УЗИ, МРТ, лабораторные исследования'],
]

const markLoaded = (e) => e.currentTarget.parentNode.classList.add('has')
const dropImage = (e) => e.currentTarget.remove()

/** Fades sections in as they scroll into view (the template's .rv behaviour). */
const useReveal = (deps) => {
    const ref = useRef(null)
    useEffect(() => {
        const nodes = ref.current?.querySelectorAll('.rv:not(.in)') || []
        const io = new IntersectionObserver((entries) => entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in')
                io.unobserve(entry.target)
            }
        }), { threshold: .12 })
        nodes.forEach((el, i) => {
            el.style.transitionDelay = `${(i % 3) * 90}ms`
            io.observe(el)
        })
        return () => io.disconnect()
    }, deps) // eslint-disable-line react-hooks/exhaustive-deps
    return ref
}

export const LandingPage = () => {
    const navigate = useNavigate()
    const { isAuthenticated, role } = useSession()
    const [doctors, setDoctors] = useState(null)
    const [showAll, setShowAll] = useState(false)

    useEffect(() => {
        listDoctors({ sort_by: 'full_name' }).then(setDoctors).catch(() => setDoctors([]))
    }, [])

    const ref = useReveal([doctors, showAll])

    /** Patients go to the assistant; guests sign in first; staff go to their own interface. */
    const goAssistant = () => {
        if (!isAuthenticated) navigate('/auth', { state: { from: '/assistant' } })
        else if (role === 'patient') navigate('/assistant')
        else navigate(homePathFor(role))
    }

    const bookDoctor = (doctorId) => {
        const target = `/profile?book=${doctorId}#appointments`
        if (!isAuthenticated) navigate('/auth', { state: { from: target } })
        else if (role === 'patient') navigate(target)
        else navigate(homePathFor(role))
    }

    const visibleDoctors = showAll ? doctors : doctors?.slice(0, 3)

    return (
        <div className="p-landing" ref={ref}>
            <SiteHeader links={LANDING_LINKS} />

            <main>
                <div className="hero">
                    <div className="hbg" aria-hidden="true">
                        <svg viewBox="0 0 900 700" preserveAspectRatio="xMidYMid slice">
                            <g className="orb">
                                <circle cx="560" cy="350" r="110" fill="none" stroke="#0F5B68" strokeOpacity="0.28" />
                                <circle cx="560" cy="350" r="190" fill="none" stroke="#0F5B68" strokeOpacity="0.22" />
                                <circle cx="560" cy="350" r="280" fill="none" stroke="#0F5B68" strokeOpacity="0.17" />
                                <circle cx="560" cy="350" r="380" fill="none" stroke="#0F5B68" strokeOpacity="0.12" />
                                <circle cx="560" cy="350" r="490" fill="none" stroke="#0F5B68" strokeOpacity="0.08" />
                                <circle cx="670" cy="350" r="5" fill="#0F5B68" />
                                <circle cx="370" cy="350" r="4" fill="#8FD9C4" />
                                <circle cx="560" cy="70" r="5" fill="#0F5B68" fillOpacity=".7" />
                                <circle cx="905" cy="350" r="4" fill="#8FD9C4" />
                            </g>
                            <path className="hs" transform="translate(560 350) scale(5) translate(-12 -12)" d="M12 0c.8 7.2 4.8 11.2 12 12-7.2.8-11.2 4.8-12 12-.8-7.2-4.8-11.2-12-12C7.2 11.2 11.2 7.2 12 0z" fill="#0F5B68" />
                        </svg>
                    </div>
                    <div className="wrap hw">
                        <div className="eyebrow">SIRIUS · Университетская клиника</div>
                        <div className="hcont">
                            <h1 className="rv">Здоровье <i style={{ whiteSpace: 'nowrap' }}>без лишних</i> звонков и ожидания</h1>
                            <p className="hp rv">Опишите, что вас беспокоит, — ИИ-ассистент соберёт жалобы и подготовит обращение, а врач изучит его и примет решение.</p>
                            <div className="hero-actions rv">
                                <button className="btn" onClick={goAssistant}>Обратиться через ИИ-ассистента <ArrowRightIcon /></button>
                                <a className="alink" href="#ai">Как это работает <ArrowUpRightIcon /></a>
                            </div>
                        </div>
                        <div className="float f2"><div className="dot">✓</div><div><b>Личный ассистент 24/7</b><small>Всегда на связи</small></div></div>
                        <div className="float f3"><div><b style={{ font: '400 34px/1 var(--serif)' }}>4.9 ★</b><small>оценка пациентов</small></div></div>
                        <div className="marq"><span>Врачи с учёными степенями</span><span>Современное оборудование</span><span>Обращение без звонков</span><span>Ежедневно 8:00–21:00</span></div>
                    </div>
                </div>

                <section className="brand">
                    <div className="wrap">
                        <div className="bigname rv" aria-label="SIRIUS">SIRIUS
                            <svg className="tw" width="64" height="64" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 0c.8 7.2 4.8 11.2 12 12-7.2.8-11.2 4.8-12 12-.8-7.2-4.8-11.2-12-12C7.2 11.2 11.2 7.2 12 0z" fill="#0F5B68" /></svg>
                        </div>
                        <svg className="ecg" viewBox="0 0 1000 60" preserveAspectRatio="none" aria-hidden="true"><path d="M0 30h330l20-8 18 8h40l14-26 20 52 18-26h40l16-8 16 8h470" fill="none" stroke="#0F5B68" strokeWidth="1.5" strokeLinecap="round" /></svg>
                        <div className="bn-row rv">
                            <p className="lead">Сириус — самая яркая звезда ночного неба. Веками по ней находили дорогу. Мы хотим быть такой же точкой опоры для пациента: <i>видимой, надёжной и всегда рядом.</i></p>
                            <div className="heart">
                                <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 21s-8-5.2-8-11a4.6 4.6 0 0 1 8-3 4.6 4.6 0 0 1 8 3c0 5.8-8 11-8 11z" /></svg>
                                <span>Медицина с сердцем.<br />Технологии — чтобы у врача было больше времени для вас.</span>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="s" id="services">
                    <div className="wrap split">
                        <div className="sticky rv">
                            <div className="eyebrow">Услуги</div>
                            <h2>Направления <i>клиники</i></h2>
                            <p>Полный цикл помощи — от первичного обращения до диагностики и наблюдения. Не знаете, к кому идти? Начните с ИИ-ассистента.</p>
                            <button className="alink" onClick={goAssistant}>Описать симптомы →</button>
                        </div>
                        <ul className="dep rv">
                            {DEPARTMENTS.map(([title, text], idx) => (
                                <li key={title}>
                                    <button onClick={goAssistant}>
                                        <em>0{idx + 1}</em>
                                        <div><h3>{title}</h3><small>{text}</small></div>
                                        <span className="arr"><ArrowRightIcon /></span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                </section>

                <section className="s bg2" id="doctors">
                    <div className="wrap">
                        <div className="shead rv">
                            <div><div className="eyebrow">Специалисты</div><h2>Наши <i>врачи</i></h2></div>
                            {doctors?.length > 3 && (
                                <button className="alink" onClick={() => setShowAll(!showAll)}>{showAll ? 'Свернуть ↑' : `См. всех (${doctors.length}) →`}</button>
                            )}
                        </div>
                        {doctors === null ? null : doctors.length === 0 ? (
                            <p className="docs-empty">Список врачей скоро появится.</p>
                        ) : (
                            <div className="docs">
                                {visibleDoctors.map((doctor) => (
                                    <article className="doc rv" key={doctor.id}>
                                        <div className="ph" role="img" aria-label={`Врач ${doctor.full_name}`}>
                                            <span className="mono">{initials(doctor.full_name)}</span>
                                            {doctor.photo_url && (
                                                <img src={mediaUrl(doctor.photo_url)} alt={doctor.full_name} loading="lazy"
                                                    style={{ objectPosition: 'center 20%' }} onLoad={markLoaded} onError={dropImage} />
                                            )}
                                        </div>
                                        <h3>{doctor.full_name}</h3>
                                        <div className="pos">{doctor.specialization}</div>
                                        <div className="meta">
                                            <div>{doctor.qualification}<span>{doctor.available_timings}</span></div>
                                            <button className="btn sm" onClick={() => bookDoctor(doctor.id)}>Записаться</button>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        )}
                    </div>
                </section>

                <section className="s" id="about">
                    <div className="wrap about">
                        <div className="ph rv" role="img" aria-label="Изображение клиники">
                            <img src="/images/clinic-about.jpg" alt="Врач в клинике" loading="lazy" style={{ objectPosition: 'center 25%' }} onLoad={markLoaded} onError={dropImage} />
                        </div>
                        <div className="rv">
                            <div className="eyebrow">О нас</div>
                            <h2>Медицина, в которой <i>вас слышат</i></h2>
                            <p className="lead">Частная клиника с современным оборудованием, врачами с учёными степенями и цифровым сервисом, где ИИ-ассистент заранее собирает жалобы, а врач приходит к решению подготовленным.</p>
                            <div className="pr">
                                <div><b>Персональный подход</b>Один маршрут пациента — от запроса до наблюдения.</div>
                                <div><b>Доказательная медицина</b>Решения врача опираются на данные и протоколы.</div>
                                <div><b>Технологии</b>Цифровые обращения и уведомления без звонков.</div>
                                <div><b>Забота</b>Спокойная среда и время на каждого пациента.</div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="s" id="ai" style={{ paddingTop: 0 }}>
                    <div className="wrap">
                        <div className="ai rv">
                            <div>
                                <div className="eyebrow">ИИ-ассистент</div>
                                <h2>Подготовит обращение <i>к врачу</i> за вас</h2>
                                <ol className="steps">
                                    <li><div><b>Опишите симптомы</b>Своими словами, текстом или голосом. Ассистент задаст уточняющие вопросы.</div></li>
                                    <li><div><b>Подтвердите сводку</b>Ассистент структурирует жалобы и отправит их профильному врачу только с вашего согласия.</div></li>
                                    <li><div><b>Получите решение врача</b>Врач изучит обращение и примет решение — уведомление придёт в кабинет и на почту.</div></li>
                                </ol>
                                <button className="btn" onClick={goAssistant}>Начать диалог <ArrowRightIcon /></button>
                            </div>
                            <div className="ph aiph" role="img" aria-label="Видео ИИ-ассистента">
                                <video autoPlay muted loop playsInline preload="metadata" aria-label="Видео ИИ-ассистента">
                                    <source src="/ai-promo.mp4" type="video/mp4" />
                                </video>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="s" style={{ paddingTop: 0 }}>
                    <div className="wrap stats">
                        <div className="rv"><b>15<sup>+</sup></b><span>лет опыта врачей клиники</span></div>
                        <div className="rv"><b>40</b><span>специалистов в штате</span></div>
                        <div className="rv"><b>12 000</b><span>пациентов ежегодно</span></div>
                    </div>
                </section>

                <section className="s bg2" id="contacts">
                    <div className="wrap contacts">
                        <div className="rv">
                            <div className="eyebrow">Контакты</div>
                            <h2>Ждём вас <i>в клинике</i></h2>
                            <div className="addr">
                                <div><b style={{ fontWeight: 500 }}>SIRIUS Hospital</b><span>119048, Москва, ул. Доватора, 15</span></div>
                                <div>Режим работы<span>Ежедневно 8:00–21:00</span></div>
                                <div>Телефон<span>+7 915 163-07-01</span></div>
                            </div>
                        </div>
                        <div className="map rv" role="img" aria-label="Стилизованная карта района клиники по адресу: 119048, Москва, ул. Доватора, 15">
                            <div className="pin"></div>
                            <div className="float"><div className="dot">⌖</div><div><b>SIRIUS Hospital</b><small>119048, Москва, ул. Доватора, 15</small></div></div>
                        </div>
                    </div>
                </section>
            </main>

            <footer>
                <div className="wrap">
                    <div className="cols">
                        <div>
                            <Logo />
                            <p style={{ fontSize: 14, color: 'var(--ink2)', marginTop: 16 }}>+7 915 163-07-01<br />info@example.clinic</p>
                        </div>
                        <div>
                            <h5>Пациентам</h5>
                            <ul>
                                <li><a href="#doctors">Врачи</a></li>
                                <li><a href="#services">Направления</a></li>
                                <li><button className="alink" style={{ border: 0, padding: 0, color: 'inherit', font: 'inherit' }} onClick={goAssistant}>ИИ-ассистент</button></li>
                                <li><Link to="/cabinet">Личный кабинет</Link></li>
                            </ul>
                        </div>
                        <div>
                            <h5>Документы</h5>
                            <ul>
                                <li><Link to="/legal/privacy">Политика конфиденциальности</Link></li>
                                <li><Link to="/legal/consent">Согласие на обработку персональных данных</Link></li>
                                <li><Link to="/legal/terms">Пользовательское соглашение</Link></li>
                                <li>Лицензии и сертификаты</li>
                            </ul>
                        </div>
                    </div>
                    <div className="word" aria-hidden="true">SIRIUS</div>
                    <div className="legal">
                        ИИ-ассистент собирает информацию для врача и не ставит диагнозов. Имеются противопоказания, необходима консультация специалиста. Информация на сайте не является публичной офертой и не заменяет очную консультацию врача. Лицензия на медицинскую деятельность № 00-00-000000 (пример). © 2026 SIRIUS.
                    </div>
                </div>
            </footer>
        </div>
    )
}
