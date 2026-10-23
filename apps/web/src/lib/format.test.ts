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
