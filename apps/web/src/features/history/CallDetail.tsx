import { useQuery } from '@tanstack/react-query';
import { ChevronLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { splitByEntities } from '@/lib/feed';
import { maskNumber, when } from '@/lib/format';
import { cn } from '@/lib/utils';

export function CallDetail() {
  const { t } = useTranslation();
  const tr = t;
  const { id = '' } = useParams();
  const q = useQuery({ queryKey: ['call', id], queryFn: () => api.call(id) });
  const call = q.data?.call;
  const turns = q.data?.turns ?? [];

  return (
    <AppShell title={call?.name ?? (call ? maskNumber(call.other_number) : t('common.call'))} action={<Button variant="ghost" asChild><Link to="/"><ChevronLeft className="size-4" /> {t('nav.calls')}</Link></Button>}>
      {q.isLoading && <Skeleton className="h-48 w-full rounded-2xl" />}
      {q.isError && <Alert variant="destructive" role="alert"><AlertDescription>{t('history.loadFailed')}</AlertDescription></Alert>}
      {call && (
        <div className="grid gap-6">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>{when(call.created_at)}</span>
            <span>{maskNumber(call.other_number)}</span>
            <Badge variant="secondary">{t(`status.${call.status}`, { defaultValue: call.status })}</Badge>
          </div>
          <section className="grid gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">{t('history.transcript')}</h2>
            {turns.length === 0 && <p className="text-sm text-muted-foreground">{t('history.nothingSaid')}</p>}
            <div className="flex flex-col gap-2">
              {turns.map((turn) => {
                const them = turn.speaker === 'other';
                return (
                  <div key={turn.seq} className={cn('max-w-[88%] rounded-2xl px-4 py-2.5', them ? 'self-start rounded-bl-md bg-secondary' : 'self-end rounded-br-md bg-accent text-accent-foreground')}>
                    <p className="mb-0.5 text-xs opacity-70">{them ? tr('history.them') : turn.source === 'disclosure' ? tr('history.opening') : turn.source === 'keeper' ? tr('history.hold') : tr('history.you')}</p>
                    <p className="text-base leading-snug">
                      {splitByEntities(turn.text, (turn.entities ?? []) as never).map((p, i) => (p.entity ? <b key={i} className="rounded-md bg-accent px-1.5 text-accent-foreground">{p.text}</b> : <span key={i}>{p.text}</span>))}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}
