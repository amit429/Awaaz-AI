import { ChevronLeft, Grid3x3, Keyboard, MessageSquare, PhoneOff, Repeat, Send, ShieldAlert, Sparkles, Languages } from 'lucide-react';
import { useEffect, useReducer, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Person } from '@/components/Person';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import starterPhrases from '@/data/phrases.json';
import { useMe, usePhrases } from '@/hooks/useData';
import { applyEvent, initialState, SCAM_COPY, splitByEntities, type FeedItem } from '@/lib/feed';
import { RelayClient } from '@/lib/relay';
import { cn } from '@/lib/utils';

const STATUS_LABEL = { connecting: 'Connecting…', ringing: 'Calling…', connected: 'Connected', ended: 'Call ended', failed: 'Call failed' } as const;
const starter = starterPhrases.filter((p) => !p.text.includes('{')); // address and number need profile data

function Them({ item }: { item: Extract<FeedItem, { kind: 'them' }> }) {
  return (
    <div className={cn('max-w-[92%] self-start rounded-3xl rounded-bl-md border border-white/10 bg-white/10 px-4 py-3 text-xl leading-snug', item.partial && 'opacity-60')}>
      {splitByEntities(item.text, item.entities).map((p, i) =>
        p.entity ? <span key={i} className="rounded-md bg-accent px-1.5 font-semibold text-accent-foreground" aria-label={`${p.entity.type}: ${p.text}`}>{p.text}</span> : <span key={i}>{p.text}</span>,
      )}
      {item.translated && <span className="mt-1 block text-sm text-muted-foreground">{item.translated}</span>}
    </div>
  );
}

