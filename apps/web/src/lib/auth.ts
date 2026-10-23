import { API_BASE } from './config';

// Local development: the API mints a token (POST /v1/dev/token). Supabase sign-in replaces this.
let cached: string | null = null;

export async function getToken(): Promise<string> {
  if (cached) return cached;
  const res = await fetch(`${API_BASE}/dev/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sub: 'dev-user' }),
  });
  if (!res.ok) throw new Error('Could not sign in');
  cached = ((await res.json()) as { token: string }).token;
  return cached;
}
