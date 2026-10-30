import { maskNumber } from './format';
import type { CallRow } from './types';

const FINISHED = ['ended', 'failed', 'no_answer', 'busy'];

export interface CallStats {
  /** Real calls placed in the window (practice calls and tasks are not counted). */
  calls: number;
  /** Seconds spent on calls that were picked up. */
  talkSeconds: number;
  answered: number;
  /** Calls that have finished (picked up or not): the base of the rate. */
  finished: number;
  /** Share of finished calls that were picked up, or null before any call has finished. */
  answeredPct: number | null;
  /** Average length of the calls that were picked up, or null if none were. */
  avgSeconds: number | null;
  /** When the latest call in the window was placed. */
  lastAt: string | null;
  /** Who was called most, over every call loaded. */
  top: { name: string; calls: number } | null;
}

/** The numbers on the dashboard, worked out from the call history the app already has. */
export function callStats(rows: CallRow[], now: Date = new Date(), days = 7): CallStats {
  const real = rows.filter((c) => c.provider !== 'mock' && c.kind !== 'task');
  const since = now.getTime() - days * 86_400_000;
  const recent = real.filter((c) => new Date(c.created_at).getTime() >= since);
  const finished = recent.filter((c) => FINISHED.includes(c.status));
  const answered = finished.filter((c) => c.status === 'ended');

  const counts = new Map<string, { name: string; calls: number }>();
  for (const c of real) {
    const entry = counts.get(c.other_number) ?? { name: c.name ?? maskNumber(c.other_number), calls: 0 };
    entry.calls += 1;
    counts.set(c.other_number, entry);
  }
  const top = [...counts.values()].sort((a, b) => b.calls - a.calls)[0] ?? null;

  const talkSeconds = answered.reduce((sum, c) => sum + (c.duration_s ?? 0), 0);
  const latest = [...recent].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];

  return {
    calls: recent.length,
    talkSeconds,
    avgSeconds: answered.length ? Math.round(talkSeconds / answered.length) : null,
    lastAt: latest?.created_at ?? null,
    answered: answered.length,
    finished: finished.length,
    answeredPct: finished.length ? Math.round((answered.length / finished.length) * 100) : null,
    top,
  };
}
