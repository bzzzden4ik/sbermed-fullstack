import { api } from '@/shared/api/axios-client.js'

export const listAppointments = (params) => api.get('/appointments', { params }).then((r) => r.data)
export const bookAppointment = (payload) => api.post('/appointments', payload).then((r) => r.data)
export const updateAppointment = (id, payload) => api.put(`/appointments/${id}`, payload).then((r) => r.data)
