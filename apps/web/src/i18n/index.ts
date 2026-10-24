import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';

/** Languages Awaaz speaks to its users. Codes match the API (hi-Latn is Hinglish). */
export const LANGUAGES = [
  { code: 'en', native: 'English', english: 'English' },
  { code: 'hi', native: 'हिन्दी', english: 'Hindi' },
  { code: 'hi-Latn', native: 'Hinglish', english: 'Hindi in English letters' },
  { code: 'mr', native: 'मराठी', english: 'Marathi' },
  { code: 'bn', native: 'বাংলা', english: 'Bengali' },
  { code: 'ta', native: 'தமிழ்', english: 'Tamil' },
  { code: 'te', native: 'తెలుగు', english: 'Telugu' },
  { code: 'kn', native: 'ಕನ್ನಡ', english: 'Kannada' },
  { code: 'gu', native: 'ગુજરાતી', english: 'Gujarati' },
  { code: 'pa', native: 'ਪੰਜਾਬੀ', english: 'Punjabi' },
  { code: 'ml', native: 'മലയാളം', english: 'Malayalam' },
  { code: 'or', native: 'ଓଡ଼ିଆ', english: 'Odia' },
] as const;

export type LangCode = (typeof LANGUAGES)[number]['code'];
/** Languages the other person can speak on a call (Hinglish is a way of writing, not speaking). */
export const SPOKEN = LANGUAGES.filter((l) => l.code !== 'hi-Latn');

export const nativeName = (code: string) => LANGUAGES.find((l) => l.code === code)?.native ?? code;
export const isLangCode = (code: string | null | undefined): code is LangCode => LANGUAGES.some((l) => l.code === code);

const loaders = import.meta.glob<{ default: Record<string, unknown> }>('./locales/*.json');
const STORAGE_KEY = 'awaaz-lang';

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en } },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false }, // React already escapes
  returnNull: false,
});

/** Load a language's strings on first use, switch to it, and remember it for the sign-in screen. */
export async function setAppLanguage(code: string): Promise<void> {
  const lang = isLangCode(code) ? code : 'en';
  if (!i18n.hasResourceBundle(lang, 'translation')) {
    const load = loaders[`./locales/${lang}.json`];
    if (load) i18n.addResourceBundle(lang, 'translation', (await load()).default);
  }
  await i18n.changeLanguage(lang);
  document.documentElement.lang = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* storage unavailable: the choice just won't be remembered before sign-in */
  }
}

/** The language remembered from last time, or one matching the browser, before anyone signs in. */
export function initialLanguage(): LangCode {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isLangCode(saved)) return saved;
  } catch {
    /* ignore */
  }
  const browser = (navigator.language || 'en').split('-')[0];
  return isLangCode(browser) ? browser : 'en';
}

export default i18n;
