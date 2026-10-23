import { describe, expect, it } from 'vitest';
import { applyPreset, summary, toggle, withModes, emptyProfile } from './profile';

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

  it('summary names the default way of talking first', () => {
    const p = applyPreset(emptyProfile(), 'mute', { ...mute, talk: [...mute.talk], hear: [...mute.hear] });
    expect(summary(p)).toContain('You talk with: type, awaaz speaks');
    expect(summary(p)).toContain('You hear with: normal audio, spoken summary after');
  });
});
