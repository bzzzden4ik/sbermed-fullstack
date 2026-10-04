import { api } from '@/shared/api/axios-client.js'

export const listCases = (params) => api.get('/cases', { params }).then((r) => r.data)
export const getCase = (id) => api.get(`/cases/${id}`).then((r) => r.data)
export const startCaseReview = (id) => api.post(`/cases/${id}/review`).then((r) => r.data)
export const decideCase = (id, payload) => api.post(`/cases/${id}/decision`, payload).then((r) => r.data)
export const getLatestCase = () => api.get('/cases/latest').then((r) => r.data)