export function Call() {
  const { sessionId = '' } = useParams();
  const location = useLocation();
  const nav = useNavigate();
  const who = (location.state as { name?: string; number?: string } | null) ?? {};
  const [state, dispatch] = useReducer(applyEvent, initialState);
  const mine = usePhrases();
  const me = useMe();
  const canHelp = Boolean(me.data?.profile.talk_modes?.includes('help'));
  const [mode, setMode] = useState<'type' | 'help'>('type');
  const usablePhrases = mine.data && mine.data.length > 0 ? mine.data : starter;
  const [online, setOnline] = useState(false);
  const [text, setText] = useState('');
  const [sheet, setSheet] = useState<'phrases' | 'keypad' | null>(null);
  const [scamSeen, setScamSeen] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const client = useRef<RelayClient | null>(null);
  const feedEnd = useRef<HTMLDivElement>(null);
  const lastTyping = useRef(0);

  useEffect(() => {
    const c = new RelayClient(sessionId, dispatch, setOnline);
    client.current = c;
    void c.connect();
    return () => c.close();
  }, [sessionId]);

  useEffect(() => {
    feedEnd.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
  }, [state.feed]);

  const preview = state.feed.find((i): i is Extract<FeedItem, { kind: 'preview' }> => i.kind === 'preview');
  const live = state.status === 'connected' || state.status === 'ringing';

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = text.trim();
    if (!v && preview) return client.current?.send({ t: 'say.confirm', preview_id: preview.id });
    if (!v) return;
    if (mode === 'help') client.current?.send({ t: 'draft.request', words: v });
    else client.current?.send({ t: 'user.say', text: v, source: 'typed' });
    setText('');
  }

  function onType(v: string) {
    setText(v);
    if (Date.now() - lastTyping.current > 1500) {
      lastTyping.current = Date.now();
      client.current?.send({ t: 'user.typing' });
    }
  }

  const name = who.name ?? who.number ?? 'Call';
  const scam = SCAM_COPY[state.scamReason ?? 'other'] ?? SCAM_COPY.other!;
  const send = (e: Parameters<NonNullable<typeof client.current>['send']>[0]) => client.current?.send(e);

  return (
    <div
      className="dark mx-auto flex h-dvh max-w-2xl flex-col text-foreground"
      style={{ background: 'radial-gradient(120% 50% at 50% -10%, oklch(0.3 0.09 75 / 0.35), transparent 60%), oklch(0.15 0.03 270)' }}
    >
      <header className="pt-safe flex items-center gap-3 px-3 pb-3 pt-3">
        <Button variant="ghost" size="icon" aria-label="Back to calls" onClick={() => nav('/')}><ChevronLeft className="size-5" /></Button>
        <Person name={name} className="size-10 bg-white/10" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-display text-lg font-semibold leading-tight">{name}</p>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <span className={cn('size-2 rounded-full', live && online ? 'bg-live shadow-[0_0_0_3px] shadow-live/25' : 'bg-muted-foreground')} />
            {online ? STATUS_LABEL[state.status] : 'Reconnecting…'}
          </p>
        </div>
      </header>

      {state.scam && !scamSeen && state.status !== 'ended' && (
        <Alert variant="destructive" role="alert" className="mx-3 mb-2 border-destructive/60 bg-destructive text-white">
          <ShieldAlert className="size-4 !text-white" />
          <AlertTitle className="text-base">{scam.title}</AlertTitle>
          <AlertDescription className="text-white/90">
            <p>{scam.body}</p>
            <div className="mt-3 flex gap-2">
              <Button size="sm" variant="secondary" className="text-destructive" onClick={() => send({ t: 'call.end' })}>End call</Button>
              <Button size="sm" variant="ghost" className="text-white hover:bg-white/15 hover:text-white" onClick={() => setScamSeen(true)}>Continue</Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto px-3 py-2" aria-live="polite">
        {state.feed.length === 0 && <p className="m-auto text-center text-muted-foreground">{state.status === 'connecting' ? 'Connecting the call…' : 'Waiting for them to speak.'}</p>}
        {state.feed.map((item, i) => {
          switch (item.kind) {
            case 'them':
              return <Them key={`t${item.turn}`} item={item} />;
            case 'you':
              return (
                <div key={`y${item.turn}`} className="max-w-[86%] self-end rounded-3xl rounded-br-md bg-accent px-4 py-2.5 text-lg font-medium text-accent-foreground">
                  {item.text}
                  {item.original && <small className="mt-0.5 block text-xs font-normal opacity-75">You typed: {item.original}</small>}
                </div>
              );
            case 'note':
              return <p key={item.id} className="max-w-[92%] self-center rounded-full bg-white/[0.07] px-3 py-1 text-center text-xs text-muted-foreground">{item.text}</p>;
            case 'draft':
              return (
                <div key={`d${item.id}`} className="self-stretch rounded-2xl border border-dashed border-accent/70 bg-white/[0.06] p-3.5">
                  <p className="flex items-center gap-1.5 text-sm font-medium text-accent"><Sparkles className="size-4" /> Drafted for you. Check it before it’s spoken</p>
                  <p className="my-2 text-lg">{item.text}</p>
                  {item.risk && <p className="mb-2 text-sm text-accent">Your words were a little unclear. Check this says what you mean.</p>}
                  <div className="flex gap-2">
                    <Button size="sm" className="bg-accent text-accent-foreground hover:bg-accent/90" onClick={() => send({ t: 'user.say', text: item.text, source: 'draft' })}>Say it</Button>
                    <Button size="sm" variant="ghost" onClick={() => { setMode('type'); setText(item.text); }}>Edit</Button>
                  </div>
                </div>
              );
            case 'preview':
              return (
                <div key={`p${i}`} className="self-stretch rounded-2xl border border-dashed border-accent/70 bg-white/[0.06] p-3.5">
                  <p className="flex items-center gap-1.5 text-sm font-medium text-accent"><Languages className="size-4" /> Check before it’s spoken</p>
                  <p className="my-2 text-lg">{item.text}</p>
                  {item.original && <p className="mb-2 text-sm text-muted-foreground">You typed: {item.original}</p>}
                  <div className="flex gap-2">
                    <Button size="sm" className="bg-accent text-accent-foreground hover:bg-accent/90" onClick={() => send({ t: 'say.confirm', preview_id: item.id })}>Say it</Button>
                    <Button size="sm" variant="ghost" onClick={() => setText(item.original ?? '')}>Edit</Button>
                  </div>
                </div>
              );
          }
        })}
        <div ref={feedEnd} />
      </div>

      {state.suggestions.length > 0 && (
        <div className="flex gap-2 overflow-x-auto px-3 pb-2" aria-label="Suggested replies">
          {state.suggestions.map((s) => (
            <Button key={s} variant="outline" className="shrink-0 rounded-full border-white/20 bg-white/[0.06] text-base" onClick={() => send({ t: 'user.say', text: s, source: 'reply' })}>{s}</Button>
          ))}
        </div>
      )}

      <div className="pb-safe mx-2 mb-2 rounded-[1.75rem] border border-white/10 bg-white/[0.06] p-2 backdrop-blur-xl">
        {live && canHelp && (
          <div className="mb-2 flex gap-1 rounded-full bg-black/25 p-1" role="group" aria-label="How you talk">
            {([['type', 'Type', Keyboard], ['help', 'Help me say', Sparkles]] as const).map(([k, label, Icon]) => (
              <button key={k} type="button" aria-pressed={mode === k} onClick={() => setMode(k)} className={cn('flex flex-1 items-center justify-center gap-1.5 rounded-full py-1.5 text-sm font-medium transition-colors', mode === k ? 'bg-foreground text-background' : 'text-muted-foreground')}>
                <Icon className="size-4" /> {label}
              </button>
            ))}
          </div>
        )}
        {live ? (
          <form className="flex items-center gap-2" onSubmit={submit}>
            <Input value={text} onChange={(e) => onType(e.target.value)} autoFocus aria-label={mode === 'help' ? 'A few words' : 'Type a message'} placeholder={mode === 'help' ? 'A few words, I’ll make a sentence' : 'Type, they hear it'} className="h-12 rounded-full border-0 bg-white/10 px-5 text-base" />
            <Button type="submit" size="icon" aria-label={mode === 'help' ? 'Draft' : 'Speak'} className="size-12 shrink-0 rounded-full bg-accent text-accent-foreground hover:bg-accent/90">{mode === 'help' ? <Sparkles className="size-5" /> : <Send className="size-5" />}</Button>
          </form>
        ) : (
          <Button variant="secondary" size="lg" className="w-full" onClick={() => nav('/')}>Back to calls</Button>
        )}
        <div className="mt-1.5 grid grid-cols-4 gap-1">
          {[
            { icon: MessageSquare, label: 'Phrases', run: () => setSheet('phrases') },
            { icon: Grid3x3, label: 'Keypad', run: () => setSheet('keypad') },
            { icon: Repeat, label: 'Ask again', run: () => send({ t: 'user.ask_repeat' }) },
          ].map(({ icon: Icon, label, run }) => (
            <Button key={label} variant="ghost" disabled={!live} onClick={run} className="h-auto flex-col gap-1 py-2 text-xs font-normal text-muted-foreground"><Icon className="size-5" />{label}</Button>
          ))}
          <Button variant="ghost" disabled={!live} onClick={() => setConfirmEnd(true)} className="h-auto flex-col gap-1 py-2 text-xs font-normal text-destructive hover:text-destructive"><PhoneOff className="size-5" />End</Button>
        </div>
      </div>

      <Sheet open={sheet === 'phrases'} onOpenChange={(o) => !o && setSheet(null)}>
        <SheetContent side="bottom" className="dark mx-auto max-h-[75dvh] max-w-2xl overflow-y-auto rounded-t-3xl">
          <SheetHeader><SheetTitle>Phrases</SheetTitle><SheetDescription>Tap one to say it.</SheetDescription></SheetHeader>
          <div className="grid gap-2 px-4 pb-6">
            {usablePhrases.map((p) => (
              <button key={p.label + p.text} type="button" onClick={() => { send({ t: 'user.say', text: p.text, source: 'phrase' }); setSheet(null); }} className="rounded-2xl bg-secondary px-4 py-3 text-left transition-colors hover:bg-secondary/70">
                <span className="block font-medium">{p.label}</span>
                <span className="block text-sm text-muted-foreground">{p.text}</span>
              </button>
            ))}
          </div>
        </SheetContent>
      </Sheet>

      <Sheet open={sheet === 'keypad'} onOpenChange={(o) => !o && setSheet(null)}>
        <SheetContent side="bottom" className="dark mx-auto max-w-2xl rounded-t-3xl">
          <SheetHeader><SheetTitle>Keypad</SheetTitle><SheetDescription>Press numbers for phone menus, like “press 1 for…”.</SheetDescription></SheetHeader>
          <div className="mx-auto grid max-w-xs grid-cols-3 gap-3 px-4 pb-8">
            {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((d) => (
              <Button key={d} variant="secondary" className="size-[4.5rem] justify-self-center rounded-full text-2xl" onClick={() => send({ t: 'user.dtmf', digits: d })}>{d}</Button>
            ))}
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog open={confirmEnd} onOpenChange={setConfirmEnd}>
        <AlertDialogContent className="dark">
          <AlertDialogHeader>
            <AlertDialogTitle>End this call?</AlertDialogTitle>
            <AlertDialogDescription>{name} will be disconnected.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Stay on the call</AlertDialogCancel>
            <AlertDialogAction className="bg-destructive text-white hover:bg-destructive/90" onClick={() => send({ t: 'call.end' })}>End call</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
