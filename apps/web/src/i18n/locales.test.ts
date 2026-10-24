import { describe, expect, it } from 'vitest';
import en from './locales/en.json';

const files = import.meta.glob('./locales/*.json', { eager: true, import: 'default' }) as Record<string, Record<string, unknown>>;

function flat(o: Record<string, unknown>, prefix = ''): Record<string, string> {
  return Object.entries(o).reduce<Record<string, string>>((acc, [k, v]) => {
    if (v && typeof v === 'object') Object.assign(acc, flat(v as Record<string, unknown>, `${prefix}${k}.`));
    else acc[`${prefix}${k}`] = String(v);
    return acc;
  }, {});
}
const holes = (s: string) => (s.match(/\{\{\w+\}\}/g) ?? []).sort().join();

describe('locale files', () => {
  const base = flat(en);
  for (const [path, data] of Object.entries(files)) {
    if (path.endsWith('/en.json')) continue;
    it(`${path} has the same keys and placeholders as English`, () => {
      const got = flat(data);
      expect(Object.keys(got).sort()).toEqual(Object.keys(base).sort());
      for (const k of Object.keys(base)) expect(holes(got[k] ?? ''), k).toBe(holes(base[k] ?? ''));
    });
  }
});
