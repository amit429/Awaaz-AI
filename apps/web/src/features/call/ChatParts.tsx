import { CheckCheck, Clock, Copy, RotateCcw, ShieldCheck, Sparkles, Volume2, Languages } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { nativeName } from '@/i18n';
import { splitByEntities, type FeedItem } from '@/lib/feed';
import { cn } from '@/lib/utils';

type Them = Extract<FeedItem, { kind: 'them' }>;

export const timeOf = (at: number | undefined, locale: string) =>
  at ? new Intl.DateTimeFormat(locale, { hour: 'numeric', minute: '2-digit' }).format(at) : '';

/** Numbers, prices and times picked out, the same way in a translation as in the original. */
export function withChips(text: string) {
  return text.split(/(₹\s?\d+(?:,\d+)*|\d{1,2}:\d{2}|\d+(?:,\d+)*(?:\s?(?:am|pm|AM|PM))?)/g).map((part, i) =>
    i % 2 === 1 ? <mark key={i} className="rounded bg-accent px-1 font-semibold text-accent-foreground">{part}</mark> : <span key={i}>{part}</span>,
  );
}

/** The small pointed corner on the first bubble of a run, as in WhatsApp. */
function Tail({ side }: { side: 'in' | 'out' }) {
  return (
    <span
      aria-hidden="true"
      className={cn('absolute top-0 h-3 w-2', side === 'in' ? '-left-2' : '-right-2')}
      style={{
        background: side === 'in' ? 'var(--bubble-in)' : 'var(--bubble-out)',
        clipPath: side === 'in' ? 'polygon(100% 0, 0 0, 100% 100%)' : 'polygon(0 0, 100% 0, 0 100%)',
      }}
    />
  );
}

/** Time and status, tucked into the bottom-right corner of the bubble. */
function Meta({ time, status }: { time: string; status?: 'sending' | 'said' }) {
  const { t } = useTranslation();
  return (
    <span className="absolute bottom-1 right-2 flex items-center gap-1 text-[11px] leading-none text-[var(--chat-muted)]">
      {time}
      {status === 'sending' && <Clock className="size-3.5" aria-label={t('call.sending')} />}
      {status === 'said' && <CheckCheck className="size-4 text-[var(--chat-tick)]" aria-label={t('call.saidOnCall')} />}
    </span>
  );
}

function Bubble({ side, first, meta, onClick, active, children }: { side: 'in' | 'out'; first: boolean; meta: React.ReactNode; onClick?: () => void; active?: boolean; children: React.ReactNode }) {
  return (
    <div className={cn('flex w-full', side === 'out' ? 'justify-end' : 'justify-start', first ? 'mt-2' : 'mt-0.5')}>
      <div
        role={onClick ? 'button' : undefined}
        tabIndex={onClick ? 0 : undefined}
        onClick={onClick}
        onKeyDown={(e) => onClick && (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onClick())}
        className={cn(
          'relative max-w-[85%] rounded-lg px-2.5 pb-1.5 pt-1.5 shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-action)]',
          side === 'in' ? 'bg-[var(--bubble-in)]' : 'bg-[var(--bubble-out)]',
          first && (side === 'in' ? 'rounded-tl-none' : 'rounded-tr-none'),
          active && 'brightness-125',
        )}
      >
        {first && <Tail side={side} />}
        {children}
        {meta}
      </div>
    </div>
  );
}

/** Space reserved at the end of the text so the time never sits on top of a word. */
const Spacer = ({ wide }: { wide?: boolean }) => <span aria-hidden="true" className={cn('inline-block', wide ? 'w-[4.5rem]' : 'w-14')} />;

export function TheirBubble({ item, readLang, first, locale, active, onTap, waiting }: { item: Them; readLang: string; first: boolean; locale: string; active: boolean; onTap: () => void; waiting: boolean }) {
  const { t } = useTranslation();
  const spoken = (item.lang ?? '').split('-')[0];
  const translation = spoken === readLang ? undefined : item.translations?.[readLang];
  const original = splitByEntities(item.text, item.entities).map((p, i) =>
    p.entity ? <mark key={i} className="rounded bg-accent px-1 font-semibold text-accent-foreground" aria-label={`${p.entity.type}: ${p.text}`}>{p.text}</mark> : <span key={i}>{p.text}</span>,
  );
  return (
    <Bubble side="in" first={first} active={active} onClick={item.partial ? undefined : onTap} meta={<Meta time={timeOf(item.at, locale)} />}>
      {translation ? (
        <>
          <p className="text-lg leading-snug">{withChips(translation)}</p>
          <p className="mt-1 text-sm leading-snug text-[var(--chat-muted)]">{t('call.original', { text: item.text })}<Spacer /></p>
        </>
      ) : (
        <>
          <p className={cn('text-lg leading-snug', item.partial && 'opacity-70')}>
            {original}
            {item.partial && <Dots />}
            {!(waiting && !item.partial && spoken !== readLang) && <Spacer />}
          </p>
          {waiting && !item.partial && spoken !== readLang && (
            <p className="mt-1 text-sm text-[var(--chat-muted)]">{t('call.translating', { lang: nativeName(readLang) })}<Dots /><Spacer /></p>
          )}
        </>
      )}
    </Bubble>
  );
}

