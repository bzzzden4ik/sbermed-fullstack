import { useCallback, useMemo, useRef, useState } from 'react'
import { ToastContext } from './toast-context.js'

export const ToastProvider = ({ children }) => {
    const [toast, setToast] = useState({ text: '', bad: false, on: false })
    const timer = useRef(null)

    const show = useCallback((text, { bad = false } = {}) => {
        clearTimeout(timer.current)
        setToast({ text, bad, on: true })
        timer.current = setTimeout(() => setToast((t) => ({ ...t, on: false })), 2800)
    }, [])

    const value = useMemo(() => ({ show, error: (text) => show(text, { bad: true }) }), [show])

    return (
        <ToastContext.Provider value={value}>
            {children}
            <div className={`toast${toast.on ? ' on' : ''}${toast.bad ? ' bad' : ''}`} role="status" aria-live="polite">{toast.text}</div>
        </ToastContext.Provider>
    )
}
