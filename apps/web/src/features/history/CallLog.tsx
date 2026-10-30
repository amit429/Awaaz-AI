import { ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { EmptyState, Person, RowList } from '@/components/Person';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useCalls } from '@/hooks/useData';
import { duration, maskNumber, when } from '@/lib/format';
import { cn } from '@/lib/utils';

type Filter = 'all' | 'answered' | 'missed';
const MISSED = ['failed', 'no_answer', 'busy'];

/** Every call, newest first, with who, when, how long and how it went. */
export function CallLog() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const calls = useCalls();
  const [filter, setFilter] = useState<Filter>('all');

  const rows = (calls.data ?? []).filter((c) => c.kind !== 'task');
  const shown = rows.filter((c) => (filter === 'answered' ? c.status === 'ended' : filter === 'missed' ? MISSED.includes(c.status) : true));

  return (
    <AppShell title={t('log.title')}>
      <div className="grid gap-4">
        <div className="flex gap-2" role="group" aria-label={t('log.filters')}>
          {(['all', 'answered', 'missed'] as const).map((f) => (
            <Button key={f} type="button" size="sm" variant={filter === f ? 'default' : 'secondary'} aria-pressed={filter === f} onClick={() => setFilter(f)} className={cn('rounded-full')}>
              {t(`log.filter_${f}`)}
            </Button>
          ))}
        </div>

        {calls.isLoading ? (
          <Skeleton className="h-48 w-full rounded-2xl" />
        ) : shown.length === 0 ? (
          <EmptyState title={t('log.emptyTitle')} body={t(rows.length === 0 ? 'log.emptyBody' : 'log.emptyFilter')} />
        ) : (
          <RowList>
            {shown.map((c) => (
              <button key={c.id} type="button" onClick={() => nav(`/calls/${c.id}`)} className="flex w-full items-center gap-3 p-3.5 text-left transition-colors hover:bg-secondary/60">
                <Person name={c.name} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{c.name ?? maskNumber(c.other_number)}</p>
                  <p className="truncate text-sm text-muted-foreground">
                    {when(c.created_at)}{c.status === 'ended' && c.duration_s ? ` · ${duration(c.duration_s)}` : ''}
                  </p>
                </div>
                {c.provider === 'mock' && <Badge variant="outline">{t('common.practice')}</Badge>}
                <Badge variant={c.status === 'ended' ? 'secondary' : 'outline'}>{t(`status.${c.status}`, { defaultValue: c.status })}</Badge>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              </button>
            ))}
          </RowList>
        )}
      </div>
    </AppShell>
  );
}
