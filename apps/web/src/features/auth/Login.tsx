import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { useSession } from '../../hooks/useSession';
import { DEV_LOGIN, friendlyAuthError, setDevLogin } from '../../lib/auth';
import { supabase } from '../../lib/supabase';

type Mode = 'signin' | 'signup';

export function Login() {
  const session = useSession();
  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  if (session.signedIn) return <Navigate to="/" replace />;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    const creds = { email: email.trim(), password };
    const { data, error: err } = mode === 'signin' ? await supabase.auth.signInWithPassword(creds) : await supabase.auth.signUp(creds);
    setBusy(false);
    if (err) return setError(friendlyAuthError(err.message));
    if (mode === 'signup' && !data.session) setNotice('Account created. Check your email for a link to confirm it, then sign in.');
  }

  async function google() {
    setError('');
    const { error: err } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } });
    if (err) setError(friendlyAuthError(err.message));
  }

  async function reset() {
    if (!email.trim()) return setError('Type your email above first, then tap “Forgot password”.');
    const { error: err } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: window.location.origin });
    if (err) return setError(friendlyAuthError(err.message));
    setError('');
    setNotice('If that email has an account, we sent a link to reset the password.');
  }

  return (
    <div className="app">
      <div className="navtitle"><h4>{mode === 'signin' ? 'Sign in' : 'Create your account'}</h4></div>
      <div className="scroll">
        <p style={{ color: 'var(--ink-2)' }}>Awaaz makes phone calls possible for people who can’t hear or speak.</p>
        <button className="cta soft" type="button" onClick={() => void google()}>Continue with Google</button>
        <div className="label" style={{ textAlign: 'center' }}>or with your email</div>
        <form className="cardx" onSubmit={(e) => void submit(e)}>
          <input className="sel" style={{ width: '100%', font: 'inherit', marginBottom: '.5rem' }} type="email" autoComplete="email" aria-label="Email" placeholder="Email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="sel" style={{ width: '100%', font: 'inherit' }} type="password" autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} aria-label="Password" placeholder="Password" minLength={6} required value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <p className="err" role="alert">{error}</p>}
          {notice && <p style={{ color: 'var(--live)', fontSize: '.88rem' }} role="status">{notice}</p>}
          <button className="cta" type="submit" disabled={busy || !email || password.length < 6} style={{ marginTop: '.7rem' }}>
            <Icon name="check" /> {mode === 'signin' ? 'Sign in' : 'Create account'}
          </button>
        </form>
        <button className="cta soft" type="button" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(''); setNotice(''); }}>
          {mode === 'signin' ? 'New here? Create an account' : 'Already have an account? Sign in'}
        </button>
        {mode === 'signin' && <button className="cta soft" type="button" onClick={() => void reset()}>Forgot password</button>}
        {DEV_LOGIN && <button className="cta soft" type="button" onClick={() => setDevLogin(true)}>Continue as the dev user (local only)</button>}
      </div>
    </div>
  );
}
