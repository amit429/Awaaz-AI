import { useQuery } from '@tanstack/react-query';
import { ChevronLeft } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { splitByEntities } from '@/lib/feed';
import { maskNumber, STATUS_TEXT, when } from '@/lib/format';
import { cn } from '@/lib/utils';

export function CallDetail() {
  const { id = '' } = useParams();
  const q = useQuery({ queryKey: ['call', id], queryFn: () => api.call(id) });
  const call = q.data?.call;
  const turns = q.data?.turns ?? [];

  return (
    <AppShell title={call?.name ?? (call ? maskNumber(call.other_number) : 'Call')} action={<Button variant="ghost" asChild><Link to="/"><ChevronLeft className="size-4" /> Calls</Link></Button>}>
      {q.isLoading && <Skeleton className="h-48 w-full rounded-2xl" />}
      {q.isError && <Alert variant="destructive" role="alert"><AlertDescription>Could not load this call.</AlertDescription></Alert>}
      {call && (
        <div className="grid gap-6">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>{when(call.created_at)}</span>
            <span>{maskNumber(call.other_number)}</span>
            <Badge variant="secondary">{STATUS_TEXT[call.status] ?? call.status}</Badge>
          </div>
          <section className="grid gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">Transcript</h2>
            {turns.length === 0 && <p className="text-sm text-muted-foreground">Nothing was said on this call.</p>}
            <div className="flex flex-col gap-2">
              {turns.map((t) => {
                const them = t.speaker === 'other';
                return (
                  <div key={t.seq} className={cn('max-w-[88%] rounded-2xl px-4 py-2.5', them ? 'self-start rounded-bl-md bg-secondary' : 'self-end rounded-br-md bg-accent text-accent-foreground')}>
                    <p className="mb-0.5 text-xs opacity-70">{them ? 'Them' : t.source === 'disclosure' ? 'Awaaz, opening line' : t.source === 'keeper' ? 'Awaaz, please hold' : 'You'}</p>
                    <p className="text-base leading-snug">
                      {splitByEntities(t.text, (t.entities ?? []) as never).map((p, i) => (p.entity ? <b key={i} className="rounded-md bg-accent px-1.5 text-accent-foreground">{p.text}</b> : <span key={i}>{p.text}</span>))}
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
