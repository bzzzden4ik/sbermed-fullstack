import React, { useState, useRef } from 'react';
import { useSession } from '../../../entities/session';
import { api } from '@/shared/api/axios-client.js'
import './CircularAudioRecorder.css';

export const AudioRecorder = () => {
  // Состояния: 'idle' | 'recording' | 'uploading'
  const [status, setStatus] = useState('idle');

  const {userId} = useSession()

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const handleRecordClick = async () => {
    if (status === 'idle') {
      await startRecording();
    } else if (status === 'recording') {
      stopRecording();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/mp4';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      // Как только запись остановлена — сразу собираем Blob и отправляем
      mediaRecorder.onstop = async () => {
        const finalBlob = new Blob(audioChunksRef.current, { type: mimeType });
        
        // Отключаем микрофон
        stream.getTracks().forEach((track) => track.stop());

        // Сразу запускаем отправку
        await sendAudio(finalBlob);
      };

      mediaRecorder.start();
      setStatus('recording');
    } catch (err) {
      console.error('Ошибка доступа к микрофону:', err);
      alert('Нет доступа к микрофону');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && status === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  // Автоматическая отправка
  const sendAudio = async (blob) => {
    if (!blob || !api) return;

    setStatus('uploading');
    const formData = new FormData();
    const fileExtension = blob.type.includes('webm') ? 'webm' : 'mp4';

    formData.append('file', blob, `voice_record.${fileExtension}`);
    if (userId) {
      formData.append('patient_id', userId);
    }

    try {
      await api.post('/medical-records/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        }
      });
      alert('Голосовое успешно отправлено!');
    } catch (err) {
      console.error('Ошибка отправки:', err);
      alert('Ошибка при загрузке файла.');
    } finally {
      // Возвращаем кнопку в исходный вид
      setStatus('idle');
    }
  };

  // Иконки
  const MicroIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
    </svg>
  );

  const StopIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );

  const SpinnerIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none" className="spin-loader">
      <circle cx="12" cy="12" r="10" strokeWidth="4" opacity="0.25" />
      <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );

  return (
    <div className="recorder-container">
      <div className={`recorder-wrapper ${status === 'recording' ? 'is-recording' : ''}`}>
        
        {/* Анимационные волны при записи */}
        <div className="pulse-ring"></div>
        <div className="pulse-ring delay-1"></div>
        <div className="pulse-ring delay-2"></div>

        <button 
          className={`circular-button state-${status}`} 
          onClick={handleRecordClick}
          disabled={status === 'uploading'}
        >
          {status === 'idle' && <MicroIcon />}
          {status === 'recording' && <StopIcon />}
          {status === 'uploading' && <SpinnerIcon />}
        </button>
      </div>
    </div>
  );
};