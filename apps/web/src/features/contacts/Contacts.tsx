import { Pencil, Phone, Plus, Star, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { AppShell } from '@/components/AppShell';
import { EmptyState, Person, RowList } from '@/components/Person';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { useContacts, useDeleteContact, useSaveContact } from '@/hooks/useData';
import { createCall } from '@/lib/api';
import type { Contact } from '@/lib/types';

type Draft = Omit<Contact, 'id'> & { id?: string };
const blank: Draft = { name: '', phone_e164: '', call_lang: 'hi', notes: '', favourite: false };

const normalise = (raw: string) => {
  const d = raw.replace(/[^\d+]/g, '');
  if (d.startsWith('+')) return d;
  return d.length === 10 ? `+91${d}` : d.startsWith('91') && d.length === 12 ? `+${d}` : d;
};

export function Contacts() {
  const nav = useNavigate();
  const contacts = useContacts();
  const save = useSaveContact();
  const del = useDeleteContact();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [toDelete, setToDelete] = useState<Contact | null>(null);

  async function call(c: Contact) {
    try {
      const made = await createCall(c.phone_e164);
      nav(`/call/${made.session_id}`, { state: { name: c.name, number: c.phone_e164 } });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not start the call');
    }
  }

  const valid = draft && draft.name.trim() && /^\+[1-9]\d{7,14}$/.test(normalise(draft.phone_e164));

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft || !valid) return;
    const { id, ...rest } = draft;
    save.mutate(
      { id, contact: { ...rest, phone_e164: normalise(rest.phone_e164), notes: rest.notes || null } },
      { onSuccess: () => { toast.success(id ? 'Contact saved' : 'Contact added'); setDraft(null); }, onError: () => toast.error('Could not save. Check the number.') },
    );
  }

  return (
    <AppShell title="Contacts" action={<Button onClick={() => setDraft({ ...blank })}><Plus className="size-4" /> Add contact</Button>}>
      {contacts.isLoading && <Skeleton className="h-40 w-full rounded-2xl" />}
      {contacts.data?.length === 0 && (
        <EmptyState title="No contacts yet" body="Save the people and places you call often. Add a note, for example “my BP medicine is Telma 40”, and Awaaz can use it in replies." action={<Button onClick={() => setDraft({ ...blank })}>Add your first contact</Button>} />
      )}
      {(contacts.data?.length ?? 0) > 0 && (
        <RowList>
          {(contacts.data ?? []).map((c) => (
            <div key={c.id} className="flex items-center gap-3 p-3.5">
              <Person name={c.name} accent={c.favourite} />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-1.5 truncate font-medium">{c.name}{c.favourite && <Star className="size-3.5 fill-accent text-accent" aria-label="Favourite" />}</p>
                <p className="truncate text-sm text-muted-foreground">{c.notes || c.phone_e164}</p>
              </div>
              <Button variant="ghost" size="icon" aria-label={`Edit ${c.name}`} onClick={() => setDraft({ ...c })}><Pencil className="size-4" /></Button>
              <Button variant="ghost" size="icon" aria-label={`Delete ${c.name}`} onClick={() => setToDelete(c)}><Trash2 className="size-4" /></Button>
              <Button size="icon" className="rounded-full" aria-label={`Call ${c.name}`} onClick={() => void call(c)}><Phone className="size-4" /></Button>
            </div>
          ))}
        </RowList>
      )}

      <Sheet open={draft !== null} onOpenChange={(o) => !o && setDraft(null)}>
        <SheetContent side="bottom" className="mx-auto max-w-lg rounded-t-3xl">
          {draft && (
            <form onSubmit={submit} className="grid gap-5 px-4 pb-4">
              <SheetHeader className="px-0">
                <SheetTitle>{draft.id ? 'Edit contact' : 'New contact'}</SheetTitle>
                <SheetDescription>Notes can be used by Awaaz when it suggests replies.</SheetDescription>
              </SheetHeader>
              <div className="grid gap-2"><Label htmlFor="c-name">Name</Label><Input id="c-name" autoFocus className="h-11" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></div>
              <div className="grid gap-2"><Label htmlFor="c-phone">Phone number</Label><Input id="c-phone" inputMode="tel" className="h-11" value={draft.phone_e164} onChange={(e) => setDraft({ ...draft, phone_e164: e.target.value })} /></div>
              <div className="grid gap-2"><Label htmlFor="c-notes">Notes</Label><Textarea id="c-notes" placeholder="For example: my BP medicine is Telma 40" value={draft.notes ?? ''} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} /></div>
              <div className="flex items-center justify-between rounded-xl border p-3.5"><Label htmlFor="c-fav" className="font-normal">Show in favourites</Label><Switch id="c-fav" checked={draft.favourite} onCheckedChange={(v) => setDraft({ ...draft, favourite: v })} /></div>
              <SheetFooter className="px-0"><Button type="submit" size="lg" disabled={!valid || save.isPending}>Save contact</Button></SheetFooter>
            </form>
          )}
        </SheetContent>
      </Sheet>

      <AlertDialog open={toDelete !== null} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {toDelete?.name}?</AlertDialogTitle>
            <AlertDialogDescription>This removes the contact and its notes. Past calls stay in your history.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep</AlertDialogCancel>
            <AlertDialogAction className="bg-destructive text-white hover:bg-destructive/90" onClick={() => toDelete && del.mutate(toDelete.id, { onSuccess: () => toast.success('Contact deleted') })}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
