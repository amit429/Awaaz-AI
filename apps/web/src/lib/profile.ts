import { AudioLines, Bell, Captions, Ear, Hand, Keyboard, Languages, type LucideIcon, Mic, MessageSquare, Sparkles, Volume2, Watch } from 'lucide-react';
import type { HearMode, PresetDef, Profile, TalkMode } from './types';

export interface Option<K extends string> {
  key: K;
  icon: LucideIcon;
  title: string;
  hint: string;
  tag?: string;
  soon?: boolean; // shown, but not built yet
}

export const TALK_OPTIONS: Option<TalkMode>[] = [
  { key: 'voice', icon: Mic, title: 'My own voice', hint: 'I speak; they hear me directly.', soon: true },
  { key: 'type', icon: Keyboard, title: 'Type, Awaaz speaks', hint: 'In a voice I pick.' },
  { key: 'replies', icon: MessageSquare, title: 'Phrases and smart replies', hint: 'One tap answers.' },
  { key: 'help', icon: Sparkles, title: 'Help me say it', hint: 'A few words in, a clear sentence out. I approve first.', soon: true },
  { key: 'clarity', icon: AudioLines, title: 'Speak clearly for me', hint: 'I talk; Awaaz re-says it clearly.', tag: 'Later', soon: true },
  { key: 'sign', icon: Hand, title: 'Sign language', hint: 'Connect a human ISL interpreter by video.', tag: 'Partner service', soon: true },
];

export const HEAR_OPTIONS: Option<HearMode>[] = [
  { key: 'captions', icon: Captions, title: 'Live captions', hint: 'Big text, numbers highlighted.' },
  { key: 'clear', icon: Ear, title: 'Clear voice', hint: 'Each sentence repeated slower and louder.', soon: true },
  { key: 'audio', icon: Volume2, title: 'Normal audio', hint: 'Straight through, boosted for speech.', soon: true },
  { key: 'summary', icon: Bell, title: 'Spoken summary after', hint: 'What was agreed, as a voice note.', soon: true },
  { key: 'vibe', icon: Watch, title: 'Vibration cues', hint: 'Phone buzzes when they start and stop talking.', soon: true },
  { key: 'translate', icon: Languages, title: 'Translate for me', hint: 'Read and type in my language, whatever they speak.' },
];

export const PRESET_ICONS: Record<string, LucideIcon> = {
  mute: Keyboard,
  deafspeak: Mic,
  deaftype: Captions,
  hoh: Ear,
  speech: AudioLines,
  lowread: Volume2,
};

export const READ_LANGS = [
  ['hi', 'Hindi'], ['en', 'English'], ['mr', 'Marathi'], ['ta', 'Tamil'], ['bn', 'Bengali'],
  ['te', 'Telugu'], ['kn', 'Kannada'], ['ml', 'Malayalam'], ['gu', 'Gujarati'], ['pa', 'Punjabi'],
] as const;

export const TYPE_LANGS = [
  ['hi-Latn', 'Hindi in English letters'], ['hi', 'Hindi'], ['en', 'English'], ['mr', 'Marathi'],
] as const;

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

const title = <K extends string>(options: Option<K>[], key: K) => options.find((o) => o.key === key)?.title ?? key;

export function summary(p: Profile): string {
  const talk = (p.talk_modes ?? []).map((k) => title(TALK_OPTIONS, k));
  const hear = (p.hear_modes ?? []).map((k) => title(HEAR_OPTIONS, k));
  const first = talk[0] ? `You talk with: ${talk[0].toLowerCase()}` : 'Choose how you talk';
  const more = talk.length > 1 ? ` (also ${talk.slice(1).join(', ').toLowerCase()})` : '';
  return `${first}${more}. You hear with: ${hear.join(', ').toLowerCase() || 'nothing selected'}.`;
}

export const emptyProfile = (): Profile => ({
  display_name: '',
  preset: null,
  talk_modes: null,
  hear_modes: null,
  read_lang: 'hi',
  type_lang: 'hi-Latn',
  easy_font: false,
  speech_rate: 0.75,
});
