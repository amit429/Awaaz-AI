import { Phone, User, Users, type LucideIcon } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { Brand } from '@/components/Brand';
import { cn } from '@/lib/utils';

const TABS: { to: string; icon: LucideIcon; label: string; end?: boolean }[] = [
  { to: '/', icon: Phone, label: 'Calls', end: true },
  { to: '/contacts', icon: Users, label: 'Contacts' },
  { to: '/me', icon: User, label: 'Me' },
];

/** Page frame for the signed-in app: top bar with navigation on wide screens, tab bar on phones. */
export function AppShell({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="pt-safe sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-3xl items-center gap-6 px-4">
          <Brand />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
            {TABS.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) =>
                  cn('rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors', isActive ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground')
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 pb-28 pt-6 md:pb-12">
        <div className="mb-6 flex items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold">{title}</h1>
          {action}
        </div>
        {children}
      </main>

      <nav className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t bg-background/90 backdrop-blur md:hidden" aria-label="Main">
        <ul className="mx-auto flex max-w-3xl">
          {TABS.map((t) => (
            <li key={t.to} className="flex-1">
              <NavLink to={t.to} end={t.end} className={({ isActive }) => cn('flex flex-col items-center gap-1 py-2.5 text-xs font-medium', isActive ? 'text-foreground' : 'text-muted-foreground')}>
                {({ isActive }) => (
                  <>
                    <span className={cn('grid h-7 w-14 place-items-center rounded-full transition-colors', isActive && 'bg-accent text-accent-foreground')}>
                      <t.icon className="size-5" />
                    </span>
                    {t.label}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

export function Centered({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-4 py-10">{children}</div>;
}
