import { describe, expect, it } from 'vitest';
import { applyEvent, initialState, splitByEntities, type ServerEvent } from './feed';

const run = (events: ServerEvent[]) => events.reduce(applyEvent, initialState);

describe('applyEvent', () => {
  it('tracks call state and turns disclosure/keeper into notes', () => {
    const s = run([
      { t: 'call.state', state: 'connected' },
      { t: 'you.final', turn: 1, text: 'Namaste, main Rafiq bol raha hoon.', source: 'disclosure' },
    ]);
    expect(s.status).toBe('connected');
    expect(s.feed).toHaveLength(1);
    expect(s.feed[0]).toMatchObject({ kind: 'note' });
  });

  it('replaces a partial caption with the final one for the same turn', () => {
    const s = run([
      { t: 'caption.partial', turn: 2, text: 'हाँ जी' },
      { t: 'caption.final', turn: 2, text: 'हाँ जी, बोलिए', confidence: 0.9, entities: [] },
    ]);
    const them = s.feed.filter((i) => i.kind === 'them');
    expect(them).toHaveLength(1);
    expect(them[0]).toMatchObject({ text: 'हाँ जी, बोलिए' });
    expect(them[0]).not.toHaveProperty('partial', true);
  });

  it('ignores a replayed you.final and clears a pending preview when speech goes out', () => {
    const s = run([
      { t: 'say.preview', preview_id: 'p1', text: 'कृपया', original: 'please' },
      { t: 'you.final', turn: 3, text: 'कृपया', source: 'typed', original: 'please' },
      { t: 'you.final', turn: 3, text: 'कृपया', source: 'typed', original: 'please' },
    ]);
    expect(s.feed.filter((i) => i.kind === 'you')).toHaveLength(1);
    expect(s.feed.some((i) => i.kind === 'preview')).toBe(false);
  });

  it('shows one draft at a time and clears it once speech goes out', () => {
    const s1 = run([
      { t: 'draft.ready', draft_id: 'd1', text: 'Mujhe 30 goliyan chahiye.', from_words: '30 goli' },
      { t: 'draft.ready', draft_id: 'd2', text: 'Mujhe 60 goliyan chahiye.', changed_meaning_risk: true },
    ]);
    expect(s1.feed.filter((i) => i.kind === 'draft')).toHaveLength(1);
    expect(s1.feed[0]).toMatchObject({ kind: 'draft', id: 'd2', risk: true });
    const s2 = applyEvent(s1, { t: 'you.final', turn: 5, text: 'Mujhe 60 goliyan chahiye.', source: 'draft' });
    expect(s2.feed.some((i) => i.kind === 'draft')).toBe(false);
  });

  it('explains blocked messages and flags scam warnings', () => {
    const s = run([{ t: 'say.blocked', reason: 'scam_digits' }, { t: 'scam.warning', reason: 'otp_request' }]);
    expect(s.scam).toBe(true);
    expect(s.scamReason).toBe('otp_request');
    expect(JSON.stringify(s.feed)).toContain('OTP');
  });
});

describe('splitByEntities', () => {
  it('highlights spans and keeps the text between them', () => {
    const text = 'हाँ, मिल जाएगी। ₹420 होंगे, शाम 6 बजे तक तैयार।';
    const a = text.indexOf('₹420');
    const b = text.indexOf('शाम 6 बजे');
    const pieces = splitByEntities(text, [
      { type: 'time', text: 'शाम 6 बजे', start: b, end: b + 'शाम 6 बजे'.length },
      { type: 'money', text: '₹420', start: a, end: a + 4 },
    ]);
    expect(pieces.map((p) => p.text).join('')).toBe(text);
    expect(pieces.filter((p) => p.entity).map((p) => p.text)).toEqual(['₹420', 'शाम 6 बजे']);
  });

  it('skips bad or overlapping spans instead of breaking the text', () => {
    const pieces = splitByEntities('abc', [
      { type: 'money', text: 'x', start: 5, end: 9 },
      { type: 'date', text: 'ab', start: 0, end: 2 },
      { type: 'time', text: 'bc', start: 1, end: 3 },
    ]);
    expect(pieces.map((p) => p.text).join('')).toBe('abc');
    expect(pieces.filter((p) => p.entity)).toHaveLength(1);
  });
});
