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
  | { t: 'caption.translation'; turn: number; lang: string; text: string }
  | { t: 'read.updated'; lang: string }
  | { t: 'you.final'; turn: number; text: string; source: string; original?: string }
  | { t: 'suggestions'; turn: number; items: string[] }
  | { t: 'draft.ready'; draft_id: string; text: string; from_words?: string; changed_meaning_risk?: boolean }
  | { t: 'say.preview'; preview_id: string; text: string; original?: string }
  | { t: 'say.blocked'; reason: 'scam_digits' | 'empty' | 'too_long' }
  | { t: 'scam.warning'; reason: string; turn?: number }
  | { t: 'keeper.spoken' }
  | { t: 'mode.updated'; talk_modes?: string[]; hear_modes?: string[] }
  | { t: 'error'; code: string; message: string }
  | { t: 'ping' }
  | { t: 'local.pending'; id: string; text: string }; // not from the server: shows a message the moment it is sent

/** `at` is when the item first appeared on this screen (ms), shown as the bubble time. */
export type FeedItem = (
  | { kind: 'them'; turn: number; text: string; entities: Entity[]; lang?: string; translations?: Record<string, string>; partial?: boolean }
  | { kind: 'pending'; id: string; text: string }
  | { kind: 'you'; turn: number; text: string; source: string; original?: string }
  | { kind: 'note'; id: string; key?: string; params?: Record<string, string>; text?: string }
  | { kind: 'preview'; id: string; text: string; original?: string }
  | { kind: 'draft'; id: string; text: string; fromWords?: string; risk: boolean }
) & { at?: number };

export interface CallState {
  status: 'connecting' | 'ringing' | 'connected' | 'ended' | 'failed';
  endReason?: string;
  feed: FeedItem[];
  suggestions: string[];
  scam: boolean;
  scamReason?: string;
  readLang?: string;
}

export const initialState: CallState = { status: 'connecting', feed: [], suggestions: [], scam: false };



let noteId = 0;
const note = (key: string, params?: Record<string, string>, id?: string): FeedItem => ({ kind: 'note', id: id ?? `n${++noteId}`, key, params, at: Date.now() });
const firstSeen = (feed: FeedItem[], turn: number): number => feed.find((i) => i.kind === 'them' && i.turn === turn)?.at ?? Date.now();
const withNote = (feed: FeedItem[], item: FeedItem): FeedItem[] => (feed.some((i) => i.kind === 'note' && i.id === (item as { id: string }).id) ? feed : [...feed, item]);

/** The oldest message still waiting for the server to prepare it is done (it now has a real bubble). */
const settleOne = (feed: FeedItem[]): FeedItem[] => {
  const i = feed.findIndex((x) => x.kind === 'pending');
  return i < 0 ? feed : feed.filter((_, j) => j !== i);
};

export function applyEvent(state: CallState, ev: ServerEvent): CallState {
  switch (ev.t) {
    case 'local.pending':
      return { ...state, feed: [...state.feed, { kind: 'pending', id: ev.id, text: ev.text, at: Date.now() }] };
    case 'call.state':
      return {
        ...state,
        status: ev.state,
        endReason: ev.reason,
        feed: ev.state === 'ended' || ev.state === 'failed' ? state.feed.filter((i) => i.kind !== 'pending') : state.feed,
      };
    case 'caption.partial': {
      const rest = state.feed.filter((i) => !(i.kind === 'them' && i.turn === ev.turn));
      return { ...state, feed: [...rest, { kind: 'them', turn: ev.turn, text: ev.text, entities: [], partial: true, at: firstSeen(state.feed, ev.turn) }] };
    }
    case 'caption.final': {
      const rest = state.feed.filter((i) => !(i.kind === 'them' && i.turn === ev.turn));
      return {
        ...state,
        suggestions: [],
        feed: [...rest, { kind: 'them', turn: ev.turn, text: ev.text, entities: ev.entities, lang: ev.lang, translations: ev.translated && state.readLang ? { [state.readLang]: ev.translated } : {}, at: firstSeen(state.feed, ev.turn) }],
      };
    }
    case 'you.final': {
      if (ev.source === 'disclosure' || ev.source === 'keeper') {
        // keyed by turn, so a reconnect that replays the turn does not add it twice
        return { ...state, feed: withNote(state.feed, note('call.toldThem', { text: ev.text }, `turn-${ev.turn}`)) };
      }
      if (state.feed.some((i) => i.kind === 'you' && i.turn === ev.turn)) return state; // replay duplicate
      const feed = settleOne(state.feed.filter((i) => i.kind !== 'preview' && i.kind !== 'draft'));
      return { ...state, suggestions: [], feed: [...feed, { kind: 'you', turn: ev.turn, text: ev.text, source: ev.source, original: ev.original, at: Date.now() }] };
    }
    case 'caption.translation':
      return {
        ...state,
        feed: state.feed.map((i) => (i.kind === 'them' && i.turn === ev.turn ? { ...i, translations: { ...i.translations, [ev.lang]: ev.text } } : i)),
      };
    case 'read.updated':
      return { ...state, readLang: ev.lang };
    case 'suggestions':
      return { ...state, suggestions: ev.items };
    case 'draft.ready':
      return { ...state, feed: [...state.feed.filter((i) => i.kind !== 'draft'), { kind: 'draft', id: ev.draft_id, text: ev.text, fromWords: ev.from_words, risk: Boolean(ev.changed_meaning_risk), at: Date.now() }] };
    case 'say.preview':
      return { ...state, feed: [...settleOne(state.feed).filter((i) => i.kind !== 'preview'), { kind: 'preview', id: ev.preview_id, text: ev.text, original: ev.original, at: Date.now() }] };
    case 'say.blocked':
      return { ...state, feed: [...settleOne(state.feed), note(`call.blocked.${ev.reason}`)] };
    case 'scam.warning':
      return { ...state, scam: true, scamReason: ev.reason };
    case 'error':
      return { ...state, feed: [...state.feed.filter((i) => i.kind !== 'pending'), { kind: 'note', id: `n${++noteId}`, key: `errors.${ev.code}`, text: ev.message, at: Date.now() }] };
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