export function MyBubble({ text, original, status, first, at, locale, active, onTap }: { text: string; original?: string; status: 'sending' | 'said'; first: boolean; at?: number; locale: string; active: boolean; onTap?: () => void }) {
  const { t } = useTranslation();
  return (
    <Bubble side="out" first={first} active={active} onClick={onTap} meta={<Meta time={timeOf(at, locale)} status={status} />}>
      <p className={cn('text-[17px] leading-snug', status === 'sending' && 'opacity-80')}>
        {text}
        {!original && <Spacer wide />}
      </p>
      {original && <p className="mt-0.5 text-[13px] leading-snug text-white/60">{t('call.youTyped', { text: original })}<Spacer wide /></p>}
    </Bubble>
  );
}

/** "They are speaking" dots, like WhatsApp's typing indicator. */
export function Dots() {
  return (
    <span className="ml-1.5 inline-flex gap-0.5 align-middle" aria-hidden="true">
      {[0, 1, 2].map((i) => <span key={i} className="chat-dot size-1.5 rounded-full bg-current" style={{ animationDelay: `${i * 0.15}s` }} />)}
    </span>
  );
}

/** System lines in the middle of the chat (what Awaaz told them, blocked numbers, errors). */
export function Note({ text, told }: { text: string; told?: boolean }) {
  return (
    <div className="my-2 flex justify-center">
      <p className={cn('flex max-w-[88%] items-start gap-1.5 rounded-lg px-3 py-1.5 text-center text-[12.5px] leading-snug shadow-sm', told ? 'bg-[#1d2c26] text-[#f7e7a1]' : 'bg-[var(--chat-note)] text-[var(--chat-muted)]')}>
        {told && <ShieldCheck className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />}
        <span>{text}</span>
      </p>
    </div>
  );
}

export function DayDivider({ label }: { label: string }) {
  return (
    <div className="my-2 flex justify-center">
      <span className="rounded-lg bg-[var(--chat-note)] px-3 py-1 text-xs font-medium uppercase tracking-wide text-[var(--chat-muted)] shadow-sm">{label}</span>
    </div>
  );
}

/** A message from Awaaz with buttons inside it (draft from Help me say, or a translation to check). */
export function ActionCard({ kind, text, original, risk, first, at, locale, onSay, onEdit }: { kind: 'draft' | 'preview'; text: string; original?: string; risk?: boolean; first: boolean; at?: number; locale: string; onSay: () => void; onEdit: () => void }) {
  const { t } = useTranslation();
  const Icon = kind === 'draft' ? Sparkles : Languages;
  return (
    <Bubble side="in" first={first} meta={null}>
      <p className="flex items-center gap-1.5 text-[13px] font-medium text-[var(--chat-action)]"><Icon className="size-3.5" /> {kind === 'draft' ? t('call.draftTitle') : t('call.previewTitle')}</p>
      <p className="mt-1 text-[17px] leading-snug">{text}</p>
      {original && <p className="mt-1 text-[13px] text-[var(--chat-muted)]">{t('call.youTyped', { text: original })}</p>}
      {risk && <p className="mt-1 text-[13px] text-accent">{t('call.draftUnclear')}</p>}
      <p className="mt-1 text-right text-[11px] text-[var(--chat-muted)]">{timeOf(at, locale)}</p>
      <div className="-mx-2.5 mt-1.5 grid grid-cols-2 border-t border-white/10 text-[15px] font-medium text-[var(--chat-action)]">
        <button type="button" onClick={onSay} className="py-2.5 transition-colors hover:bg-white/5">{t('call.sayIt')}</button>
        <button type="button" onClick={onEdit} className="border-l border-white/10 py-2.5 transition-colors hover:bg-white/5">{t('common.edit')}</button>
      </div>
    </Bubble>
  );
}

/** What can be done with a tapped bubble. */
export function BubbleActions({ side, onCopy, onRead, onAgain }: { side: 'in' | 'out'; onCopy: () => void; onRead?: () => void; onAgain?: () => void }) {
  const { t } = useTranslation();
  const btn = 'flex items-center gap-1.5 rounded-full bg-[var(--chat-bar)] px-3 py-1.5 text-[13px] shadow-sm transition-colors hover:bg-[var(--chat-composer)]';
  return (
    <div className={cn('mt-1 flex gap-1.5', side === 'out' ? 'justify-end' : 'justify-start')}>
      <button type="button" className={btn} onClick={onCopy}><Copy className="size-3.5" /> {t('call.copy')}</button>
      {onRead && <button type="button" className={btn} onClick={onRead}><Volume2 className="size-3.5" /> {t('call.readAloud')}</button>}
      {onAgain && <button type="button" className={btn} onClick={onAgain}><RotateCcw className="size-3.5" /> {t('call.sayAgain')}</button>}
    </div>
  );
}
