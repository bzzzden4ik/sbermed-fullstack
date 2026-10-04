import { api } from "@/shared/api/axios-client.js"

export const getChatById = async (chat_id) => {
    const res = await api.get(`/chat/${chat_id}`)
    return res.data
}