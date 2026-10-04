import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
    listConversations, getConversation, createConversation, sendMessage, deleteConversation, transcribeAudio,
} from '@/entities/conversation/api/conversation-api.js'
import { SiteHeader } from '@/widgets/site-header'
import { useToast } from '@/shared/ui/toast-context.js'
import { StatusChip } from '@/shared/ui/common.jsx'
import { SparkIcon, PlusIcon, SearchIcon, CloseIcon, MicIcon, SendIcon, TrashIcon, MenuIcon } from '@/shared/ui/icons.jsx'
import { getLatestCase } from '@/entities/case'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { CASE_DECISION, CASE_STATUS } from '@/shared/lib/labels.js'
import { dayGroup, formatDate, formatTime } from '@/shared/lib/format.js'
import { useVoiceRecorder } from '../lib/use-voice-recorder.js'
import './assistant.css'

const SUGGESTIONS = ['Болит голова', 'Повышенное давление', 'Ухудшилось зрение', 'Боль в спине']
const CHECK_IN = ['Мне стало лучше', 'Лучше не стало', 'Стало хуже', 'Появились новые симптомы']

/** Last sent case and the doctor's answer, read from the database (no AI) for the follow-up start screen. */
const LastCaseCard = ({ item }) => {
    const resolved = item.status === 'RESOLVED'
    return (
        <div className="lastcase">
            <div className="lc-h">
                <span>Обращение №{item.id} · {formatDate(item.submitted_at || item.created_at)}</span>
                <StatusChip map={CASE_STATUS} value={item.status} />
            </div>
            <b>{item.complaint}</b>
            {resolved ? (
                <>
                    <p className="lc-dec">Ответ врача{item.doctor ? ` (${item.doctor.full_name})` : ''}: {CASE_DECISION[item.decision]?.label || item.decision}</p>
                    {item.doctor_comment && <blockquote>{item.doctor_comment}</blockquote>}
                </>
            ) : (
                <p className="lc-dec">Обращение у врача{item.doctor ? ` ${item.doctor.full_name}` : ''} — решение придёт уведомлением и на почту.</p>
            )}
        </div>
    )
}
const COLLECTING = ['OPEN', 'AI_COLLECTING']
const fmtSeconds = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

/** Renders the assistant's plain-text reply, keeping line breaks and **bold** fragments. */
const RichText = ({ text }) => text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
        ? <b key={i}>{part.slice(2, -2)}</b>
        : <Fragment key={i}>{part}</Fragment>
)

const Bubble = ({ message }) => (
    <div className={`row ${message.role === 'user' ? 'u' : 'b'}`}>
        {message.role !== 'user' && <div className="av"><SparkIcon /></div>}
        <div className="msg">
            <RichText text={message.content} />
            {message.created_at && <time>{formatTime(message.created_at)}</time>}
        </div>
    </div>
)

