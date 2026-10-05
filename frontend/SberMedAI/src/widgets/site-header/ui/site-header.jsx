import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useSession, homePathFor } from '@/entities/session'
import { listNotifications, markAllNotificationsRead, markNotificationRead } from '@/entities/notification/api/notification-api.js'
import { Logo } from '@/shared/ui/common.jsx'
import { BellIcon, UserIcon, LogoutIcon } from '@/shared/ui/icons.jsx'
import { ROLE } from '@/shared/lib/labels.js'
import { formatDateTime } from '@/shared/lib/format.js'

const NAV = {
    patient: [['/', 'Главная'], ['/assistant', 'ИИ-ассистент'], ['/profile', 'Личный кабинет']],
    doctor: [['/', 'Главная'], ['/doctor', 'Обращения пациентов'], ['/doctor/assistant', 'ИИ-ассистент']],
    admin: [['/', 'Главная'], ['/admin', 'Администрирование'], ['/admin/assistant', 'ИИ-ассистент']],
}

const caseLink = (role, caseId) => {
    if (!caseId) return null
    if (role === 'doctor') return `/doctor/cases/${caseId}`
    if (role === 'patient') return `/profile?case=${caseId}#cases`
    return null
}

const NotificationsBell = () => {
    const { role } = useSession()
    const navigate = useNavigate()
    const [items, setItems] = useState([])
    const [open, setOpen] = useState(false)
    const ref = useRef(null)

    // Plain DB read (no AI): refreshed when the header mounts and whenever the panel is opened.
    const load = () => listNotifications().then(setItems).catch(() => {})
    useEffect(() => { load() }, [])

    useEffect(() => {
        if (!open) return
        const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
        const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
        document.addEventListener('mousedown', onClick)
        document.addEventListener('keydown', onKey)
        return () => {
            document.removeEventListener('mousedown', onClick)
            document.removeEventListener('keydown', onKey)
        }
    }, [open])

    const unread = items.filter((n) => !n.is_read).length

    const openItem = async (item) => {
        if (!item.is_read) {
            setItems((list) => list.map((n) => (n.id === item.id ? { ...n, is_read: true } : n)))
            markNotificationRead(item.id).catch(() => {})
        }
        const to = caseLink(role, item.case_id)
        setOpen(false)
        if (to) navigate(to)
    }

    const readAll = async () => {
        setItems((list) => list.map((n) => ({ ...n, is_read: true })))
        await markAllNotificationsRead().catch(() => {})
    }

    return (
        <div ref={ref} style={{ position: 'relative' }}>
            <button
                className={`ibtn${open ? ' on' : ''}`}
                aria-label={`Уведомления${unread ? `, непрочитанных: ${unread}` : ''}`}
                aria-expanded={open}
                onClick={() => { if (!open) load(); setOpen(!open) }}
            >
                <BellIcon />
                {unread > 0 && <span className="badge">{unread > 9 ? '9+' : unread}</span>}
            </button>
            {open && (
                <div className="panel">
                    <div className="panel-h">
                        <div>Уведомления<small>{unread ? `Непрочитанных: ${unread}` : 'Все прочитаны'}</small></div>
                        {unread > 0 && <button className="alink" onClick={readAll}>Прочитать все</button>}
                    </div>
                    <div className="panel-b">
                        {items.length === 0
                            ? <div className="panel-empty">Здесь появятся решения врачей и новости по вашим обращениям.</div>
                            : items.map((item) => (
                                <button key={item.id} className={`ntf${item.is_read ? '' : ' unread'}`} onClick={() => openItem(item)}>
                                    <b>{item.title}</b>
                                    <p>{item.message}</p>
                                    <time>{formatDateTime(item.created_at)}</time>
                                </button>
                            ))}
                    </div>
                </div>
            )}
        </div>
    )
}

/**
 * Shared header. `links` overrides the menu (the landing page passes its section anchors).
 */
export const SiteHeader = ({ links, solid = false }) => {
    const { user, role, isAuthenticated, logout } = useSession()
    const navigate = useNavigate()
    const [stuck, setStuck] = useState(false)

    useEffect(() => {
        const onScroll = () => setStuck(window.scrollY > 8)
        onScroll()
        window.addEventListener('scroll', onScroll, { passive: true })
        return () => window.removeEventListener('scroll', onScroll)
    }, [])

    const menu = links || NAV[role] || []

    return (
        <header className={`header${stuck ? ' stuck' : ''}${solid ? ' solid' : ''}`}>
            <div className="wrap hnav">
                <Logo />
                <ul className="menu">
                    {menu.map(([to, label]) => (
                        <li key={to}>
                            {to.startsWith('#')
                                ? <a href={to}>{label}</a>
                                : <NavLink to={to} end className={({ isActive }) => (isActive ? 'cur' : undefined)}>{label}</NavLink>}
                        </li>
                    ))}
                </ul>
                <div className="hright">
                    {isAuthenticated ? (
                        <>
                            <span className="role-tag" title={user.full_name}>{ROLE[role]}</span>
                            <NotificationsBell />
                            <Link className="ibtn" to={homePathFor(role)} aria-label="Личный кабинет" title={user.full_name}><UserIcon /></Link>
                            <button className="ibtn" aria-label="Выйти" title="Выйти" onClick={() => { logout(); navigate('/') }}><LogoutIcon /></button>
                        </>
                    ) : (
                        <Link className="btn sm" to="/auth">Войти</Link>
                    )}
                </div>
            </div>
        </header>
    )
}
