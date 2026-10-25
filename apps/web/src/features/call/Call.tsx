import { ArrowLeft, ChevronDown, Grid3x3, Languages, MessageSquareText, Mic, PhoneOff, Plus, Repeat, SendHorizontal, ShieldAlert, Sparkles, Square, X } from 'lucide-react';
import { useEffect, useLayoutEffect, useReducer, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { LanguageSelect } from '@/components/LanguageSelect';
import { Person } from '@/components/Person';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Switch } from '@/components/ui/switch';
import starterPhrases from '@/data/phrases.json';
import { useMe, usePhrases } from '@/hooks/useData';
import { useVisualViewport } from '@/hooks/useVisualViewport';
import { nativeName } from '@/i18n';
import { api } from '@/lib/api';
import { applyEvent, initialState, type FeedItem } from '@/lib/feed';
import { RelayClient } from '@/lib/relay';
import { buzz, speak, stopSpeaking, useLiveVoice } from '@/lib/speech';
import { cn } from '@/lib/utils';
import { ActionCard, BubbleActions, DayDivider, Dots, MyBubble, Note, TheirBubble } from './ChatParts';

const starter = starterPhrases.filter((p) => !p.text.includes('{')); // address and number need profile data
const NEAR_BOTTOM = 96; // px: closer than this to the end counts as "at the latest message"

/** Which side of the chat an item sits on; consecutive items on the same side form a run. */
const sideOf = (i: FeedItem): 'in' | 'out' | 'mid' => (i.kind === 'them' || i.kind === 'draft' || i.kind === 'preview' ? 'in' : i.kind === 'you' || i.kind === 'pending' ? 'out' : 'mid');
const keyOf = (i: FeedItem): string => (i.kind === 'them' ? `t${i.turn}` : i.kind === 'you' ? `y${i.turn}` : `${i.kind}-${i.id}`);

const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

