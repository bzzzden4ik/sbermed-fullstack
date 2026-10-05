import { api } from '@/shared/api/axios-client.js'

export const createPatientProfile = (payload) => api.post('/patients', payload).then((r) => r.data)
export const updatePatientProfile = (id, payload) => api.put(`/patients/${id}`, payload).then((r) => r.data)
export const listPatients = (params) => api.get('/patients', { params }).then((r) => r.data)
export const deletePatient = (id) => api.delete(`/patients/${id}`)

export const uploadPatientPhoto = (id, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/patients/${id}/photo`, formData).then((r) => r.data)
}
export const deletePatientPhoto = (id) => api.delete(`/patients/${id}/photo`).then((r) => r.data)
// The photo is private, so it is fetched with the auth header and shown from a blob URL.
export const fetchPatientPhoto = (id) => api.get(`/patients/${id}/photo`, { responseType: 'blob' }).then((r) => r.data)
