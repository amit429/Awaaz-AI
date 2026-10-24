import { ChevronLeft, Plus, X } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { AppShell } from '@/components/AppShell';
import { EmptyState, RowList } from '@/components/Person';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAddPhrase, useDeletePhrase, usePhrases } from '@/hooks/useData';

export function Phrases() {
  const phrases = usePhrases();
  const add = useAddPhrase();
  const del = useDeletePhrase();
  const [label, setLabel] = useState('');
  const [text, setText] = useState('');

  return (
    <AppShell title="My phrases" action={<Button variant="ghost" asChild><Link to="/me"><ChevronLeft className="size-4" /> Me</Link></Button>}>
      <div className="grid gap-8">
        <form
          className="grid gap-4 rounded-2xl border bg-card p-4"
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate({ label: label.trim(), text: text.trim() }, { onSuccess: () => { setLabel(''); setText(''); toast.success('Phrase added'); }, onError: () => toast.error('Could not save the phrase.') });
          }}
        >
          <div className="grid gap-2"><Label htmlFor="p-label">Short name</Label><Input id="p-label" className="h-11" placeholder="My address" value={label} onChange={(e) => setLabel(e.target.value)} /></div>
          <div className="grid gap-2"><Label htmlFor="p-text">What is said on the call</Label><Input id="p-text" className="h-11" placeholder="Mera pata hai: Flat 12, Shanti Nagar, Nagpur" value={text} onChange={(e) => setText(e.target.value)} /></div>
          <Button type="submit" disabled={!label.trim() || !text.trim() || add.isPending}><Plus className="size-4" /> Add phrase</Button>
        </form>

        {(phrases.data ?? []).length === 0 ? (
          <EmptyState title="No phrases yet" body="The call screen shows a starter set until you add your own." />
        ) : (
          <RowList>
            {(phrases.data ?? []).map((p) => (
              <div key={p.id} className="flex items-center gap-3 p-3.5">
                <div className="min-w-0 flex-1"><p className="truncate font-medium">{p.label}</p><p className="truncate text-sm text-muted-foreground">{p.text}</p></div>
                <Button variant="ghost" size="icon" aria-label={`Delete ${p.label}`} onClick={() => del.mutate(p.id)}><X className="size-4" /></Button>
              </div>
            ))}
          </RowList>
        )}
      </div>
    </AppShell>
  );
}
