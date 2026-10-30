import { describe, expect, it } from 'vitest';
import { initials, maskNumber, when } from './format';

describe('format', () => {
  it('initials from Latin and Devanagari names', () => {
    expect(initials('Sharma Medical')).toBe('SM');
    expect(initials('शर्मा मेडिकल')).toBe('शम');
    expect(initials('  ')).toBe('#');
  });
  it('shows times in IST', () => {
    expect(when('2026-10-24T08:30:00Z')).toMatch(/2:00/); // 08:30 UTC is 14:00 IST
  });
  it('masks phone numbers to the last four digits', () => {
    expect(maskNumber('+919876543210')).toBe('••••3210');
  });
});

describe('duration', () => {
  it('reads naturally from seconds to hours', async () => {
    const { duration } = await import('./format');
    expect(duration(0)).toBe('0 s');
    expect(duration(45)).toBe('45 s');
    expect(duration(60)).toBe('1 min');
    expect(duration(185)).toBe('3 min');
    expect(duration(3600)).toBe('1 h');
    expect(duration(3900)).toBe('1 h 5 min');
    expect(duration(null)).toBe('—');
  });
});
