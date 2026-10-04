import { api } from '@/shared/api/axios-client.js'

export const listNotifications = () => api.get('/notifications').then((r) => r.data)
export const markNotificationRead = (id) => api.post(`/notifications/${id}/read`).then((r) => r.data)
export const markAllNotificationsRead = () => api.post('/notifications/read-all')
