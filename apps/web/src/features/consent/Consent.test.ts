import { describe, expect, it } from 'vitest';
import { normalisePhone } from './Consent';

describe('normalisePhone', () => {
  it('adds +91 to a ten-digit Indian mobile number', () => {
    expect(normalisePhone('98227 90187')).toBe('+919822790187');
    expect(normalisePhone('(98227) 90187')).toBe('+919822790187');
  });
  it('keeps a number that already has its country code', () => {
    expect(normalisePhone('+91 98227 90187')).toBe('+919822790187');
    expect(normalisePhone('+14155550123')).toBe('+14155550123');
  });
  it('rejects anything else', () => {
    expect(normalisePhone('12345')).toBeNull();
    expect(normalisePhone('abc')).toBeNull();
    expect(normalisePhone('5822790187')).toBeNull(); // not an Indian mobile start digit, no country code
  });
});
