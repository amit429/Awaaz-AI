import { useCallback, useRef, useState } from 'react';

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

/** Record from the microphone; `stop()` resolves with the audio. */
export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const r = new MediaRecorder(stream);
    chunks.current = [];
    r.ondataavailable = (e) => e.data.size > 0 && chunks.current.push(e.data);
    r.start();
    rec.current = r;
    setRecording(true);
  }, []);

  const stop = useCallback(
    () =>
      new Promise<Blob | null>((resolve) => {
        const r = rec.current;
        if (!r) return resolve(null);
        r.onstop = () => {
          r.stream.getTracks().forEach((t) => t.stop());
          setRecording(false);
          resolve(new Blob(chunks.current, { type: r.mimeType || 'audio/webm' }));
        };
        r.stop();
      }),
    [],
  );

  return { recording, start, stop };
}
