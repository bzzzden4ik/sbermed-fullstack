import axios from "axios";

const TOKEN_KEY = 'token'
export const AUTH_EXPIRED_EVENT = 'auth:expired'

export const tokenStorage = {
    get: () => {
        try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
    },
    set: (token) => {
        try { localStorage.setItem(TOKEN_KEY, token) } catch { /* storage unavailable */ }
    },
    clear: () => {
        try { localStorage.removeItem(TOKEN_KEY) } catch { /* storage unavailable */ }
    },
}

export const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
})

// Every request carries the JWT so FastAPI can resolve current_user and its role.
api.interceptors.request.use((config) => {
    const token = tokenStorage.get()
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// An expired or invalid token logs the user out everywhere.
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && tokenStorage.get()) {
            tokenStorage.clear()
            window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
        }
        return Promise.reject(error)
    }
)

/** Human-readable message from a FastAPI error response. */
export const getErrorMessage = (error, fallback = 'Что-то пошло не так. Попробуйте ещё раз.') => {
    const detail = error?.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length) {
        return detail.map((item) => item.msg?.replace(/^Value error, /, '')).filter(Boolean).join('; ')
    }
    if (error?.code === 'ERR_NETWORK') return 'Сервер недоступен. Проверьте, что backend запущен.'
    return fallback
}
