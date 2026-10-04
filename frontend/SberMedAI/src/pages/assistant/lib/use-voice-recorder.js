import { useCallback, useEffect, useRef, useState } from 'react'

const MAX_SECONDS = 300

/**
 * Microphone recording with the template's live waveform. `onRecorded(blob)` fires only when the user sends;
 * cancelled recordings are discarded locally and never uploaded.
 */
export const useVoiceRecorder = ({ onRecorded, onError }) => {
    const [recording, setRecording] = useState(false)
    const [elapsed, setElapsed] = useState(0)
    const canvasRef = useRef(null)
    const stateRef = useRef(null)
    const callbacks = useRef({ onRecorded, onError })
    const stopRef = useRef(null)

    useEffect(() => {
        callbacks.current = { onRecorded, onError }
    }, [onRecorded, onError])

    const draw = useCallback(function frame() {
        const r = stateRef.current
        if (!r) return
        const buf = new Uint8Array(r.analyser.fftSize)
        r.analyser.getByteTimeDomainData(buf)
        let sum = 0
        for (const v of buf) { const x = (v - 128) / 128; sum += x * x }
        r.levels.push(Math.min(1, Math.sqrt(sum / buf.length) * 3.2))
        if (r.levels.length > 200) r.levels.shift()

        const seconds = (performance.now() - r.t0) / 1000
        setElapsed(seconds)

        const cv = canvasRef.current
        if (cv) {
            const d = window.devicePixelRatio || 1
            if (cv.width !== cv.clientWidth * d) { cv.width = cv.clientWidth * d; cv.height = cv.clientHeight * d }
            const cx = cv.getContext('2d')
            const w = cv.width, h = cv.height, bw = 3 * d, gap = 3 * d, n = Math.floor(w / (bw + gap))
            cx.clearRect(0, 0, w, h)
            const g = cx.createLinearGradient(0, 0, w, 0)
            g.addColorStop(0, 'rgba(143,217,196,.25)'); g.addColorStop(.7, '#2A8796'); g.addColorStop(1, '#8FD9C4')
            cx.fillStyle = g
            for (let i = 0; i < n; i++) {
                const li = r.levels.length - n + i
                const v = li >= 0 ? r.levels[li] : 0
                const bh = Math.max(4 * d, v * h * .92)
                cx.beginPath()
                if (cx.roundRect) cx.roundRect(i * (bw + gap), (h - bh) / 2, bw, bh, bw / 2)
                else cx.rect(i * (bw + gap), (h - bh) / 2, bw, bh)
                cx.fill()
            }
        }
        if (seconds >= MAX_SECONDS) { stopRef.current(true); return }
        r.raf = requestAnimationFrame(frame)
    }, [])

    const stop = useCallback((send) => {
        const r = stateRef.current
        if (!r) return
        stateRef.current = null
        cancelAnimationFrame(r.raf)
        setRecording(false)
        const duration = (performance.now() - r.t0) / 1000
        r.recorder.onstop = () => {
            r.stream.getTracks().forEach((t) => t.stop())
            r.audioContext.close().catch(() => {})
            if (!send) return
            if (duration < .8) { callbacks.current.onError?.('Запись слишком короткая'); return }
            callbacks.current.onRecorded(new Blob(r.chunks, { type: r.recorder.mimeType || 'audio/webm' }))
        }
        try { r.recorder.stop() } catch { r.recorder.onstop() }
    }, [])

    useEffect(() => {
        stopRef.current = stop
    }, [stop])

    const start = useCallback(async () => {
        if (stateRef.current) return
        if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
            callbacks.current.onError?.('Запись голоса недоступна в этом браузере')
            return
        }
        let stream
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        } catch {
            callbacks.current.onError?.('Нет доступа к микрофону. Разрешите его в настройках браузера.')
            return
        }
        const AC = window.AudioContext || window.webkitAudioContext
        const audioContext = new AC()
        const analyser = audioContext.createAnalyser()
        analyser.fftSize = 512
        analyser.smoothingTimeConstant = .8
        audioContext.createMediaStreamSource(stream).connect(analyser)
        const chunks = []
        let recorder
        try {
            recorder = new MediaRecorder(stream)
            recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
            recorder.start()
        } catch {
            stream.getTracks().forEach((t) => t.stop())
            callbacks.current.onError?.('Не удалось начать запись')
            return
        }
        stateRef.current = { stream, audioContext, analyser, recorder, chunks, t0: performance.now(), levels: [], raf: 0 }
        setElapsed(0)
        setRecording(true)
        stateRef.current.raf = requestAnimationFrame(draw)
    }, [draw])

    // Release the microphone if the page unmounts mid-recording.
    useEffect(() => () => {
        const r = stateRef.current
        if (r) {
            cancelAnimationFrame(r.raf)
            r.recorder.onstop = null
            try { r.recorder.stop() } catch { /* already stopped */ }
            r.stream.getTracks().forEach((t) => t.stop())
            r.audioContext.close().catch(() => {})
        }
    }, [])

    return { recording, elapsed, canvasRef, start, stop }
}
