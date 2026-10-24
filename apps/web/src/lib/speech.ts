import { useCallback, useEffect, useRef, useState } from 'react';
import { getToken } from './auth';
import { WS_BASE } from './config';

/** Browser voices by language code; Hinglish is Latin text, so an English (India) voice reads it best. */
const VOICE_LANG: Record<string, string> = {
  en: 'en-IN', hi: 'hi-IN', 'hi-Latn': 'en-IN', mr: 'mr-IN', bn: 'bn-IN', ta: 'ta-IN', te: 'te-IN',
  kn: 'kn-IN', gu: 'gu-IN', pa: 'pa-IN', ml: 'ml-IN', or: 'or-IN',
};

export const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;
export const canVibrate = typeof navigator !== 'undefined' && 'vibrate' in navigator;

/** Read text aloud, slower and at full volume. Words and numbers are read exactly as written. */
export function speak(text: string, lang: string, rate = 0.8): void {
  if (!canSpeak || !text.trim()) return;
  const u = new SpeechSynthesisUtterance(text);
  const key = lang === 'hi-Latn' ? lang : (lang.split('-')[0] ?? 'en');
  u.lang = VOICE_LANG[key] ?? 'en-IN';
  u.rate = rate;
  u.volume = 1;
  window.speechSynthesis.speak(u);
}

export function stopSpeaking(): void {
  if (canSpeak) window.speechSynthesis.cancel();
}

export function buzz(pattern: number | number[]): void {
  if (canVibrate) navigator.vibrate(pattern);
}

export interface LiveVoiceHandlers {
  onSpeechStart: () => void;
  onText: (text: string) => void;
  onError: (code: 'denied' | 'unavailable' | 'failed') => void;
}

/**
 * Live voice: the microphone is streamed to the server, which streams it to speech to text and
 * returns each finished sentence. Nothing here speaks on the call; the caller decides what to do
 * with the text.
 */
export function useLiveVoice(lang: string, handlers: LiveVoiceHandlers) {
  const [active, setActive] = useState(false);
  const h = useRef(handlers);
  h.current = handlers;
  const parts = useRef<{ ws?: WebSocket; ctx?: AudioContext; stream?: MediaStream }>({});

  const stop = useCallback(() => {
    const { ws, ctx, stream } = parts.current;
    parts.current = {};
    stream?.getTracks().forEach((t) => t.stop());
    void ctx?.close().catch(() => undefined);
    if (ws && ws.readyState <= 1) ws.close();
    setActive(false);
  }, []);

  const start = useCallback(async () => {
    try {
      const token = await getToken();
      const ws = new WebSocket(`${WS_BASE}/v1/stt/ws?token=${encodeURIComponent(token)}&lang=${encodeURIComponent(lang)}`);
      ws.binaryType = 'arraybuffer';
      parts.current.ws = ws;
      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () => reject(new Error('unavailable'));
      });
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
      } catch {
        stop();
        return h.current.onError('denied');
      }
      parts.current.stream = stream;
      const ctx = new AudioContext();
      parts.current.ctx = ctx;
      await ctx.audioWorklet.addModule('/pcm-worklet.js');
      const node = new AudioWorkletNode(ctx, 'pcm-worklet');
      node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => ws.readyState === WebSocket.OPEN && ws.send(e.data);
      ctx.createMediaStreamSource(stream).connect(node);
      ws.onmessage = (e: MessageEvent<string>) => {
        const m = JSON.parse(e.data) as { t: string; signal?: string; text?: string; code?: string };
        if (m.t === 'vad' && m.signal === 'start') h.current.onSpeechStart();
        else if (m.t === 'transcript' && m.text) h.current.onText(m.text);
        else if (m.t === 'error') {
          h.current.onError('unavailable');
          stop();
        }
      };
      ws.onclose = () => {
        if (parts.current.ws === ws) stop();
      };
      setActive(true);
    } catch {
      stop();
      h.current.onError('failed');
    }
  }, [lang, stop]);

  useEffect(() => stop, [stop]);
  return { active, start, stop };
}
