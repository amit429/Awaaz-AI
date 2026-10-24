import { ChevronLeft, Globe, Grid3x3, Keyboard, Languages, MessageSquare, Mic, PhoneOff, Repeat, Send, ShieldAlert, Sparkles, Square } from 'lucide-react';
import { useEffect, useReducer, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { LanguageSelect } from '@/components/LanguageSelect';
import { Person } from '@/components/Person';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import starterPhrases from '@/data/phrases.json';
import { useMe, usePhrases } from '@/hooks/useData';
import { api } from '@/lib/api';
import { applyEvent, initialState, splitByEntities, type FeedItem } from '@/lib/feed';
import { nativeName } from '@/i18n';
import { buzz, speak, stopSpeaking, useLiveVoice } from '@/lib/speech';
import { toast } from 'sonner';
import { RelayClient } from '@/lib/relay';
import { cn } from '@/lib/utils';

const starter = starterPhrases.filter((p) => !p.text.includes('{')); // address and number need profile data

/** Numbers, prices and times in a translated caption, picked out the same way as in the original. */
function withChips(text: string) {
  return text.split(/(₹\s?\d[\d,]*|\d{1,2}:\d{2}|\d[\d,]*(?:\s?(?:am|pm|AM|PM))?)/g).map((part, i) =>
    i % 2 === 1 ? <span key={i} className="rounded-md bg-accent px-1.5 font-semibold text-accent-foreground">{part}</span> : <span key={i}>{part}</span>,
  );
}

function Them({ item, readLang }: { item: Extract<FeedItem, { kind: 'them' }>; readLang: string }) {
  const { t } = useTranslation();
  const spoken = (item.lang ?? '').split('-')[0];
  const sameLanguage = spoken === readLang;
  const translation = sameLanguage ? undefined : item.translations?.[readLang];
  const original = splitByEntities(item.text, item.entities).map((p, i) =>
    p.entity ? <span key={i} className="rounded-md bg-accent px-1.5 font-semibold text-accent-foreground" aria-label={`${p.entity.type}: ${p.text}`}>{p.text}</span> : <span key={i}>{p.text}</span>,
  );
  return (
    <div className={cn('max-w-[92%] self-start rounded-3xl rounded-bl-md border border-white/10 bg-white/10 px-4 py-3 leading-snug', item.partial && 'opacity-60')}>
      {translation ? (
        <>
          <p className="text-xl">{withChips(translation)}</p>
          <p className="mt-1.5 text-sm text-muted-foreground">{t('call.original', { text: item.text })}</p>
        </>
      ) : (
        <p className="text-xl">{original}</p>
      )}
    </div>
  );
}

export function Call() {
  const { t } = useTranslation();
  const { sessionId = '' } = useParams();
  const location = useLocation();
  const nav = useNavigate();
  const who = (location.state as { name?: string; number?: string } | null) ?? {};
  const [state, dispatch] = useReducer(applyEvent, initialState);
  const mine = usePhrases();
  const me = useMe();
  const canHelp = Boolean(me.data?.profile.talk_modes?.includes('help'));
  const [mode, setMode] = useState<'type' | 'help'>('type');
  const [readLang, setReadLang] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const typeLang = me.data?.profile.type_lang ?? 'hi-Latn';
  const caption = readLang ?? me.data?.profile.read_lang ?? 'hi';
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
    feedEnd.current?.scrollIntoView({ block: 'end' });
  }, [state.feed]);

  useEffect(() => {
    // People without a regional keyboard: offer their script for text typed in English letters.
    setSuggestion(null);
    const v = text.trim();
    if (v.length < 3 || !/^[\x00-\x7F]+$/.test(v) || typeLang === 'en' || typeLang === 'hi-Latn') return;
    const id = setTimeout(() => {
      api.transliterate(v, typeLang).then((r) => r.text !== v && setSuggestion(r.text)).catch(() => undefined);
    }, 600);
    return () => clearTimeout(id);
  }, [text, typeLang]);

  function changeCaptionLanguage(code: string) {
    setReadLang(code);
    client.current?.send({ t: 'read.set', lang: code });
  }

  const talkModes = me.data?.profile.talk_modes ?? [];
  const hearModes = me.data?.profile.hear_modes ?? [];
  const [autoSend, setAutoSend] = useState(() => {
    try { return localStorage.getItem('awaaz-voice-auto') !== 'off'; } catch { return true; }
  });
  const [heard, setHeard] = useState('');
  const voice = useLiveVoice(typeLang === 'hi-Latn' ? 'hi' : typeLang, {
    // The other person is not left in silence while the user is mid-sentence.
    onSpeechStart: () => client.current?.send({ t: 'user.typing' }),
    onText: (spoken) => {
      setHeard(spoken);
      if (autoSend) {
        dispatch({ t: 'local.pending', id: `p${Date.now()}`, text: spoken });
        client.current?.send({ t: 'user.say', text: spoken, source: 'voice' });
      }
      else { setMode('type'); setText(spoken); }
    },
    onError: (code) => toast.error(t(code === 'denied' ? 'call.micDenied' : 'call.voiceFailed')),
  });

  function toggleVoice() {
    if (voice.active) return voice.stop();
    stopSpeaking();
    void voice.start();
  }
  function changeAutoSend(on: boolean) {
    setAutoSend(on);
    try { localStorage.setItem('awaaz-voice-auto', on ? 'on' : 'off'); } catch { /* ignore */ }
  }

  // Clear voice and vibration cues react to what the other person says.
  const voiceOn = useRef(false);
  voiceOn.current = voice.active;
  const lastCue = useRef<{ turn: number; final: boolean }>({ turn: 0, final: false });
  useEffect(() => {
    const last = [...state.feed].reverse().find((i): i is Extract<FeedItem, { kind: 'them' }> => i.kind === 'them');
    if (!last) return;
    const seen = lastCue.current;
    const isNew = last.turn !== seen.turn;
    if (hearModes.includes('vibe') && isNew) buzz(80);
    if (!last.partial && !(seen.turn === last.turn && seen.final)) {
      if (hearModes.includes('vibe')) buzz([120, 60, 120]);
      if (hearModes.includes('clear') && !voiceOn.current) speak(last.text, (last.lang ?? 'hi').split('-')[0] ?? 'hi');
      lastCue.current = { turn: last.turn, final: true };
    } else if (isNew) {
      lastCue.current = { turn: last.turn, final: false };
    }
  }, [state.feed]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => stopSpeaking, []);

  const preview = state.feed.find((i): i is Extract<FeedItem, { kind: 'preview' }> => i.kind === 'preview');
  const live = state.status === 'connected' || state.status === 'ringing';
  useEffect(() => {
    if (!live && voice.active) voice.stop();
  }, [live]); // eslint-disable-line react-hooks/exhaustive-deps

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = text.trim();
    if (!v && preview) return client.current?.send({ t: 'say.confirm', preview_id: preview.id });
    if (!v) return;
    if (mode === 'help') client.current?.send({ t: 'draft.request', words: v });
    else {
      dispatch({ t: 'local.pending', id: `p${Date.now()}`, text: v });
      client.current?.send({ t: 'user.say', text: v, source: 'typed' });
    }
    setText('');
    window.clearTimeout(prefetchTimer.current);
  }

  // While the user pauses mid-message, the server prepares it (script conversion, translation),
  // so pressing send is instant. Text already in a native script needs no preparation.
  const prefetchTimer = useRef<number>(0);
  function onType(v: string) {
    setText(v);
    window.clearTimeout(prefetchTimer.current);
    const draft = v.trim();
    if (mode === 'type' && draft.length >= 3 && /^[\x00-\x7F]+$/.test(draft)) {
      prefetchTimer.current = window.setTimeout(() => client.current?.send({ t: 'say.prefetch', text: draft }), 300);
    }
    if (Date.now() - lastTyping.current > 1500) {
      lastTyping.current = Date.now();
      client.current?.send({ t: 'user.typing' });
    }
  }

  const name = who.name ?? who.number ?? 'Call';
  const scamKey = state.scamReason && ['otp_request', 'pin_request', 'upi_pin', 'cvv_request', 'remote_app'].includes(state.scamReason) ? state.scamReason : 'other';
  const send = (e: Parameters<NonNullable<typeof client.current>['send']>[0]) => client.current?.send(e);

  return (
    <div
      className="dark mx-auto flex h-dvh max-w-2xl flex-col text-foreground"
      style={{ background: 'radial-gradient(120% 50% at 50% -10%, oklch(0.3 0.09 75 / 0.35), transparent 60%), oklch(0.15 0.03 270)' }}
    >
      <header className="pt-safe flex items-center gap-3 px-3 pb-3 pt-3">
        <Button variant="ghost" size="icon" aria-label={t('call.back')} onClick={() => nav('/')}><ChevronLeft className="size-5" /></Button>
        <Person name={name} className="size-10 bg-white/10" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-display text-lg font-semibold leading-tight">{name}</p>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <span className={cn('size-2 rounded-full', live && online ? 'bg-live shadow-[0_0_0_3px] shadow-live/25' : 'bg-muted-foreground')} />
            {online ? t(`call.${state.status}`) : t('call.reconnecting')}
          </p>
        </div>
        <div className="flex items-center gap-1.5" title={t('call.captionsIn')}>
          <Globe className="size-4 text-muted-foreground" aria-hidden="true" />
          <LanguageSelect value={caption} onChange={changeCaptionLanguage} className="h-9 w-[8.5rem] border-white/15 bg-white/10 text-sm" />
        </div>
      </header>

      {state.scam && !scamSeen && state.status !== 'ended' && (
        <Alert variant="destructive" role="alert" className="mx-3 mb-2 w-auto border-destructive/60 bg-destructive text-white">
          <ShieldAlert className="size-4 !text-white" />
          <AlertTitle className="line-clamp-none text-base">{t(`scam.${scamKey}.title`)}</AlertTitle>
          <AlertDescription className="!text-white/90">
            <p>{t(`scam.${scamKey}.body`)}</p>
            <div className="mt-3 flex gap-2">
              <Button size="sm" variant="secondary" className="text-destructive" onClick={() => send({ t: 'call.end' })}>{t('call.endCall')}</Button>
              <Button size="sm" variant="ghost" className="text-white hover:bg-white/15 hover:text-white" onClick={() => setScamSeen(true)}>{t('call.continue')}</Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto px-3 py-2" aria-live="polite">
        {state.feed.length === 0 && <p className="m-auto text-center text-muted-foreground">{state.status === 'connecting' ? t('call.connectingCall') : t('call.waiting')}</p>}
        {state.feed.map((item, i) => {
          switch (item.kind) {
            case 'them':
              return <Them key={`t${item.turn}`} item={item} readLang={caption} />;
            case 'you':
              return (
                <div key={`y${item.turn}`} className="max-w-[86%] self-end rounded-3xl rounded-br-md bg-accent px-4 py-2.5 text-lg font-medium text-accent-foreground">
                  {item.text}
                  {item.original && <small className="mt-0.5 block text-xs font-normal opacity-75">{t('call.youTyped', { text: item.original })}</small>}
                </div>
              );
            case 'pending':
              return (
                <div key={item.id} className="max-w-[86%] self-end rounded-3xl rounded-br-md bg-accent/60 px-4 py-2.5 text-lg font-medium text-accent-foreground">
                  {item.text}
                  <small className="mt-0.5 block text-xs font-normal opacity-75">{t('call.sending')}</small>
                </div>
              );
            case 'note':
              return <p key={item.id} className="max-w-[92%] self-center rounded-full bg-white/[0.07] px-3 py-1 text-center text-xs text-muted-foreground">{item.key ? t(item.key, { ...item.params, defaultValue: item.text ?? item.key }) : item.text}</p>;
            case 'draft':
              return (
                <div key={`d${item.id}`} className="self-stretch rounded-2xl border border-dashed border-accent/70 bg-white/[0.06] p-3.5">
                  <p className="flex items-center gap-1.5 text-sm font-medium text-accent"><Sparkles className="size-4" /> {t('call.draftTitle')}</p>
                  <p className="my-2 text-lg">{item.text}</p>
                  {item.risk && <p className="mb-2 text-sm text-accent">{t('call.draftUnclear')}</p>}
                  <div className="flex gap-2">
                    <Button size="sm" className="bg-accent text-accent-foreground hover:bg-accent/90" onClick={() => send({ t: 'user.say', text: item.text, source: 'draft' })}>{t('call.sayIt')}</Button>
                    <Button size="sm" variant="ghost" onClick={() => { setMode('type'); setText(item.text); }}>{t('common.edit')}</Button>
                  </div>
                </div>
              );
            case 'preview':
              return (
                <div key={`p${i}`} className="self-stretch rounded-2xl border border-dashed border-accent/70 bg-white/[0.06] p-3.5">
                  <p className="flex items-center gap-1.5 text-sm font-medium text-accent"><Languages className="size-4" /> {t('call.previewTitle')}</p>
                  <p className="my-2 text-lg">{item.text}</p>
                  {item.original && <p className="mb-2 text-sm text-muted-foreground">{t('call.youTyped', { text: item.original })}</p>}
                  <div className="flex gap-2">
                    <Button size="sm" className="bg-accent text-accent-foreground hover:bg-accent/90" onClick={() => send({ t: 'say.confirm', preview_id: item.id })}>{t('call.sayIt')}</Button>
                    <Button size="sm" variant="ghost" onClick={() => setText(item.original ?? '')}>{t('common.edit')}</Button>
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
            {([['type', t('call.type'), Keyboard], ['help', t('call.helpMeSay'), Sparkles]] as const).map(([k, label, Icon]) => (
              <button key={k} type="button" aria-pressed={mode === k} onClick={() => setMode(k)} className={cn('flex flex-1 items-center justify-center gap-1.5 rounded-full py-1.5 text-sm font-medium transition-colors', mode === k ? 'bg-foreground text-background' : 'text-muted-foreground')}>
                <Icon className="size-4" /> {label}
              </button>
            ))}
          </div>
        )}
        {live && suggestion && (
          <button type="button" onClick={() => { setText(suggestion); setSuggestion(null); }} className="mb-2 flex w-full items-center gap-2 rounded-2xl bg-accent/15 px-4 py-2 text-left text-base transition-colors hover:bg-accent/25">
            <span className="truncate">{t('call.inScript', { lang: nativeName(typeLang), text: suggestion })}</span>
            <span className="ml-auto shrink-0 text-sm font-medium text-accent">{t('call.useThis')}</span>
          </button>
        )}
        {live && voice.active && (
          <div className="mb-2 flex items-center gap-3 rounded-2xl bg-white/[0.07] px-4 py-2 text-sm" aria-live="polite">
            <span className="size-2.5 shrink-0 animate-pulse rounded-full bg-destructive" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate">{heard ? t('call.voiceHeard', { text: heard }) : t('call.voiceListening')}</span>
            <label className="flex shrink-0 items-center gap-2 text-muted-foreground">
              {t('call.autoSend')}
              <Switch checked={autoSend} onCheckedChange={changeAutoSend} aria-label={t('call.autoSend')} />
            </label>
          </div>
        )}
        {live ? (
          <form className="flex items-center gap-2" onSubmit={submit}>
            <Input value={text} onChange={(e) => onType(e.target.value)} autoFocus aria-label={mode === 'help' ? t('call.helpPlaceholder') : t('call.typePlaceholder')} placeholder={mode === 'help' ? t('call.helpPlaceholder') : t('call.typePlaceholder')} className="h-12 rounded-full border-0 bg-white/10 px-5 text-base" />
            {talkModes.includes('voice') && (
              <Button type="button" size="icon" variant={voice.active ? 'destructive' : 'secondary'} onClick={toggleVoice} aria-pressed={voice.active} aria-label={voice.active ? t('call.micStop') : t('call.micStart')} className={cn('size-12 shrink-0 rounded-full', voice.active && 'animate-pulse')}>
                {voice.active ? <Square className="size-5" /> : <Mic className="size-5" />}
              </Button>
            )}
            <Button type="submit" size="icon" aria-label={mode === 'help' ? 'Draft' : 'Speak'} className="size-12 shrink-0 rounded-full bg-accent text-accent-foreground hover:bg-accent/90">{mode === 'help' ? <Sparkles className="size-5" /> : <Send className="size-5" />}</Button>
          </form>
        ) : (
          <Button variant="secondary" size="lg" className="w-full" onClick={() => nav('/')}>{t('call.back')}</Button>
        )}
        <div className="mt-1.5 grid grid-cols-4 gap-1">
          {[
            { icon: MessageSquare, label: t('call.phrases'), run: () => setSheet('phrases') },
            { icon: Grid3x3, label: t('call.keypad'), run: () => setSheet('keypad') },
            { icon: Repeat, label: t('call.askAgain'), run: () => send({ t: 'user.ask_repeat' }) },
          ].map(({ icon: Icon, label, run }) => (
            <Button key={label} variant="ghost" disabled={!live} onClick={run} className="h-auto flex-col gap-1 py-2 text-xs font-normal text-muted-foreground"><Icon className="size-5" />{label}</Button>
          ))}
          <Button variant="ghost" disabled={!live} onClick={() => setConfirmEnd(true)} className="h-auto flex-col gap-1 py-2 text-xs font-normal text-destructive hover:text-destructive"><PhoneOff className="size-5" />{t('call.end')}</Button>
        </div>
      </div>

      <Sheet open={sheet === 'phrases'} onOpenChange={(o) => !o && setSheet(null)}>
        <SheetContent side="bottom" className="dark mx-auto max-h-[75dvh] max-w-2xl overflow-y-auto rounded-t-3xl">
          <SheetHeader><SheetTitle>{t('call.phrases')}</SheetTitle><SheetDescription>{t('call.phrasesHint')}</SheetDescription></SheetHeader>
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
          <SheetHeader><SheetTitle>{t('call.keypad')}</SheetTitle><SheetDescription>{t('call.keypadHint')}</SheetDescription></SheetHeader>
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
            <AlertDialogTitle>{t('call.endTitle')}</AlertDialogTitle>
            <AlertDialogDescription>{t('call.endBody', { name })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('call.stay')}</AlertDialogCancel>
            <AlertDialogAction className="bg-destructive text-white hover:bg-destructive/90" onClick={() => send({ t: 'call.end' })}>{t('call.endCall')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
