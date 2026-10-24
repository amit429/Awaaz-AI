import { describe, expect, it } from 'vitest';
import { friendlyAuthError } from './auth';

describe('friendlyAuthError', () => {
  it('turns Supabase messages into plain language', () => {
    expect(friendlyAuthError('Invalid login credentials')).toBe('Wrong email or password.');
    expect(friendlyAuthError('Email not confirmed')).toContain('confirm your email');
    expect(friendlyAuthError('User already registered')).toContain('already has an account');
    expect(friendlyAuthError('Password should be at least 6 characters.')).toContain('at least 6');
    expect(friendlyAuthError('email rate limit exceeded')).toContain('Too many tries');
    expect(friendlyAuthError('Unsupported provider: provider is not enabled')).toContain('isn’t switched on');
  });
  it('passes unknown messages through and never returns an empty string', () => {
    expect(friendlyAuthError('Network down')).toBe('Network down');
    expect(friendlyAuthError('')).toContain('Something went wrong');
  });
});
