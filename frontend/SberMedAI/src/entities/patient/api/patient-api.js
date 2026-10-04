import { api } from '@/shared/api/axios-client.js'

export const createPatientProfile = (payload) => api.post('/patients', payload).then((r) => r.data)
export const updatePatientProfile = (id, payload) => api.put(`/patients/${id}`, payload).then((r) => r.data)
export const listPatients = (params) => api.get('/patients', { params }).then((r) => r.data)
export const deletePatient = (id) => api.delete(`/patients/${id}`)
