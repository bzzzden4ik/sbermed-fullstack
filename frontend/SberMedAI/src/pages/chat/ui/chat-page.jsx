import { useState, useEffect } from "react"
import { useSession } from '@/entities/session'
import { useParams } from "react-router-dom"

import { getChat } from "../model/chat-by-id.js"
import { sendMessage } from "../model/send-message.js"

import { MessageContainer } from "@/entities/message"
import { AudioRecorder } from "@/widgets/audio-recorder"

export function ChatPage () {
    const [isNewChat, setIsNewChat] = useState(true)
    const [messages, setMessages] = useState([])
    const { chat_id } = useParams(); 
    const [currentInput, setCurrentInput] = useState('')

    const { userId } = useSession()
    const [chatId, setChatId] = useState(chat_id)

    useEffect(() => {
        async function startSearchingChat() {
            const res = await getChat("123")
            if (res?.chat) {
                setMessages(res.chat)
                setIsNewChat(false)
            }
        }
        if (chat_id) {
            startSearchingChat()
        }
    }, [])

    const handle_question = async () => {
        try {
            setIsNewChat(false)
            await sendMessage(currentInput, chat_id, userId, setMessages)
            setCurrentInput("")
        } catch {
            alert("Проблемы с сообщением")   
        }
    }

    return (
        <main>
            <div className="container">
                <div className="chat__container">
                    <div className="chat__area">
                        {isNewChat ? 
                            <h1>Привет! Что Вы хотели уточнить?</h1>
                        : messages?.map((el, idx) => 
                            <MessageContainer key={idx} message={el.text} time={el.timestamp} position={el.sender_id == 0}/>
                        )}
                    </div>
                    <div className="input__area">
                        <input type="text" placeholder="Введите Ваш Запрос" value={currentInput} onChange={(e) => setCurrentInput(e.target.value)}/>
                        {currentInput ?
                            <button onClick={handle_question}>+</button>
                            : <AudioRecorder />
                        }
                    </div>
                </div>
            </div>
        </main>
    )
}
