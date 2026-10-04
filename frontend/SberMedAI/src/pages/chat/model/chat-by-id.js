import { getChatById } from "../api/chat.js"


export const getChat = async (chat_id) => {
    const res = await getChatById(chat_id)
    return res
}