export function Call() {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'hi-Latn' ? 'en-IN' : `${i18n.language}-IN`;
  const { sessionId = '' } = useParams();
  const location = useLocation();
  const nav = useNavigate();
  const who = (location.state as { name?: string; number?: string } | null) ?? {};
  const [state, dispatch] = useReducer(applyEvent, initialState);
  const mine = usePhrases();
  const me = useMe();
  const viewport = useVisualViewport();
  const canHelp = Boolean(me.data?.profile.talk_modes?.includes('help'));
  const [mode, setMode] = useState<'type' | 'help'>('type');
  const [readLang, setReadLang] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const typeLang = me.data?.profile.type_lang ?? 'hi-Latn';
  const caption = readLang ?? me.data?.profile.read_lang ?? 'hi';
  const usablePhrases = mine.data && mine.data.length > 0 ? mine.data : starter;
  const [online, setOnline] = useState(false);
  const [text, setText] = useState('');
  const [sheet, setSheet] = useState<'phrases' | 'more' | 'captions' | 'keypad' | null>(null);
  const [scamSeen, setScamSeen] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [activeBubble, setActiveBubble] = useState<string | null>(null);
  const client = useRef<RelayClient | null>(null);
  const list = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const atBottom = useRef(true);
  const [showJump, setShowJump] = useState(false);
  const [unread, setUnread] = useState(0);
  const lastTyping = useRef(0);
  const prefetchTimer = useRef<number>(0);

  useEffect(() => {
    const c = new RelayClient(sessionId, dispatch, setOnline);
    client.current = c;
    void c.connect();
    return () => c.close();
  }, [sessionId]);

  // The call screen owns the whole window: no page bounce or scroll behind it.
  useEffect(() => {
    const html = document.documentElement;
    const before = { overflow: html.style.overflow, background: html.style.backgroundColor };
    html.style.overflow = 'hidden';
    html.style.backgroundColor = '#0b141a'; // wide screens: the area beside the chat matches it
    return () => {
      html.style.overflow = before.overflow;
      html.style.backgroundColor = before.background;
    };
  }, []);

  // ---------- scrolling, like a chat app ----------
  const scrollToEnd = () => {
    const el = list.current;
    if (el) el.scrollTop = el.scrollHeight;
    atBottom.current = true;
    setShowJump(false);
    setUnread(0);
  };
  function onScroll() {
    const el = list.current;
    if (!el) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM;
    atBottom.current = near;
    setShowJump(!near);
    if (near) setUnread(0);
    setActiveBubble(null);
  }
  const lastKey = useRef('');
  useLayoutEffect(() => {
    const last = state.feed[state.feed.length - 1];
    if (!last) return;
    const key = keyOf(last);
    const isNew = key !== lastKey.current;
    lastKey.current = key;
    // Follow the conversation when already at the end, or when the user just sent something.
    if (atBottom.current || (isNew && last.kind === 'pending')) scrollToEnd();
    else if (isNew && sideOf(last) === 'in') setUnread((n) => n + 1);
  }, [state.feed]);
  // Keyboard opening or closing changes the visible height: keep the latest message in view.
  useLayoutEffect(() => {
    if (atBottom.current) scrollToEnd();
  }, [viewport.height]);

  // ---------- typing helpers ----------
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

  // The box grows with the message, up to about five lines, like WhatsApp.
  useLayoutEffect(() => {
    const el = input.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
  }, [text]);

  function changeCaptionLanguage(code: string) {
    setReadLang(code);
    client.current?.send({ t: 'read.set', lang: code });
  }

  const talkModes = me.data?.profile.talk_modes ?? [];
  const hearModes = me.data?.profile.hear_modes ?? [];
  // The mic is for anyone who can speak: shown unless they said they can't (so it can be found).
  const canUseVoice = talkModes.includes('voice') || me.data?.profile.preset !== 'mute';
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
      } else {
        setMode('type');
        setText(spoken);
      }
    },
    onError: (code) => toast.error(t(code === 'denied' ? 'call.micDenied' : 'call.voiceFailed')),
  });

  function toggleVoice() {
    if (voice.active) return voice.stop();
    stopSpeaking();
    setHeard('');
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

  // Call timer, shown in the header like a phone call.
  const [connectedAt, setConnectedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (state.status === 'connected' && connectedAt === null) setConnectedAt(Date.now());
  }, [state.status, connectedAt]);
  useEffect(() => {
    if (!live) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [live]);

  function sendText() {
    const v = text.trim();
    if (!v && preview) return client.current?.send({ t: 'say.confirm', preview_id: preview.id });
    if (!v) return;
    if (mode === 'help') client.current?.send({ t: 'draft.request', words: v });
    else {
      dispatch({ t: 'local.pending', id: `p${Date.now()}`, text: v });
      client.current?.send({ t: 'user.say', text: v, source: 'typed' });
    }
    setText('');
    setMode('type');
    window.clearTimeout(prefetchTimer.current);
    scrollToEnd();
  }

  // While the user pauses mid-message, the server prepares it (script conversion, translation),
  // so pressing send is instant. Text already in a native script needs no preparation.
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

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends on a computer keyboard; on a phone it starts a new line and the button sends (as in WhatsApp).
    const touch = window.matchMedia('(pointer: coarse)').matches;
    if (e.key === 'Enter' && !e.shiftKey && !touch && !e.nativeEvent.isComposing) {
      e.preventDefault();
      sendText();
    }
  }

  function sayAgain(spoken: string) {
    dispatch({ t: 'local.pending', id: `p${Date.now()}`, text: spoken });
    client.current?.send({ t: 'user.say', text: spoken, source: 'phrase' });
    setActiveBubble(null);
  }
  function copy(value: string) {
    void navigator.clipboard?.writeText(value).then(() => toast.success(t('call.copied'))).catch(() => undefined);
    setActiveBubble(null);
  }

  const name = who.name ?? who.number ?? t('common.call');
  const scamKey = state.scamReason && ['otp_request', 'pin_request', 'upi_pin', 'cvv_request', 'remote_app'].includes(state.scamReason) ? state.scamReason : 'other';
  const send = (e: Parameters<NonNullable<typeof client.current>['send']>[0]) => client.current?.send(e);
  const lastItem = state.feed[state.feed.length - 1];
  const theySpeaking = lastItem?.kind === 'them' && lastItem.partial;

  const status = !online && state.status !== 'ended'
    ? t('call.reconnecting')
    : state.status === 'connected'
      ? theySpeaking ? t('call.speaking') : `${t('call.connected')}${connectedAt ? ` · ${clock(Math.max(0, Math.floor((now - connectedAt) / 1000)))}` : ''}`
      : t(`call.${state.status}`);

  const hasText = text.trim().length > 0;
  const showMic = canUseVoice && !hasText && mode === 'type';

  return (
    <div
      className="chat dark fixed inset-x-0 mx-auto flex max-w-2xl flex-col overflow-hidden"
      style={{ top: viewport.top, height: viewport.height }}
      onClick={(e) => e.target === e.currentTarget && setActiveBubble(null)}
    >
      {/* Header */}
      <header className="pt-safe z-20 flex shrink-0 items-center gap-1 bg-[var(--chat-bar)] px-1.5 pb-2 pt-2 shadow-sm">
        <Button variant="ghost" size="icon" className="text-[var(--chat-fg)] hover:bg-white/10" aria-label={t('call.back')} onClick={() => nav('/')}><ArrowLeft className="size-5" /></Button>
        <Person name={name} className="size-10 bg-white/10" />
        <div className="ml-1.5 min-w-0 flex-1">
          <p className="truncate text-[17px] font-medium leading-tight">{name}</p>
          <p className={cn('truncate text-[13px] leading-tight', theySpeaking ? 'text-[var(--chat-action)]' : 'text-[var(--chat-muted)]')} aria-live="polite">{status}</p>
        </div>
        <Button variant="ghost" size="icon" className="text-[var(--chat-fg)] hover:bg-white/10" aria-label={t('call.captionsTitle')} onClick={() => setSheet('captions')}><Languages className="size-5" /></Button>
        {live && (
          <Button size="icon" className="ml-0.5 rounded-full bg-[var(--chat-danger)] text-white hover:bg-[var(--chat-danger)]/90" aria-label={t('call.endCall')} onClick={() => setConfirmEnd(true)}><PhoneOff className="size-[18px]" /></Button>
        )}
      </header>

      {state.scam && !scamSeen && state.status !== 'ended' && (
        <div role="alert" className="z-10 flex shrink-0 gap-3 bg-[#5c1f27] px-4 py-3 text-white shadow-md">
          <ShieldAlert className="mt-0.5 size-5 shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="font-semibold">{t(`scam.${scamKey}.title`)}</p>
            <p className="text-sm text-white/85">{t(`scam.${scamKey}.body`)}</p>
            <div className="mt-2 flex gap-2">
              <Button size="sm" className="bg-white text-[#5c1f27] hover:bg-white/90" onClick={() => send({ t: 'call.end' })}>{t('call.endCall')}</Button>
              <Button size="sm" variant="ghost" className="text-white hover:bg-white/15 hover:text-white" onClick={() => setScamSeen(true)}>{t('call.continue')}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="relative min-h-0 flex-1">
        <div ref={list} onScroll={onScroll} onPointerDown={(e) => !(e.target as Element).closest('[role=button], button') && setActiveBubble(null)} className="chat-wallpaper h-full overflow-y-auto overscroll-contain px-3 pb-2 pt-1" aria-live="polite">
          <DayDivider label={t('call.today')} />
          {state.feed.length === 0 && (
            <p className="mt-10 text-center text-[15px] text-[var(--chat-muted)]">{state.status === 'connecting' ? t('call.connectingCall') : t('call.waiting')}</p>
          )}
          {state.feed.map((item, idx) => {
            const prev = state.feed[idx - 1];
            const first = !prev || sideOf(prev) !== sideOf(item);
            const key = keyOf(item);
            const active = activeBubble === key;
            switch (item.kind) {
              case 'them':
                return (
                  <div key={key}>
                    <TheirBubble item={item} readLang={caption} first={first} locale={locale} active={active} onTap={() => setActiveBubble(active ? null : key)} />
                    {active && <BubbleActions side="in" onCopy={() => copy(item.translations?.[caption] ?? item.text)} onRead={() => { speak(item.text, (item.lang ?? 'hi').split('-')[0] ?? 'hi'); setActiveBubble(null); }} />}
                  </div>
                );
              case 'you':
                return (
                  <div key={key}>
                    <MyBubble text={item.text} original={item.original} status="said" first={first} at={item.at} locale={locale} active={active} onTap={() => setActiveBubble(active ? null : key)} />
                    {active && <BubbleActions side="out" onCopy={() => copy(item.text)} onAgain={live ? () => sayAgain(item.text) : undefined} />}
                  </div>
                );
              case 'pending':
                return <MyBubble key={key} text={item.text} status="sending" first={first} at={item.at} locale={locale} active={false} />;
              case 'note': {
                const textOf = item.key ? t(item.key, { ...item.params, defaultValue: item.text ?? item.key }) : item.text ?? '';
                return <Note key={key} text={textOf} told={item.key === 'call.toldThem'} />;
              }
              case 'draft':
                return <ActionCard key={key} kind="draft" text={item.text} risk={item.risk} first={first} at={item.at} locale={locale} onSay={() => send({ t: 'user.say', text: item.text, source: 'draft' })} onEdit={() => { setMode('type'); setText(item.text); input.current?.focus(); }} />;
              case 'preview':
                return <ActionCard key={key} kind="preview" text={item.text} original={item.original} first={first} at={item.at} locale={locale} onSay={() => send({ t: 'say.confirm', preview_id: item.id })} onEdit={() => { setText(item.original ?? ''); input.current?.focus(); }} />;
            }
          })}
        </div>
        {showJump && (
          <button type="button" onClick={scrollToEnd} aria-label={t('call.scrollDown')} className="absolute bottom-3 right-3 grid size-11 place-items-center rounded-full bg-[var(--chat-bar)] text-[var(--chat-muted)] shadow-lg">
            <ChevronDown className="size-6" />
            {unread > 0 && <span className="absolute -top-1.5 -right-1 min-w-5 rounded-full bg-[var(--chat-action)] px-1.5 text-center text-xs font-semibold leading-5 text-[#0b141a]">{unread}</span>}
          </button>
        )}
      </div>

      {/* Quick replies sit in the layout above the input, never on top of it. */}
      {live && !voice.active && (suggestion || state.suggestions.length > 0) && (
        <div className="no-scrollbar flex shrink-0 gap-2 overflow-x-auto px-2 pb-1.5 pt-1" aria-label={t('call.more')}>
          {suggestion && (
            <button type="button" onClick={() => { setText(suggestion); setSuggestion(null); input.current?.focus(); }} className="shrink-0 whitespace-nowrap rounded-full border border-[var(--chat-action)]/60 bg-[var(--chat-bar)] px-3.5 py-2 text-[15px]">
              {t('call.inScript', { lang: nativeName(typeLang), text: suggestion })}
            </button>
          )}
          {state.suggestions.map((s) => (
            <button key={s} type="button" onClick={() => { dispatch({ t: 'local.pending', id: `p${Date.now()}`, text: s }); send({ t: 'user.say', text: s, source: 'reply' }); }} className="shrink-0 whitespace-nowrap rounded-full bg-[var(--chat-bar)] px-3.5 py-2 text-[15px] shadow-sm transition-colors hover:bg-[var(--chat-composer)]">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div className="pb-safe shrink-0 px-1.5 pb-1.5 pt-0.5">
        {live ? (
          <form className="flex items-end gap-1.5" onSubmit={(e) => { e.preventDefault(); sendText(); }}>
            {voice.active ? (
              <div className="flex min-h-12 flex-1 items-center gap-3 rounded-[1.6rem] bg-[var(--chat-composer)] px-4 py-2" aria-live="polite">
                <span className="size-2.5 shrink-0 animate-pulse rounded-full bg-[var(--chat-danger)]" aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate text-[15px]">{heard ? t('call.voiceHeard', { text: heard }) : <>{t('call.voiceListening')}<Dots /></>}</span>
                <label className="flex shrink-0 items-center gap-2 text-[13px] text-[var(--chat-muted)]">
                  {t('call.autoSend')}
                  <Switch checked={autoSend} onCheckedChange={changeAutoSend} aria-label={t('call.autoSend')} />
                </label>
              </div>
            ) : (
              <div className="flex min-h-12 flex-1 items-end rounded-[1.6rem] bg-[var(--chat-composer)] pl-1 pr-1">
                <button type="button" onClick={() => setSheet('phrases')} aria-label={t('call.phrases')} className="grid size-11 shrink-0 place-items-center rounded-full text-[var(--chat-muted)] hover:text-[var(--chat-fg)]"><MessageSquareText className="size-6" /></button>
                <div className="flex min-w-0 flex-1 flex-col py-1.5">
                  {mode === 'help' && (
                    <span className="mb-1 flex w-fit items-center gap-1 rounded-full bg-[var(--chat-action)]/20 py-0.5 pl-2 pr-1 text-xs font-medium text-[var(--chat-action)]">
                      <Sparkles className="size-3" /> {t('call.helpOn')}
                      <button type="button" onClick={() => setMode('type')} aria-label={t('call.helpOff')} className="grid size-4 place-items-center rounded-full hover:bg-white/10"><X className="size-3" /></button>
                    </span>
                  )}
                  <textarea
                    ref={input}
                    rows={1}
                    value={text}
                    onChange={(e) => onType(e.target.value)}
                    onKeyDown={onKeyDown}
                    enterKeyHint="send"
                    aria-label={mode === 'help' ? t('call.helpPlaceholder') : t('call.typePlaceholder')}
                    placeholder={mode === 'help' ? t('call.helpPlaceholder') : t('call.typePlaceholder')}
                    className="block max-h-36 w-full resize-none bg-transparent py-1.5 text-[17px] leading-6 text-[var(--chat-fg)] outline-none placeholder:text-[var(--chat-muted)]"
                  />
                </div>
                <button type="button" onClick={() => setSheet('more')} aria-label={t('call.more')} className="grid size-11 shrink-0 place-items-center rounded-full text-[var(--chat-muted)] hover:text-[var(--chat-fg)]"><Plus className="size-6" /></button>
              </div>
            )}
            {voice.active ? (
              <button type="button" onClick={toggleVoice} aria-label={t('call.micStop')} className="grid size-12 shrink-0 place-items-center rounded-full bg-[var(--chat-danger)] text-white shadow-md"><Square className="size-5" /></button>
            ) : showMic ? (
              <button type="button" onClick={toggleVoice} aria-label={t('call.micStart')} className="grid size-12 shrink-0 place-items-center rounded-full bg-[var(--chat-action)] text-[#0b141a] shadow-md"><Mic className="size-6" /></button>
            ) : (
              // Keeping focus in the box keeps the keyboard open after sending, as in WhatsApp.
              <button type="submit" onPointerDown={(e) => e.preventDefault()} disabled={!hasText && !preview} aria-label={mode === 'help' ? t('call.helpOn') : t('call.sayIt')} className="grid size-12 shrink-0 place-items-center rounded-full bg-[var(--chat-action)] text-[#0b141a] shadow-md disabled:opacity-50">
                {mode === 'help' ? <Sparkles className="size-5" /> : <SendHorizontal className="size-5" />}
              </button>
            )}
          </form>
        ) : (
          <div className="flex items-center gap-2 rounded-2xl bg-[var(--chat-bar)] p-2">
            <p className="flex-1 px-2 text-[15px] text-[var(--chat-muted)]">{status}</p>
            {state.status === 'ended' && <Button variant="ghost" asChild className="text-[var(--chat-action)] hover:bg-white/5"><Link to={`/calls/${sessionId}`}>{t('call.seeSummary')}</Link></Button>}
            <Button className="bg-[var(--chat-action)] text-[#0b141a] hover:bg-[var(--chat-action)]/90" onClick={() => nav('/')}>{t('call.back')}</Button>
          </div>
        )}
      </div>

      {/* Phrases */}
      <Sheet open={sheet === 'phrases'} onOpenChange={(o) => !o && setSheet(null)}>
        <SheetContent side="bottom" className="chat dark mx-auto max-h-[75dvh] max-w-2xl overflow-y-auto rounded-t-3xl border-0 bg-[var(--chat-bar)]">
          <SheetHeader><SheetTitle>{t('call.phrases')}</SheetTitle><SheetDescription>{t('call.phrasesHint')}</SheetDescription></SheetHeader>
          <div className="grid gap-2 px-4 pb-6">
            {usablePhrases.map((p) => (
              <button key={p.label + p.text} type="button" onClick={() => { dispatch({ t: 'local.pending', id: `p${Date.now()}`, text: p.text }); send({ t: 'user.say', text: p.text, source: 'phrase' }); setSheet(null); }} className="rounded-2xl bg-[var(--chat-composer)] px-4 py-3 text-left transition-colors hover:brightness-110">
                <span className="block font-medium">{p.label}</span>
                <span className="block text-sm text-[var(--chat-muted)]">{p.text}</span>
              </button>
            ))}
          </div>
        </SheetContent>
      </Sheet>

      {/* More: keypad, ask again, help me say (like WhatsApp's attach sheet) */}
      <Sheet open={sheet === 'more' || sheet === 'captions'} onOpenChange={(o) => !o && setSheet(null)}>
        <SheetContent side="bottom" className="chat dark mx-auto max-w-2xl rounded-t-3xl border-0 bg-[var(--chat-bar)] pb-6">
          {sheet === 'captions' ? (
            <>
              <SheetHeader><SheetTitle>{t('call.captionsTitle')}</SheetTitle><SheetDescription>{t('call.captionsHint')}</SheetDescription></SheetHeader>
              <div className="px-4"><LanguageSelect value={caption} onChange={(c) => { changeCaptionLanguage(c); setSheet(null); }} /></div>
            </>
          ) : (
            <>
              <SheetHeader><SheetTitle>{t('call.more')}</SheetTitle></SheetHeader>
              <div className="grid grid-cols-4 gap-2 px-4">
                {[
                  { icon: Grid3x3, label: t('call.keypad'), color: '#7f66ff', run: () => setSheet('keypad') },
                  { icon: Repeat, label: t('call.askAgain'), color: '#00a884', run: () => { send({ t: 'user.ask_repeat' }); setSheet(null); } },
                  ...(canHelp ? [{ icon: Sparkles, label: t('call.helpMeSay'), color: '#ffbc38', run: () => { setMode('help'); setSheet(null); input.current?.focus(); } }] : []),
                  { icon: Languages, label: t('call.captionsIn'), color: '#53bdeb', run: () => setSheet('captions') },
                ].map(({ icon: Icon, label, color, run }) => (
                  <button key={label} type="button" onClick={run} className="flex flex-col items-center gap-1.5 rounded-xl py-2 text-[13px] text-[var(--chat-fg)] hover:bg-white/5">
                    <span className="grid size-14 place-items-center rounded-full text-white" style={{ background: color }}><Icon className="size-6" /></span>
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Keypad */}
      <Sheet open={sheet === 'keypad'} onOpenChange={(o) => !o && setSheet(null)}>
        <SheetContent side="bottom" className="chat dark mx-auto max-w-2xl rounded-t-3xl border-0 bg-[var(--chat-bar)]">
          <SheetHeader><SheetTitle>{t('call.keypad')}</SheetTitle><SheetDescription>{t('call.keypadHint')}</SheetDescription></SheetHeader>
          <div className="mx-auto grid max-w-xs grid-cols-3 gap-3 px-4 pb-8">
            {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((d) => (
              <button key={d} type="button" className="size-[4.5rem] justify-self-center rounded-full bg-[var(--chat-composer)] text-2xl transition-colors active:bg-[var(--chat-action)] active:text-[#0b141a]" onClick={() => send({ t: 'user.dtmf', digits: d })}>{d}</button>
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
