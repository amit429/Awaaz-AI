import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createVoiceBuffer } from './voiceBuffer';

describe('voice buffer', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('joins phrases separated by a short pause into one message', () => {
    const sent: string[] = [];
    const buf = createVoiceBuffer((t) => sent.push(t), { gapMs: 1800 });
    buf.text('मुझे दवाई चाहिए');
    vi.advanceTimersByTime(900); // a breath, not the end of the sentence
    buf.text('बीपी की');
    vi.advanceTimersByTime(1799);
    expect(sent).toEqual([]);
    vi.advanceTimersByTime(2);
    expect(sent).toEqual(['मुझे दवाई चाहिए बीपी की']);
  });

  it('shows what has been heard so far', () => {
    const buf = createVoiceBuffer(() => undefined);
    expect(buf.text('one')).toBe('one');
    expect(buf.text('two')).toBe('one two');
  });

  it('waits while they are still speaking, even if the transcript is late', () => {
    const sent: string[] = [];
    const buf = createVoiceBuffer((t) => sent.push(t), { gapMs: 1800, maxWaitMs: 10000 });
    buf.text('first part');
    vi.advanceTimersByTime(1700);
    buf.speechStarted(); // they started again before the gap ended
    vi.advanceTimersByTime(5000);
    expect(sent).toEqual([]);
    buf.text('second part');
    vi.advanceTimersByTime(1800);
    expect(sent).toEqual(['first part second part']);
  });

  it('never holds a message longer than the maximum wait', () => {
    const sent: string[] = [];
    const buf = createVoiceBuffer((t) => sent.push(t), { gapMs: 1800, maxWaitMs: 10000 });
    buf.text('a');
    for (let i = 0; i < 12; i++) {
      vi.advanceTimersByTime(1500);
      buf.speechStarted();
      buf.text(`b${i}`);
    }
    expect(sent.length).toBeGreaterThan(0);
    expect(sent[0]).toMatch(/^a b0/);
  });

  it('sends at once when asked (the mic is stopped) and ignores empty input', () => {
    const sent: string[] = [];
    const buf = createVoiceBuffer((t) => sent.push(t));
    buf.flush();
    buf.text('last words');
    buf.flush();
    vi.advanceTimersByTime(5000);
    expect(sent).toEqual(['last words']);
  });

  it('drops what was heard when cancelled (the call ended)', () => {
    const sent: string[] = [];
    const buf = createVoiceBuffer((t) => sent.push(t));
    buf.text('too late');
    buf.cancel();
    vi.advanceTimersByTime(5000);
    expect(sent).toEqual([]);
  });
});
