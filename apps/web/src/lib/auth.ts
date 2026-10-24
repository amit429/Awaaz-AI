import { API_BASE } from './config';
import { supabase } from './supabase';

// Local development shortcut: the API mints a token for a dev user (POST /v1/dev/token).
// Only offered when VITE_DEV_LOGIN=true; never in a production build.
export const DEV_LOGIN = import.meta.env.VITE_DEV_LOGIN === 'true';
const DEV_FLAG = 'awaaz-dev-login';
let devToken: string | null = null;

export const devLoginActive = (): boolean => {
  try {
    return DEV_LOGIN && localStorage.getItem(DEV_FLAG) === '1';
  } catch {
    return false;
  }
};

export function setDevLogin(on: boolean): void {
  try {
    if (on) localStorage.setItem(DEV_FLAG, '1');
    else localStorage.removeItem(DEV_FLAG);
  } catch {
    /* storage unavailable: the shortcut just won't persist */
  }
  devToken = null;
  window.dispatchEvent(new Event('awaaz-auth'));
}

export async function getToken(): Promise<string> {
  const { data } = await supabase.auth.getSession();
  if (data.session) return data.session.access_token;
  if (devLoginActive()) {
    if (devToken) return devToken;
    const res = await fetch(`${API_BASE}/dev/token`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (!res.ok) throw new Error('Could not sign in');
    devToken = ((await res.json()) as { token: string }).token;
    return devToken;
  }
  throw new Error('Not signed in');
}

/** A translation key for a Supabase auth error, or the message itself when it is not one we know. */
export function friendlyAuthError(message: string): string {
  const m = message.toLowerCase();
  if (m.includes('invalid login credentials')) return 'authErrors.wrongPassword';
  if (m.includes('email not confirmed')) return 'authErrors.notConfirmed';
  if (m.includes('already registered') || m.includes('already been registered')) return 'authErrors.exists';
  if (m.includes('password') && m.includes('at least')) return 'authErrors.shortPassword';
  if (m.includes('rate limit') || m.includes('too many')) return 'authErrors.tooMany';
  if (m.includes('valid email') || m.includes('invalid email')) return 'authErrors.badEmail';
  if (m.includes('provider is not enabled') || m.includes('unsupported provider')) return 'authErrors.googleOff';
  return message || 'authErrors.generic';
}