export function AssistantPage() {
    const { conversationId } = useParams()
    const currentId = conversationId ? Number(conversationId) : null
    const navigate = useNavigate()
    const toast = useToast()

    const [conversations, setConversations] = useState([])
    const [loaded, setLoaded] = useState(false)
    const [query, setQuery] = useState('')
    const [input, setInput] = useState('')
    const [pending, setPending] = useState(false)
    const [optimistic, setOptimistic] = useState(null)
    const [transcribing, setTranscribing] = useState(false)
    const [sideOpen, setSideOpen] = useState(false)

    // Synchronous guard: blocks a second AI request from double clicks / Enter repeats before React re-renders.
    const inFlight = useRef(false)
    const logRef = useRef(null)
    const inputRef = useRef(null)

    // Stored conversations only — loading history never calls the AI.
    useEffect(() => {
        listConversations()
            .then(setConversations)
            .catch((err) => toast.error(getErrorMessage(err)))
            .finally(() => setLoaded(true))
    }, [toast])

    // Latest sent case for the follow-up check-in; refreshed whenever the start screen is shown.
    const [latestCase, setLatestCase] = useState(undefined)
    useEffect(() => {
        if (currentId) return
        getLatestCase().then(setLatestCase).catch(() => setLatestCase(null))
    }, [currentId])

    // Deep link to a conversation that is not in the list (e.g. just after the list loaded empty).
    useEffect(() => {
        if (!loaded || !currentId || conversations.some((c) => c.id === currentId)) return
        getConversation(currentId)
            .then((c) => setConversations((list) => [c, ...list]))
            .catch(() => navigate('/assistant', { replace: true }))
    }, [loaded, currentId, conversations, navigate])

    const current = conversations.find((c) => c.id === currentId) || null
    const messages = useMemo(() => {
        const list = current?.messages || []
        return optimistic ? [...list, optimistic] : list
    }, [current, optimistic])
    const caseSent = current && current.case_status && !COLLECTING.includes(current.case_status)

    useEffect(() => {
        const log = logRef.current
        if (log) log.scrollTop = log.scrollHeight
    }, [messages.length, pending])

    // Switching conversations closes the mobile drawer and clears the draft (state reset during render).
    const [shownId, setShownId] = useState(currentId)
    if (shownId !== currentId) {
        setShownId(currentId)
        setSideOpen(false)
        setInput('')
    }

    const fitInput = () => {
        const el = inputRef.current
        if (!el) return
        el.style.height = 'auto'
        el.style.height = `${Math.min(el.scrollHeight, 140)}px`
    }
    useEffect(fitInput, [input])

    const send = async (raw) => {
        const text = (raw ?? input).trim()
        if (!text || inFlight.current || caseSent) return
        inFlight.current = true
        setPending(true)
        setInput('')
        setOptimistic({ id: 'pending', role: 'user', content: text })
        try {
            if (!current) {
                const conversation = await createConversation(text)
                setConversations((list) => [conversation, ...list])
                navigate(`/assistant/${conversation.id}`)
            } else {
                const result = await sendMessage(current.id, text)
                setConversations((list) => list.map((c) => (c.id === result.conversation_id
                    ? {
                        ...c,
                        case_id: result.case_id,
                        case_status: result.case_status,
                        messages: [...c.messages, result.user_message, result.assistant_message],
                    }
                    : c)))
                if (!COLLECTING.includes(result.case_status)) {
                    toast.show(`Обращение №${result.case_id} отправлено врачу`)
                }
            }
        } catch (err) {
            setInput(text) // nothing was saved on the server, so the patient can simply resend
            toast.error(err.response?.status === 502 ? 'Ассистент временно недоступен. Попробуйте ещё раз.' : getErrorMessage(err))
            if (err.response?.status === 409 && current) {
                getConversation(current.id).then((c) => setConversations((list) => list.map((x) => (x.id === c.id ? c : x)))).catch(() => {})
            }
        } finally {
            setOptimistic(null)
            setPending(false)
            inFlight.current = false
            inputRef.current?.focus()
        }
    }

    const remove = async (conversation) => {
        const sent = conversation.case_status && !COLLECTING.includes(conversation.case_status)
        const ok = window.confirm(sent
            ? 'Удалить переписку? Отправленное обращение останется у врача и в личном кабинете.'
            : 'Удалить диалог? Несохранённое обращение будет удалено.')
        if (!ok) return
        try {
            await deleteConversation(conversation.id)
            setConversations((list) => list.filter((c) => c.id !== conversation.id))
            if (conversation.id === currentId) navigate('/assistant')
        } catch (err) {
            toast.error(getErrorMessage(err))
        }
    }

    const onRecorded = useCallback(async (blob) => {
        setTranscribing(true)
        try {
            const text = await transcribeAudio(blob)
            if (!text) {
                toast.error('Не удалось распознать речь')
                return
            }
            setInput((prev) => (prev ? `${prev} ${text}` : text))
            toast.show('Проверьте распознанный текст и отправьте')
            inputRef.current?.focus()
        } catch (err) {
            toast.error(getErrorMessage(err, 'Не удалось распознать запись'))
        } finally {
            setTranscribing(false)
        }
    }, [toast])
    const { recording, elapsed, canvasRef, start: startRecording, stop: stopRecording } = useVoiceRecorder({ onRecorded, onError: toast.error })

    const filtered = conversations.filter((c) => !query.trim() || (c.title || '').toLowerCase().includes(query.trim().toLowerCase()))
    const groups = filtered.map((c) => dayGroup(c.created_at))

    return (
        <div className="p-assistant">
            <SiteHeader solid />
            <div className="app">
                <aside className={`side${sideOpen ? ' open' : ''}`} aria-label="История диалогов">
                    <div className="side-h">
                        <h2>Обращения</h2>
                        <button className="btn" onClick={() => navigate('/assistant')} disabled={pending}><PlusIcon />Новое обращение</button>
                    </div>
                    <label className="find">
                        <SearchIcon />
                        <input placeholder="Поиск по диалогам" aria-label="Поиск по диалогам" value={query} onChange={(e) => setQuery(e.target.value)} />
                    </label>
                    <div className="hist">
                        {loaded && filtered.length === 0 && (
                            <div className="empty-h">{query ? 'Ничего не найдено' : 'Здесь появятся ваши диалоги с ассистентом'}</div>
                        )}
                        {filtered.map((c, idx) => {
                            const group = groups[idx]
                            const showGroup = idx === 0 || groups[idx - 1] !== group
                            const last = c.messages[c.messages.length - 1]
                            return (
                                <Fragment key={c.id}>
                                    {showGroup && <div className="grp">{group}</div>}
                                    <div
                                        role="button" tabIndex={0}
                                        className={`cv${c.id === currentId ? ' on' : ''}`}
                                        onClick={() => navigate(`/assistant/${c.id}`)}
                                        onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/assistant/${c.id}`) }}
                                    >
                                        <div>
                                            <b>{c.title || 'Новый диалог'}</b>
                                            <small>{last?.content || 'Пустой диалог'}</small>
                                            {c.case_status && !COLLECTING.includes(c.case_status) && (
                                                <span className="sent">✓ {CASE_STATUS[c.case_status]?.label}</span>
                                            )}
                                        </div>
                                        <button className="x" aria-label="Удалить диалог" onClick={(e) => { e.stopPropagation(); remove(c) }}>
                                            <CloseIcon />
                                        </button>
                                    </div>
                                </Fragment>
                            )
                        })}
                    </div>
                </aside>
                <div className={`scrim${sideOpen ? ' on' : ''}`} onClick={() => setSideOpen(false)}></div>

                <section className="chat">
                    <div className="top">
                        <button className="ibtn burger" aria-label="История диалогов" onClick={() => setSideOpen(true)}><MenuIcon /></button>
                        <div className="av"><SparkIcon size={16} /></div>
                        <div><div>Ассистент SIRIUS</div><small>готовит обращение к врачу</small></div>
                        <span className="sp"></span>
                        {current?.case_id && <StatusChip map={CASE_STATUS} value={current.case_status} />}
                    </div>

                    <div className="log" ref={logRef} aria-live="polite">
                        {messages.length === 0 && !currentId ? (
                            latestCase ? (
                                <div className="welcome">
                                    <div className="orb"><SparkIcon size={34} /></div>
                                    <h2>Как вы <i>себя чувствуете?</i></h2>
                                    <p>Расскажите, как самочувствие после вашего последнего обращения. Если лучше не стало, я помогу оформить новое обращение к врачу.</p>
                                    <LastCaseCard item={latestCase} />
                                    <div className="chips">
                                        {CHECK_IN.map((s) => <button key={s} disabled={pending} onClick={() => send(s)}>{s}</button>)}
                                    </div>
                                    <p className="lc-new">Другая проблема? Просто опишите её ниже.</p>
                                </div>
                            ) : (
                                <div className="welcome">
                                    <div className="orb"><SparkIcon size={34} /></div>
                                    <h2>Расскажите, <i>что беспокоит</i></h2>
                                    <p>Напишите или надиктуйте своими словами. Я задам несколько уточняющих вопросов, составлю сводку и с вашего согласия передам её врачу.</p>
                                    <div className="chips">
                                        {SUGGESTIONS.map((s) => <button key={s} disabled={pending} onClick={() => send(s)}>{s}</button>)}
                                    </div>
                                </div>
                            )
                        ) : (
                            messages.map((m) => <Bubble key={m.id} message={m} />)
                        )}
                        {pending && (
                            <div className="row b">
                                <div className="av"><SparkIcon /></div>
                                <div className="msg typing" aria-label="Ассистент печатает"><i></i><i></i><i></i></div>
                            </div>
                        )}
                    </div>

                    {caseSent ? (
                        <div className="sent-banner">
                            <div>
                                <b>Обращение №{current.case_id} передано врачу</b>
                                <p>Врач изучит сводку и примет решение. Уведомление придёт в личный кабинет и на почту.</p>
                            </div>
                            <div className="acts">
                                <Link className="btn sm" to={`/profile?case=${current.case_id}#cases`}>Открыть обращение</Link>
                                <button className="btn sm ghost" onClick={() => navigate('/assistant')}>Новое обращение</button>
                            </div>
                        </div>
                    ) : (
                        <div className="comp">
                            <div className={`pill${recording ? ' rc' : ''}`}>
                                <textarea
                                    ref={inputRef}
                                    rows={1}
                                    placeholder={transcribing ? 'Распознаём запись…' : 'Опишите, что вас беспокоит…'}
                                    aria-label="Сообщение"
                                    value={input}
                                    disabled={transcribing}
                                    maxLength={4000}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                                            e.preventDefault()
                                            send()
                                        }
                                    }}
                                />
                                {input.trim() ? (
                                    <button className="act snd" aria-label="Отправить" disabled={pending} onClick={() => send()}><SendIcon /></button>
                                ) : (
                                    <button className="act mic" aria-label="Записать голосовое сообщение" disabled={pending || transcribing} onClick={startRecording}><MicIcon /></button>
                                )}
                                <div className="rec" aria-hidden={!recording}>
                                    <button className="act trash" aria-label="Отменить запись" onClick={() => { stopRecording(false); toast.show('Запись удалена') }}><TrashIcon /></button>
                                    <span className="rdot"></span>
                                    <span className="rtime">{fmtSeconds(elapsed)}</span>
                                    <canvas className="wave" ref={canvasRef}></canvas>
                                    <button className="act snd" aria-label="Распознать запись" onClick={() => stopRecording(true)}><SendIcon /></button>
                                </div>
                            </div>
                            <p className="hint">Enter — отправить, Shift+Enter — новая строка. Ассистент не ставит диагнозов и не заменяет консультацию врача.</p>
                        </div>
                    )}
                </section>
            </div>
        </div>
    )
}
