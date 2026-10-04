import { api } from '@/shared/api/axios-client.js'

export const getAnswer = async (message, chat_id, date) => {
    const res = await api.post(`/${chat_id}/answer`, {message, date})
    return res.data
}