import { api } from '@/shared/api/axios-client.js'

export const getDashboardReport = () => api.get('/reports/dashboard').then((r) => r.data)
export const getDoctorsReport = () => api.get('/reports/doctors').then((r) => r.data)
