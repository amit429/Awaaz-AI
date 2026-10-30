export const initials = (name: string) =>
  name.replace(/[^\p{L}\s]/gu, '').split(/\s+/).filter(Boolean).map((w) => w[0]).join('').slice(0, 2).toUpperCase() || '#';

const IST = 'Asia/Kolkata';

/** Times are stored in UTC and shown in IST. */
export function when(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat('en-IN', { timeZone: IST, day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }).format(d);
}

export function maskNumber(n: string): string {
  return n.length > 4 ? `••••${n.slice(-4)}` : n;
}


/** 45 s, 3 min, 1 h 5 min. Used for how long a call lasted. */
export function duration(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  if (seconds < 60) return `${Math.max(0, Math.round(seconds))} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}
