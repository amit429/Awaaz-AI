import { cn } from '@/lib/utils';

/** The Awaaz mark: four bars, like a voice level. The two lower-right bars carry the accent. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn('size-8', className)} aria-hidden="true">
      <rect width="32" height="32" rx="9" className="fill-primary" />
      <rect x="7" y="13" width="3.4" height="7" rx="1.7" className="fill-primary-foreground" />
      <rect x="12.5" y="8" width="3.4" height="16" rx="1.7" className="fill-primary-foreground" />
      <rect x="18" y="11" width="3.4" height="10" rx="1.7" className="fill-accent" />
      <rect x="23.5" y="14" width="3.4" height="4" rx="1.7" className="fill-accent" />
    </svg>
  );
}

export function Brand({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2 font-display text-lg font-semibold tracking-tight', className)}>
      <BrandMark />
      Awaaz
    </span>
  );
}
