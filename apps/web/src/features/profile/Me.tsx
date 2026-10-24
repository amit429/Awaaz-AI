import { useQueryClient } from '@tanstack/react-query';
import { Check, ChevronRight, Loader2, LogOut, MessageSquare } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useMe, useSaveMe } from '@/hooks/useData';
import { useSession } from '@/hooks/useSession';
import { setDevLogin } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import type { Profile } from '@/lib/types';
import { ProfileForm } from './ProfileForm';

export function Me() {
  const me = useMe();
  const save = useSaveMe();
  const session = useSession();
  const qc = useQueryClient();
  const nav = useNavigate();
  const [draft, setDraft] = useState<Profile | null>(null);

  useEffect(() => {
    if (me.data && !draft) setDraft(me.data.profile);
  }, [me.data, draft]);

  const dirty = Boolean(draft && me.data && JSON.stringify(draft) !== JSON.stringify(me.data.profile));

  async function signOut() {
    await supabase.auth.signOut();
    setDevLogin(false);
    qc.clear();
    nav('/login', { replace: true });
  }

  return (
    <AppShell title="Me">
      {!me.data || !draft ? (
        <Skeleton className="h-64 w-full rounded-2xl" />
      ) : (
        <div className="grid gap-8">
          <div className="grid gap-2">
            <Label htmlFor="me-name">Your name</Label>
            <Input id="me-name" className="h-11" value={draft.display_name} onChange={(e) => setDraft({ ...draft, display_name: e.target.value })} />
            <p className="text-sm text-muted-foreground">Said to the other person at the start of every call.</p>
          </div>

          <ProfileForm value={draft} presets={me.data.presets} onChange={setDraft} />

          <Link to="/me/phrases" className="flex items-center gap-3 rounded-2xl border bg-card p-3.5 transition-colors hover:bg-secondary/60">
            <span className="grid size-10 place-items-center rounded-lg bg-secondary"><MessageSquare className="size-[18px]" /></span>
            <span className="flex-1"><span className="block font-medium">My phrases</span><span className="block text-sm text-muted-foreground">Quick things to say on calls</span></span>
            <ChevronRight className="size-4 text-muted-foreground" />
          </Link>

          <div className="pb-safe sticky bottom-20 z-20 md:bottom-4">
            <Button size="lg" className="w-full shadow-lg" disabled={!dirty || save.isPending || !draft.display_name.trim()} onClick={() => save.mutate(draft, { onSuccess: () => toast.success('Saved'), onError: () => toast.error('Could not save. Please try again.') })}>
              {save.isPending ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />} {dirty ? 'Save changes' : 'Saved'}
            </Button>
          </div>

          <div className="flex items-center justify-between gap-4 border-t pt-6">
            <p className="min-w-0 truncate text-sm text-muted-foreground">Signed in as {session.email ?? 'you'}</p>
            <Button variant="outline" onClick={() => void signOut()}><LogOut className="size-4" /> Sign out</Button>
          </div>
        </div>
      )}
    </AppShell>
  );
}
