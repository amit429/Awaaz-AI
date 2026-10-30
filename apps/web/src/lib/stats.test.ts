import { describe, expect, it } from 'vitest';
import { callStats } from './stats';
import type { CallRow } from './types';

const NOW = new Date('2026-10-30T12:00:00Z');
const day = (n: number) => new Date(NOW.getTime() - n * 86_400_000).toISOString();

let id = 0;
const call = (over: Partial<CallRow> = {}): CallRow => ({
  id: `c${++id}`,
  name: 'Sharma Medical',
  other_number: '+919876543210',
  kind: 'relay',
  provider: 'bolna',
  status: 'ended',
  created_at: day(1),
  call_lang: 'hi',
  duration_s: 60,
  ...over,
});

describe('call stats', () => {
  it('counts calls and talk time in the last 7 days only', () => {
    const s = callStats([call({ duration_s: 120 }), call({ duration_s: 30, created_at: day(6) }), call({ created_at: day(8) })], NOW);
    expect(s.calls).toBe(2);
    expect(s.talkSeconds).toBe(150);
  });

  it('leaves practice calls and tasks out', () => {
    const s = callStats([call(), call({ provider: 'mock' }), call({ kind: 'task' })], NOW);
    expect(s.calls).toBe(1);
  });

  it('works out how many calls were picked up, ignoring calls still going', () => {
    const s = callStats(
      [call(), call(), call({ status: 'failed', duration_s: null }), call({ status: 'failed', duration_s: null }), call({ status: 'connected', duration_s: null })],
      NOW,
    );
    expect(s.calls).toBe(5);
    expect(s.answered).toBe(2);
    expect(s.answeredPct).toBe(50); // 2 of the 4 that finished
  });

  it('has no rate when nothing has finished', () => {
    expect(callStats([], NOW).answeredPct).toBeNull();
    expect(callStats([call({ status: 'ringing', duration_s: null })], NOW).answeredPct).toBeNull();
  });

  it('finds the contact called most, across all loaded calls', () => {
    const s = callStats(
      [call({ name: 'Netra Clinic', other_number: '+911' }), call({ created_at: day(40) }), call({ created_at: day(41) }), call({ created_at: day(2) })],
      NOW,
    );
    expect(s.top).toEqual({ name: 'Sharma Medical', calls: 3 });
  });

  it('names an unsaved number by its last four digits and counts it as one person', () => {
    const s = callStats([call({ name: null, other_number: '+919800001234' }), call({ name: null, other_number: '+919800001234' })], NOW);
    expect(s.top).toEqual({ name: '••••1234', calls: 2 });
  });

  it('has no favourite when there are no calls', () => {
    expect(callStats([], NOW).top).toBeNull();
  });

  it('gives the average length of calls that were picked up and when the last call was', () => {
    const s = callStats(
      [call({ duration_s: 60, created_at: day(2) }), call({ duration_s: 180, created_at: day(1) }), call({ status: 'failed', duration_s: null, created_at: day(3) })],
      NOW,
    );
    expect(s.avgSeconds).toBe(120);
    expect(s.lastAt).toBe(day(1));
    expect(callStats([], NOW).avgSeconds).toBeNull();
    expect(callStats([], NOW).lastAt).toBeNull();
  });
});
