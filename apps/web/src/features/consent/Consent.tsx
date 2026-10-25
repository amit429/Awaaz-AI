import { Ear, Loader2, Mic, Phone, ShieldCheck, Users, Mail, MessageSquareText, type LucideIcon } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Centered } from '@/components/AppShell';
import { Brand } from '@/components/Brand';
import { LanguageSelect } from '@/components/LanguageSelect';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useConsent, useMe } from '@/hooks/useData';
import { setAppLanguage } from '@/i18n';
import { supabase } from '@/lib/supabase';
import { setDevLogin } from '@/lib/auth';

/** A 10-digit Indian mobile number gets +91; anything else must already have its country code. */
export function normalisePhone(input: string): string | null {
  const digits = input.replace(/[\s\-()]/g, '');
  if (/^[6-9]\d{9}$/.test(digits)) return `+91${digits}`;
  if (/^\+[1-9]\d{7,14}$/.test(digits)) return digits;
  return null;
}

const ITEMS: { key: string; icon: LucideIcon }[] = [
  { key: 'email', icon: Mail },
  { key: 'calls', icon: Users },
  { key: 'text', icon: MessageSquareText },
  { key: 'mic', icon: Mic },
  { key: 'share', icon: ShieldCheck },
  { key: 'other', icon: Ear },
];

/** Shown once after sign-up or sign-in, before anything is collected or used. */
export function Consent() {
  const { t, i18n } = useTranslation();
  const nav = useNavigate();
  const me = useMe();
  const consent = useConsent();
  const qc = useQueryClient();
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState(false);

  useEffect(() => {
    if (me.data?.consented) nav(me.data.onboarded ? '/' : '/onboarding', { replace: true });
  }, [me.data, nav]);

  if (!me.data) return <Centered><Skeleton className="h-8 w-40" /><Skeleton className="mt-6 h-40 w-full" /></Centered>;

  async function decline() {
    await supabase.auth.signOut();
    setDevLogin(false);
    qc.clear();
    nav('/login', { replace: true });
  }

  function agree() {
    const value = phone.trim();
    const normal = value ? normalisePhone(value) : undefined;
    if (value && !normal) return setPhoneError(true);
    setPhoneError(false);
    consent.mutate(normal ?? undefined);
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-xl flex-col px-4 py-8">
      <div className="flex items-center justify-between gap-4">
        <Brand />
        <LanguageSelect value={i18n.language} onChange={(c) => void setAppLanguage(c)} className="h-10 w-44 text-sm" />
      </div>
      <h1 className="mt-8 text-3xl font-semibold sm:text-4xl">{t('consent.title')}</h1>
      <p className="mt-2 text-muted-foreground">{t('consent.intro')}</p>

      <ul className="mt-6 grid gap-3">
        {ITEMS.slice(0, 1).map(({ key, icon: Icon }) => (
          <li key={key} className="flex gap-3 rounded-xl border bg-card p-3.5">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-secondary text-secondary-foreground"><Icon className="size-[18px]" /></span>
            <span>
              <span className="block font-medium leading-tight">{t(`consent.${key}Title`)}</span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{t(`consent.${key}Body`)}</span>
            </span>
          </li>
        ))}
        <li className="flex gap-3 rounded-xl border bg-card p-3.5">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-secondary text-secondary-foreground"><Phone className="size-[18px]" /></span>
          <span className="grid flex-1 gap-2">
            <span>
              <span className="block font-medium leading-tight">{t('consent.phoneTitle')}</span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{t('consent.phoneBody')}</span>
            </span>
            <Label htmlFor="own-phone" className="sr-only">{t('consent.phoneLabel')}</Label>
            <Input id="own-phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="+91 98765 43210" value={phone} aria-invalid={phoneError} onChange={(e) => { setPhone(e.target.value); setPhoneError(false); }} className="h-11" />
            <span className="text-sm text-muted-foreground">{t('consent.phoneHint')}</span>
            {phoneError && <span role="alert" className="text-sm text-destructive">{t('consent.phoneInvalid')}</span>}
          </span>
        </li>
        {ITEMS.slice(1).map(({ key, icon: Icon }) => (
          <li key={key} className="flex gap-3 rounded-xl border bg-card p-3.5">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-secondary text-secondary-foreground"><Icon className="size-[18px]" /></span>
            <span>
              <span className="block font-medium leading-tight">{t(`consent.${key}Title`)}</span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{t(`consent.${key}Body`)}</span>
            </span>
          </li>
        ))}
      </ul>

      {consent.isError && <Alert variant="destructive" role="alert" className="mt-4"><AlertDescription>{t('consent.failed')}</AlertDescription></Alert>}
      <div className="mt-6 grid gap-2">
        <Button size="lg" disabled={consent.isPending} onClick={agree}>
          {consent.isPending && <Loader2 className="size-4 animate-spin" />} {t('consent.agree')}
        </Button>
        <Button variant="ghost" onClick={() => void decline()}>{t('consent.decline')}</Button>
      </div>
    </div>
  );
}
