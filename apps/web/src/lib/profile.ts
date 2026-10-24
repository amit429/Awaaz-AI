import { AudioLines, Bell, Captions, Ear, Keyboard, Languages, type LucideIcon, Mic, MessageSquare, Sparkles, Volume2, Watch } from 'lucide-react';
import type { HearMode, PresetDef, Profile, TalkMode } from './types';

export interface Option<K extends string> {
  key: K;
  icon: LucideIcon;
}

export const TALK_OPTIONS: Option<TalkMode>[] = [
  { key: 'voice', icon: Mic },
  { key: 'type', icon: Keyboard },
  { key: 'replies', icon: MessageSquare },
  { key: 'help', icon: Sparkles },
];

export const HEAR_OPTIONS: Option<HearMode>[] = [
  { key: 'captions', icon: Captions },
  { key: 'clear', icon: Ear },
  { key: 'summary', icon: Bell },
  { key: 'vibe', icon: Watch },
  { key: 'translate', icon: Languages },
];

export const PRESET_ICONS: Record<string, LucideIcon> = {
  mute: Keyboard,
  deafspeak: Mic,
  deaftype: Captions,
  hoh: Ear,
  speech: AudioLines,
  lowread: Volume2,
};


/** Add or remove a mode. The list order is the user's priority; the first is the default. */
export function toggle<T extends string>(list: T[], key: T): T[] {
  if (list.includes(key)) return list.length > 1 ? list.filter((k) => k !== key) : list; // keep at least one
  return [...list, key];
}

export function applyPreset(profile: Profile, key: string, preset: PresetDef): Profile {
  return { ...profile, preset: key, talk_modes: [...preset.talk], hear_modes: [...preset.hear] };
}

/** Changing options by hand makes the profile custom (no preset). */
export function withModes(profile: Profile, patch: Partial<Pick<Profile, 'talk_modes' | 'hear_modes'>>): Profile {
  return { ...profile, ...patch, preset: null };
}

type T = (key: string, options?: Record<string, string>) => string;

/** One plain sentence describing the profile, in the app language. */
export function summary(p: Profile, t: T): string {
  const talk = (p.talk_modes ?? []).filter((k) => TALK_OPTIONS.some((o) => o.key === k)).map((k) => t(`talk.${k}.title`).toLowerCase());
  const hear = (p.hear_modes ?? []).filter((k) => HEAR_OPTIONS.some((o) => o.key === k)).map((k) => t(`hear.${k}.title`).toLowerCase());
  if (!talk[0]) return t('profile.chooseTalk');
  const also = talk.length > 1 ? t('profile.summaryAlso', { list: talk.slice(1).join(', ') }) : '';
  return t('profile.summary', { talk: talk[0], also, hear: hear.join(', ') || t('profile.summaryNone') });
}

/** Sensible defaults when someone picks a language: read captions in it, and type in it. */
export function withLanguage(profile: Profile, code: string): Profile {
  return { ...profile, app_lang: code, read_lang: code, type_lang: code === 'hi-Latn' ? 'hi-Latn' : code };
}

export const emptyProfile = (): Profile => ({
  display_name: '',
  preset: null,
  talk_modes: null,
  hear_modes: null,
  read_lang: 'hi',
  type_lang: 'hi-Latn',
  app_lang: 'en',
  easy_font: false,
  speech_rate: 0.75,
});
