export type TalkMode = 'voice' | 'type' | 'replies' | 'help' | 'clarity' | 'sign';
export type HearMode = 'captions' | 'clear' | 'audio' | 'summary' | 'vibe' | 'translate';

export interface Profile {
  display_name: string;
  preset: string | null;
  talk_modes: TalkMode[] | null;
  hear_modes: HearMode[] | null;
  read_lang: string;
  type_lang: string;
  app_lang: string;
  easy_font: boolean;
  speech_rate: number;
}

export interface PresetDef {
  label: string;
  talk: TalkMode[];
  hear: HearMode[];
  disability_phrase: string;
}

export interface Me {
  onboarded: boolean;
  profile: Profile;
  presets: Record<string, PresetDef>;
}

export interface Contact {
  id: string;
  name: string;
  phone_e164: string;
  call_lang?: string | null;
  notes?: string | null;
  favourite: boolean;
}

export interface Phrase {
  id: string;
  label: string;
  text: string;
  group_name?: string | null;
}

export interface CallRow {
  id: string;
  name: string | null;
  other_number: string;
  kind?: string;
  status: string;
  created_at: string;
  call_lang: string | null;
  duration_s: number | null;
}

export interface Turn {
  seq: number;
  speaker: 'other' | 'user' | 'system';
  source: string;
  text: string;
  entities?: { type: string; text: string; start?: number; end?: number }[];
  t_ms: number;
}
