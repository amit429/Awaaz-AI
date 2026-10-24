import { Phone } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { initials } from '@/lib/format';
import { cn } from '@/lib/utils';

export function Person({ name, accent, className }: { name?: string | null; accent?: boolean; className?: string }) {
  return (
    <Avatar className={cn('size-11', className)}>
      <AvatarFallback className={cn('text-sm font-semibold', accent ? 'bg-accent text-accent-foreground' : 'bg-secondary text-secondary-foreground')}>{name ? initials(name) : <Phone className="size-4" />}</AvatarFallback>
    </Avatar>
  );
}

/** A bordered list: one card, rows divided by lines. Used instead of a stack of separate cards. */
export function RowList({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('divide-y overflow-hidden rounded-2xl border bg-card', className)}>{children}</div>;
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed p-8 text-center">
      <p className="font-medium">{title}</p>
      <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{body}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
