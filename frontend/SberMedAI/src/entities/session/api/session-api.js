import { api } from "@/shared/api/axios-client.js";

export const loginRequest = (email, password) =>
    api.post('/auth/login', { email, password }).then((r) => r.data)

export const registerRequest = (email, password, full_name) =>
    api.post('/auth/register', { email, password, full_name, role: 'patient' }).then((r) => r.data)

export const fetchMe = () => api.get('/auth/me').then((r) => r.data)

/** Role-specific profile: the patient's own card or the doctor's record; admins have none. */
export const fetchRoleProfile = async (user) => {
    if (user.role === 'patient') {
        try {
            const patients = await api.get('/patients').then((r) => r.data)
            return patients[0] || null
        } catch (error) {
            // A newly registered patient has no profile yet: the backend answers 404 and onboarding creates it.
            if (error.response?.status === 404) return null
            throw error
        }
    }
    if (user.role === 'doctor') {
        const doctors = await api.get('/doctors', { params: { limit: 1000 } }).then((r) => r.data)
        return doctors.find((doctor) => doctor.user_id === user.id) || null
    }
    return null
}
