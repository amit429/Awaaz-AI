// Pure state for the call screen: server events in, feed items out.

export interface Entity {
  type: 'money' | 'time' | 'date' | 'phone' | 'otp_request' | 'name' | 'quantity';
  text: string;
  value?: string | number | null;
  start?: number;
  end?: number;
}

export type ServerEvent =
  | { t: 'call.state'; state: 'ringing' | 'connected' | 'ended' | 'failed'; reason?: string }
  | { t: 'caption.partial'; turn: number; text: string }
  | { t: 'caption.final'; turn: number; text: string; lang?: string; translated?: string | null; confidence: number; entities: Entity[] }
  | { t: 'you.final'; turn: number; text: string; source: string; original?: string }
  | { t: 'suggestions'; turn: number; items: string[] }
  | { t: 'draft.ready'; draft_id: string; text: string; from_words?: string; changed_meaning_risk?: boolean }
  | { t: 'say.preview'; preview_id: string; text: string; original?: string }
  | { t: 'say.blocked'; reason: 'scam_digits' | 'empty' | 'too_long' }
  | { t: 'scam.warning'; reason: string; turn?: number }
  | { t: 'keeper.spoken' }
  | { t: 'mode.updated'; talk_modes?: string[]; hear_modes?: string[] }
  | { t: 'error'; code: string; message: string }
  | { t: 'ping' };

export type FeedItem =
  | { kind: 'them'; turn: number; text: string; entities: Entity[]; translated?: string | null; partial?: boolean }
  | { kind: 'you'; turn: number; text: string; source: string; original?: string }
  | { kind: 'note'; id: string; text: string }
  | { kind: 'preview'; id: string; text: string; original?: string }
  | { kind: 'draft'; id: string; text: string; fromWords?: string; risk: boolean };

export interface CallState {
  status: 'connecting' | 'ringing' | 'connected' | 'ended' | 'failed';
  endReason?: string;
  feed: FeedItem[];
  suggestions: string[];
  scam: boolean;
  scamReason?: string;
}

export const initialState: CallState = { status: 'connecting', feed: [], suggestions: [], scam: false };

export const SCAM_COPY: Record<string, { title: string; body: string }> = {
  otp_request: { title: 'They asked for your OTP', body: 'Banks never ask for an OTP on a call. Awaaz won’t read out OTPs or PINs on this call.' },
  pin_request: { title: 'They asked for your PIN', body: 'No bank or shop needs your PIN on a call. Awaaz won’t read out PINs or codes on this call.' },
  upi_pin: { title: 'They asked for your UPI PIN', body: 'Your UPI PIN is only for you. Awaaz won’t read out PINs or codes on this call.' },
  cvv_request: { title: 'They asked for your card’s CVV', body: 'Never share the CVV on a call. Awaaz won’t read out card details on this call.' },
  remote_app: { title: 'They asked you to install an app', body: 'Never install an app because a caller asks. It lets them see your phone and your bank.' },
  other: { title: 'This may be a scam call', body: 'Be careful. Awaaz won’t read out OTPs, PINs or card details on this call.' },
};

const BLOCKED: Record<string, string> = {
  scam_digits: 'Not sent: Awaaz won’t speak OTP or PIN digits on this call.',
  empty: 'Nothing to send.',
  too_long: 'That message is too long. Please shorten it.',
};

let noteId = 0;
const note = (text: string, id?: string): FeedItem => ({ kind: 'note', id: id ?? `n${++noteId}`, text });
const withNote = (feed: FeedItem[], item: FeedItem): FeedItem[] => (feed.some((i) => i.kind === 'note' && i.id === (item as { id: string }).id) ? feed : [...feed, item]);

export function applyEvent(state: CallState, ev: ServerEvent): CallState {
  switch (ev.t) {
    case 'call.state':
      return { ...state, status: ev.state, endReason: ev.reason };
    case 'caption.partial': {
      const rest = state.feed.filter((i) => !(i.kind === 'them' && i.turn === ev.turn));
      return { ...state, feed: [...rest, { kind: 'them', turn: ev.turn, text: ev.text, entities: [], partial: true }] };
    }
    case 'caption.final': {
      const rest = state.feed.filter((i) => !(i.kind === 'them' && i.turn === ev.turn));
      return {
        ...state,
        suggestions: [],
        feed: [...rest, { kind: 'them', turn: ev.turn, text: ev.text, entities: ev.entities, translated: ev.translated }],
      };
    }
    case 'you.final': {
      if (ev.source === 'disclosure' || ev.source === 'keeper') {
        // keyed by turn, so a reconnect that replays the turn does not add it twice
        return { ...state, feed: withNote(state.feed, note(`Awaaz told them: ${ev.text}`, `turn-${ev.turn}`)) };
      }
      if (state.feed.some((i) => i.kind === 'you' && i.turn === ev.turn)) return state; // replay duplicate
      const feed = state.feed.filter((i) => i.kind !== 'preview' && i.kind !== 'draft');
      return { ...state, suggestions: [], feed: [...feed, { kind: 'you', turn: ev.turn, text: ev.text, source: ev.source, original: ev.original }] };
    }
    case 'suggestions':
      return { ...state, suggestions: ev.items };
    case 'draft.ready':
      return { ...state, feed: [...state.feed.filter((i) => i.kind !== 'draft'), { kind: 'draft', id: ev.draft_id, text: ev.text, fromWords: ev.from_words, risk: Boolean(ev.changed_meaning_risk) }] };
    case 'say.preview':
      return { ...state, feed: [...state.feed.filter((i) => i.kind !== 'preview'), { kind: 'preview', id: ev.preview_id, text: ev.text, original: ev.original }] };
    case 'say.blocked':
      return { ...state, feed: [...state.feed, note(BLOCKED[ev.reason] ?? 'Not sent.')] };
    case 'scam.warning':
      return { ...state, scam: true, scamReason: ev.reason };
    case 'error':
      return { ...state, feed: [...state.feed, note(ev.message)] };
    default:
      return state;
  }
}

export interface Piece {
  text: string;
  entity?: Entity;
}

/** Split a caption into plain text and highlighted entity chips (spans from the server). */
export function splitByEntities(text: string, entities: Entity[]): Piece[] {
  const spans = entities
    .filter((e) => typeof e.start === 'number' && typeof e.end === 'number' && e.end > e.start)
    .sort((a, b) => (a.start as number) - (b.start as number));
  const out: Piece[] = [];
  let at = 0;
  for (const e of spans) {
    const start = e.start as number;
    const end = e.end as number;
    if (start < at || end > text.length) continue; // overlapping or out of range: skip
    if (start > at) out.push({ text: text.slice(at, start) });
    out.push({ text: text.slice(start, end), entity: e });
    at = end;
  }
  if (at < text.length) out.push({ text: text.slice(at) });
  return out;
}
