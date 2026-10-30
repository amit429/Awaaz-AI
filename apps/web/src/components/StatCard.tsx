import type { LucideIcon } from 'lucide-react';
import { Card } from '@/components/ui/card';

/** One number on the dashboard, with a label and an optional line of detail underneath. */
export function StatCard({ icon: Icon, label, value, hint }: { icon: LucideIcon; label: string; value: string; hint?: string }) {
  return (
    <Card className="gap-2 p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="grid size-7 place-items-center rounded-full bg-accent text-accent-foreground"><Icon className="size-4" /></span>
        <span className="truncate">{label}</span>
      </div>
      <p className="line-clamp-2 break-words text-2xl font-semibold leading-tight">{value}</p>
      <p className="min-h-4 truncate text-xs text-muted-foreground">{hint ?? ''}</p>
    </Card>
  );
}
