import { ChevronRight, Loader2, Phone } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { EmptyState, Person, RowList } from '@/components/Person';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useCalls, useContacts } from '@/hooks/useData';
import { createCall } from '@/lib/api';
import { maskNumber, STATUS_TEXT, when } from '@/lib/format';

const PRACTICE = [
  { name: 'Sharma Medical', detail: 'Pharmacy, Hindi', number: '+919800000001', callee: 'pharmacy' },
  { name: 'Netra Clinic', detail: 'Clinic, Marathi', number: '+919800000002', callee: 'clinic_mr' },
  { name: 'Unknown number', detail: 'A bank scam call', number: '+919800000003', callee: 'bank_scam' },
];

export function Home() {
  const nav = useNavigate();
  const contacts = useContacts();
  const calls = useCalls();
  const [open, setOpen] = useState(false);
  const [number, setNumber] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function start(name: string, to: string, callee?: string) {
    setBusy(true);
    setError('');
    try {
      const call = await createCall(to, callee);
      nav(`/call/${call.session_id}`, { state: { name, number: to } });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start the call');
      setBusy(false);
    }
  }

  const favourites = (contacts.data ?? []).filter((c) => c.favourite);
  const recent = (calls.data ?? []).filter((c) => c.kind !== 'task').slice(0, 8);
  const loading = contacts.isLoading || calls.isLoading;

  return (
    <AppShell title="Calls" action={<Button onClick={() => setOpen(true)}><Phone className="size-4" /> New call</Button>}>
      <div className="grid gap-8">
        {error && <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

        {loading && <Skeleton className="h-32 w-full rounded-2xl" />}

        {favourites.length > 0 && (
          <section className="grid gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">Favourites</h2>
            <RowList>
              {favourites.map((c) => (
                <div key={c.id} className="flex items-center gap-3 p-3.5">
                  <Person name={c.name} accent />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{c.name}</p>
                    <p className="truncate text-sm text-muted-foreground">{c.notes || c.phone_e164}</p>
                  </div>
                  <Button size="icon" className="rounded-full" aria-label={`Call ${c.name}`} disabled={busy} onClick={() => void start(c.name, c.phone_e164)}><Phone className="size-4" /></Button>
                </div>
              ))}
            </RowList>
          </section>
        )}

        <section className="grid gap-3">
          <h2 className="text-sm font-medium text-muted-foreground">Recent</h2>
          {!loading && recent.length === 0 ? (
            <EmptyState title="No calls yet" body="Start a call, or try a practice call below to see how captions and replies work." action={<Button onClick={() => setOpen(true)}>New call</Button>} />
          ) : (
            <RowList>
              {recent.map((c) => (
                <button key={c.id} type="button" onClick={() => nav(`/calls/${c.id}`)} className="flex w-full items-center gap-3 p-3.5 text-left transition-colors hover:bg-secondary/60">
                  <Person name={c.name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{c.name ?? maskNumber(c.other_number)}</p>
                    <p className="truncate text-sm text-muted-foreground">{when(c.created_at)}</p>
                  </div>
                  <Badge variant={c.status === 'ended' ? 'secondary' : 'outline'}>{STATUS_TEXT[c.status] ?? c.status}</Badge>
                  <ChevronRight className="size-4 text-muted-foreground" />
                </button>
              ))}
            </RowList>
          )}
        </section>

        <section className="grid gap-3">
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-medium text-muted-foreground">Practice calls</h2>
            <span className="text-xs text-muted-foreground">Scripted callers, no real phone call</span>
          </div>
          <RowList>
            {PRACTICE.map((p) => (
              <button key={p.number} type="button" disabled={busy} onClick={() => void start(p.name, p.number, p.callee)} className="flex w-full items-center gap-3 p-3.5 text-left transition-colors hover:bg-secondary/60 disabled:opacity-60">
                <Person name={p.name} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{p.name}</p>
                  <p className="truncate text-sm text-muted-foreground">{p.detail}</p>
                </div>
                <Badge variant="outline">Practice</Badge>
              </button>
            ))}
          </RowList>
        </section>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New call</DialogTitle>
            <DialogDescription>Enter the number you want to call. Awaaz tells them an assistant is helping.</DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={(e) => { e.preventDefault(); const n = number.length === 10 ? `+91${number}` : number; void start(n, n); }}>
            <div className="grid gap-2">
              <Label htmlFor="number">Phone number</Label>
              <Input id="number" inputMode="tel" autoFocus placeholder="98765 43210" className="h-12 text-lg" value={number} onChange={(e) => setNumber(e.target.value.replace(/[^\d+]/g, ''))} />
            </div>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
            <Button type="submit" size="lg" disabled={busy || number.length < 8}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : <Phone className="size-4" />} Call
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
