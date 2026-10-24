import { AlertCircle, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router-dom';
import { Brand } from '@/components/Brand';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSession } from '@/hooks/useSession';
import { DEV_LOGIN, friendlyAuthError, setDevLogin } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { LanguageSelect } from '@/components/LanguageSelect';
import { setAppLanguage } from '@/i18n';
import { CaptionDemo } from './CaptionDemo';

type Mode = 'signin' | 'signup';

const GoogleMark = () => (
  <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
    <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.8z" />
    <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1C3.3 21.4 7.3 24 12 24z" />
    <path fill="#FBBC05" d="M5.3 14.3c-.2-.7-.4-1.5-.4-2.3s.1-1.6.4-2.3V6.6H1.3C.5 8.2 0 10 0 12s.5 3.8 1.3 5.4l4-3.1z" />
    <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4C18 1.2 15.2 0 12 0 7.3 0 3.3 2.6 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9z" />
  </svg>
);

export function Login() {
  const { t, i18n } = useTranslation();
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
    if (err) return setError(t(friendlyAuthError(err.message), { defaultValue: err.message }));
    if (mode === 'signup' && !data.session) setNotice(t('login.accountCreated'));
  }

  async function google() {
    setError('');
    const { error: err } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } });
    if (err) setError(t(friendlyAuthError(err.message), { defaultValue: err.message }));
  }

  async function reset() {
    if (!email.trim()) return setError(t('login.typeEmailFirst'));
    const { error: err } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: window.location.origin });
    if (err) return setError(t(friendlyAuthError(err.message), { defaultValue: err.message }));
    setError('');
    setNotice(t('login.resetSent'));
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.1fr_1fr]">
      <section
        className="dark flex flex-col justify-between gap-10 px-6 py-8 text-foreground sm:px-10 lg:py-12"
        style={{ background: 'radial-gradient(120% 80% at 0% 0%, oklch(0.3 0.08 275), transparent 60%), oklch(0.16 0.035 270)' }}
      >
        <div className="flex items-center justify-between gap-4">
          <Brand />
          <LanguageSelect value={i18n.language} onChange={(c) => void setAppLanguage(c)} className="h-10 w-44 bg-white/10 text-sm" />
        </div>
        <div className="flex flex-col items-start gap-8">
          <h1 className="max-w-xl text-4xl font-semibold leading-[1.08] sm:text-5xl">{t('login.headline')}</h1>
          <p className="max-w-md text-lg text-muted-foreground">{t('login.subhead')}</p>
          <CaptionDemo />
        </div>
        <p className="text-sm text-muted-foreground">{t('login.footnote')}</p>
      </section>

      <section className="flex items-center justify-center px-4 py-10 sm:px-8">
        <Card className="w-full max-w-md border-0 bg-transparent shadow-none lg:border lg:bg-card lg:shadow-sm">
          <CardHeader>
            <CardTitle className="text-2xl">{mode === 'signin' ? t('login.welcomeBack') : t('login.createTitle')}</CardTitle>
            <CardDescription>{mode === 'signin' ? t('login.signInHint') : t('login.createHint')}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <Tabs value={mode} onValueChange={(v) => { setMode(v as Mode); setError(''); setNotice(''); }}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="signin">{t('login.signIn')}</TabsTrigger>
                <TabsTrigger value="signup">{t('login.createAccount')}</TabsTrigger>
              </TabsList>
            </Tabs>

            <Button variant="outline" size="lg" className="w-full gap-3" onClick={() => void google()}>
              <GoogleMark /> {t('login.google')}
            </Button>

            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Separator className="flex-1" /> {t('login.orEmail')} <Separator className="flex-1" />
            </div>

            <form className="flex flex-col gap-4" onSubmit={(e) => void submit(e)}>
              <div className="grid gap-2">
                <Label htmlFor="email">{t('login.email')}</Label>
                <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="h-11" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="password">{t('login.password')}</Label>
                <Input id="password" type="password" autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} minLength={6} required value={password} onChange={(e) => setPassword(e.target.value)} className="h-11" />
                {mode === 'signup' && <p className="text-sm text-muted-foreground">{t('login.passwordHint')}</p>}
              </div>
              {error && (
                <Alert variant="destructive" role="alert">
                  <AlertCircle className="size-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              {notice && <Alert role="status"><AlertDescription>{notice}</AlertDescription></Alert>}
              <Button type="submit" size="lg" disabled={busy || !email || password.length < 6}>
                {busy && <Loader2 className="size-4 animate-spin" />}
                {mode === 'signin' ? t('login.signIn') : t('login.createAccount')}
              </Button>
            </form>

            <div className="flex flex-col items-center gap-1">
              {mode === 'signin' && <Button variant="link" onClick={() => void reset()}>{t('login.forgot')}</Button>}
              {DEV_LOGIN && <Button variant="ghost" size="sm" onClick={() => setDevLogin(true)}>{t('login.devUser')}</Button>}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
