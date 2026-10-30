import { CircleCheck, Clock, Loader2, Phone, Star } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LanguageSelect } from '@/components/LanguageSelect';
import { useNavigate } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { EmptyState, Person, RowList } from '@/components/Person';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { StatCard } from '@/components/StatCard';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useCalls, useContacts } from '@/hooks/useData';
import { createCall } from '@/lib/api';
import { duration, when } from '@/lib/format';
import { callStats } from '@/lib/stats';

const PRACTICE = [
  { name: 'Sharma Medical', detail: 'home.practiceSharma', number: '+919800000001', callee: 'pharmacy' },
  { name: 'Netra Clinic', detail: 'home.practiceNetra', number: '+919800000002', callee: 'clinic_mr' },
  { name: 'Unknown number', detail: 'home.practiceScam', number: '+919800000003', callee: 'bank_scam' },
];

export function Home() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const contacts = useContacts();
  const calls = useCalls();
  const [open, setOpen] = useState(false);
  const [number, setNumber] = useState('');
  const [theySpeak, setTheySpeak] = useState('hi');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function start(name: string, to: string, callee?: string, language?: string) {
    setBusy(true);
    setError('');
    try {
      const call = await createCall(to, callee, language);
      nav(`/call/${call.session_id}`, { state: { name, number: to } });
    } catch (e) {
      setError(e instanceof Error ? t(e.message, { defaultValue: e.message }) : t('home.couldNotStart'));
      setBusy(false);
    }
  }

  const favourites = (contacts.data ?? []).filter((c) => c.favourite);
  const stats = useMemo(() => callStats(calls.data ?? []), [calls.data]);
  const loading = contacts.isLoading || calls.isLoading;

  return (
    <AppShell title={t('home.title')} action={<Button onClick={() => setOpen(true)}><Phone className="size-4" /> {t('home.newCall')}</Button>}>
      <div className="grid gap-8">
        {error && <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

        {loading && <Skeleton className="h-32 w-full rounded-2xl" />}

        {favourites.length > 0 && (
          <section className="grid gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">{t('home.favourites')}</h2>
            <RowList>
              {favourites.map((c) => (
                <div key={c.id} className="flex items-center gap-3 p-3.5">
                  <Person name={c.name} accent />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{c.name}</p>
                    <p className="truncate text-sm text-muted-foreground">{c.notes || c.phone_e164}</p>
                  </div>
                  <Button size="icon" className="rounded-full" aria-label={`Call ${c.name}`} disabled={busy} onClick={() => void start(c.name, c.phone_e164, undefined, c.call_lang ?? undefined)}><Phone className="size-4" /></Button>
                </div>
              ))}
            </RowList>
          </section>
        )}

        <section className="grid gap-3">
          <h2 className="text-sm font-medium text-muted-foreground">{t('home.statsTitle')}</h2>
          {loading ? (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[110px] rounded-xl" />)}
            </div>
          ) : (calls.data ?? []).length === 0 ? (
            <EmptyState title={t('home.noCallsTitle')} body={t('home.noCallsBody')} action={<Button onClick={() => setOpen(true)}>{t('home.newCall')}</Button>} />
          ) : (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatCard icon={Phone} label={t('home.stats.calls')} value={String(stats.calls)} hint={stats.lastAt ? t('home.stats.callsHint', { when: when(stats.lastAt) }) : undefined} />
              <StatCard icon={Clock} label={t('home.stats.talk')} value={stats.talkSeconds ? duration(stats.talkSeconds) : '—'} hint={stats.avgSeconds ? t('home.stats.talkHint', { time: duration(stats.avgSeconds) }) : undefined} />
              <StatCard
                icon={CircleCheck}
                label={t('home.stats.answered')}
                value={stats.answeredPct == null ? '—' : `${stats.answeredPct}%`}
                hint={stats.finished ? t('home.stats.answeredHint', { answered: stats.answered, total: stats.finished }) : undefined}
              />
              <StatCard icon={Star} label={t('home.stats.top')} value={stats.top?.name ?? '—'} hint={stats.top ? t('home.stats.topHint', { count: stats.top.calls }) : undefined} />
            </div>
          )}
        </section>

        <section className="grid gap-3">
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-medium text-muted-foreground">{t('home.practiceTitle')}</h2>
            <span className="text-xs text-muted-foreground">{t('home.practiceHint')}</span>
          </div>
          <RowList>
            {PRACTICE.map((p) => (
              <button key={p.number} type="button" disabled={busy} onClick={() => void start(p.name, p.number, p.callee)} className="flex w-full items-center gap-3 p-3.5 text-left transition-colors hover:bg-secondary/60 disabled:opacity-60">
                <Person name={p.name} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{p.name}</p>
                  <p className="truncate text-sm text-muted-foreground">{t(p.detail)}</p>
                </div>
                <Badge variant="outline">{t('common.practice')}</Badge>
              </button>
            ))}
          </RowList>
        </section>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('home.newCall')}</DialogTitle>
            <DialogDescription>{t('home.newCallHint')}</DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={(e) => { e.preventDefault(); const n = number.length === 10 ? `+91${number}` : number; void start(n, n, undefined, theySpeak); }}>
            <div className="grid gap-2">
              <Label htmlFor="number">{t('home.phoneNumber')}</Label>
              <Input id="number" inputMode="tel" autoFocus placeholder="98765 43210" className="h-12 text-lg" value={number} onChange={(e) => setNumber(e.target.value.replace(/[^\d+]/g, ''))} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="they-speak">{t('home.theySpeak')}</Label>
              <LanguageSelect id="they-speak" spokenOnly value={theySpeak} onChange={setTheySpeak} />
            </div>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
            <Button type="submit" size="lg" disabled={busy || number.length < 8}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : <Phone className="size-4" />} {t('home.callButton')}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
