import { describe, expect, it } from 'vitest';
import i18n from '../i18n';
import { applyPreset, emptyProfile, summary, toggle, withLanguage, withModes } from './profile';

const mute = { label: 'I can’t speak', talk: ['type', 'replies', 'help'], hear: ['audio', 'summary'], disability_phrase: 'cannot speak' } as const;

describe('profile helpers', () => {
  it('toggle adds at the end, removes, and never leaves the list empty', () => {
    expect(toggle(['type'], 'voice')).toEqual(['type', 'voice']);
    expect(toggle(['type', 'voice'], 'type')).toEqual(['voice']);
    expect(toggle(['type'], 'type')).toEqual(['type']);
  });

  it('a preset sets both lists; editing by hand makes it custom', () => {
    const p = applyPreset(emptyProfile(), 'mute', { ...mute, talk: [...mute.talk], hear: [...mute.hear] });
    expect(p.preset).toBe('mute');
    expect(p.talk_modes).toEqual(['type', 'replies', 'help']);
    expect(withModes(p, { hear_modes: ['captions'] }).preset).toBeNull();
  });

  it('picking a language sets the app, captions and typing to it', () => {
    expect(withLanguage(emptyProfile(), 'ta')).toMatchObject({ app_lang: 'ta', read_lang: 'ta', type_lang: 'ta' });
    expect(withLanguage(emptyProfile(), 'hi-Latn')).toMatchObject({ app_lang: 'hi-Latn', read_lang: 'hi-Latn', type_lang: 'hi-Latn' });
  });

  it('summary names the default way of talking first', () => {
    const p = applyPreset(emptyProfile(), 'mute', { ...mute, talk: [...mute.talk], hear: [...mute.hear] });
    const t = i18n.t.bind(i18n) as (k: string, o?: Record<string, string>) => string;
    expect(summary(p, t)).toContain('You talk with: type, awaaz speaks');
    expect(summary(p, t)).toContain('You hear with: normal audio, spoken summary after');
  });
});
