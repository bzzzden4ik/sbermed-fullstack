import { api } from '@/shared/api/axios-client.js'

// Only createConversation and sendMessage trigger a paid AI request; everything else reads stored data.
export const listConversations = () => api.get('/conversations').then((r) => r.data)
export const getConversation = (id) => api.get(`/conversations/${id}`).then((r) => r.data)
export const createConversation = (message) => api.post('/conversations', { message }).then((r) => r.data.conversation)
export const sendMessage = (id, content) => api.post(`/conversations/${id}/messages`, { content }).then((r) => r.data)
export const deleteConversation = (id) => api.delete(`/conversations/${id}`)

export const transcribeAudio = (blob) => {
    const formData = new FormData()
    const extension = blob.type.includes('mp4') ? 'mp4' : blob.type.includes('ogg') ? 'ogg' : 'webm'
    formData.append('file', blob, `voice.${extension}`)
    return api.post('/convert_audio_to_text', formData).then((r) => String(r.data.text || '').trim())
}
