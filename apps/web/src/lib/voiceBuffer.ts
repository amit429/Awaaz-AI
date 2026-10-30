/**
 * Speech to text hands back a phrase at every short pause, but people pause mid-sentence. The
 * buffer collects phrases and sends them as one message once there has been a real pause, or when
 * they are cut off for good. A pause only counts if they have not started speaking again.
 */
export interface VoiceBuffer {
  /** A finished phrase arrived. Returns everything heard since the last message. */
  text(phrase: string): string;
  /** They started speaking again: do not send yet. */
  speechStarted(): void;
  /** Send what has been heard now (the mic was stopped). */
  flush(): void;
  /** Forget what has been heard (the call ended). */
  cancel(): void;
}

export const VOICE_GAP_MS = 1800; // quiet this long after a phrase = the message is finished
export const VOICE_MAX_WAIT_MS = 10000; // never hold a message longer than this, however they talk

export function createVoiceBuffer(
  onSend: (text: string) => void,
  { gapMs = VOICE_GAP_MS, maxWaitMs = VOICE_MAX_WAIT_MS }: { gapMs?: number; maxWaitMs?: number } = {},
): VoiceBuffer {
  let parts: string[] = [];
  let gap: ReturnType<typeof setTimeout> | undefined;
  let max: ReturnType<typeof setTimeout> | undefined;

  const clear = () => {
    clearTimeout(gap);
    clearTimeout(max);
    gap = max = undefined;
  };
  const flush = () => {
    const message = parts.join(' ').trim();
    parts = [];
    clear();
    if (message) onSend(message);
  };

  return {
    text(phrase) {
      parts.push(phrase.trim());
      clearTimeout(gap);
      gap = setTimeout(flush, gapMs);
      max ??= setTimeout(flush, maxWaitMs);
      return parts.join(' ');
    },
    speechStarted() {
      clearTimeout(gap);
      gap = undefined;
    },
    flush,
    cancel() {
      parts = [];
      clear();
    },
  };
}
