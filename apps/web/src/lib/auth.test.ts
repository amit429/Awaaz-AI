import { describe, expect, it } from 'vitest';
import { friendlyAuthError } from './auth';

describe('friendlyAuthError', () => {
  it('maps Supabase messages to translation keys', () => {
    expect(friendlyAuthError('Invalid login credentials')).toBe('authErrors.wrongPassword');
    expect(friendlyAuthError('Email not confirmed')).toBe('authErrors.notConfirmed');
    expect(friendlyAuthError('User already registered')).toBe('authErrors.exists');
    expect(friendlyAuthError('Password should be at least 6 characters.')).toBe('authErrors.shortPassword');
    expect(friendlyAuthError('email rate limit exceeded')).toBe('authErrors.tooMany');
    expect(friendlyAuthError('Unsupported provider: provider is not enabled')).toBe('authErrors.googleOff');
  });
  it('passes unknown messages through and never returns an empty string', () => {
    expect(friendlyAuthError('Network down')).toBe('Network down');
    expect(friendlyAuthError('')).toBe('authErrors.generic');
  });
});
