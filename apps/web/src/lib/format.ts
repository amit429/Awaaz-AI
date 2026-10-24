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

