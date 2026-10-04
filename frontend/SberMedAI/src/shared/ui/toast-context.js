import { createContext, useContext } from 'react'

export const ToastContext = createContext(null)

export const useToast = () => {
    const context = useContext(ToastContext)
    if (!context) {
        throw new Error('useToast должен использоваться внутри ToastProvider')
    }
    return context
}
