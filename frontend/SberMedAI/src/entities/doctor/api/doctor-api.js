import { api } from '@/shared/api/axios-client.js'

export const listDoctors = (params) => api.get('/doctors', { params }).then((r) => r.data)
export const createDoctor = (payload) => api.post('/doctors', payload).then((r) => r.data)
export const updateDoctor = (id, payload) => api.put(`/doctors/${id}`, payload).then((r) => r.data)
export const deleteDoctor = (id) => api.delete(`/doctors/${id}`)
