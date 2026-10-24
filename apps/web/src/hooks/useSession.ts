import { useEffect, useState } from 'react';
import { devLoginActive } from '../lib/auth';
import { supabase } from '../lib/supabase';

export interface SessionState {
  loading: boolean;
  signedIn: boolean;
  email: string | null;
}

export function useSession(): SessionState {
  const [state, setState] = useState<SessionState>({ loading: true, signedIn: false, email: null });

  useEffect(() => {
    let alive = true;
    const apply = (email: string | null) => {
      if (!alive) return;
      const dev = devLoginActive();
      setState({ loading: false, signedIn: Boolean(email) || dev, email: email ?? (dev ? 'dev user' : null) });
    };
    void supabase.auth.getSession().then(({ data }) => apply(data.session?.user.email ?? null));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => apply(session?.user.email ?? null));
    const onDev = () => void supabase.auth.getSession().then(({ data }) => apply(data.session?.user.email ?? null));
    window.addEventListener('awaaz-auth', onDev);
    return () => {
      alive = false;
      sub.subscription.unsubscribe();
      window.removeEventListener('awaaz-auth', onDev);
    };
  }, []);

  return state;
}
