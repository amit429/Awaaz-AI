import { getToken } from './auth';
import { API_BASE } from './config';
import type { CallRow, CallSummary, Contact, Me, Phrase, Profile, Turn } from './types';

export interface CreatedCall {
  session_id: string;
  ws_url: string;
}

/** Bump when what the app collects changes, so people are asked again. */
export const CONSENT_VERSION = '2026-10';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      Authorization: `Bearer ${await getToken()}`,
      ...init.headers,
    },
  });
  if (!res.ok) {
    let detail = '';
    try {
      const body = (await res.json()) as { detail?: unknown };
      detail = typeof body.detail === 'string' ? body.detail : '';
    } catch {
      /* no body */
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const send = (method: string, body?: unknown): RequestInit => ({ method, body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  me: () => request<Me>('/me'),
  consent: (phone?: string) => request<Me>('/consent', send('POST', { version: CONSENT_VERSION, phone: phone || undefined })),
  saveMe: (p: Profile) => request<Me>('/me', send('PUT', p)),
  contacts: () => request<Contact[]>('/contacts'),
  saveContact: (c: Omit<Contact, 'id'>, id?: string) =>
    request<Contact>(id ? `/contacts/${id}` : '/contacts', send(id ? 'PUT' : 'POST', c)),
  deleteContact: (id: string) => request<void>(`/contacts/${id}`, send('DELETE')),
  phrases: () => request<Phrase[]>('/phrases'),
  addPhrase: (p: Omit<Phrase, 'id'>) => request<Phrase>('/phrases', send('POST', p)),
  deletePhrase: (id: string) => request<void>(`/phrases/${id}`, send('DELETE')),
  calls: () => request<CallRow[]>('/calls?limit=200'),
  call: (id: string) => request<{ call: CallRow; turns: Turn[] }>(`/calls/${id}`),
  createCall: (to: string, callee?: string, language?: string) => request<CreatedCall>('/calls', send('POST', { to, callee, call_language: language })),
  transcribe: async (audio: Blob, lang: string) => {
    const form = new FormData();
    form.append('audio', audio, 'voice.webm');
    form.append('lang', lang);
    return request<{ text: string }>('/text/transcribe', { method: 'POST', body: form });
  },
  callSummary: (id: string) => request<CallSummary>(`/calls/${id}/summary`),
  transliterate: (text: string, to: string) => request<{ text: string }>('/text/transliterate', send('POST', { text, to })),
};

export async function createCall(to: string, callee?: string, language?: string): Promise<CreatedCall> {
  try {
    return await api.createCall(to, callee, language);
  } catch (e) {
    if (e instanceof ApiError && e.status === 422) throw new Error('home.checkNumber');
    throw e instanceof ApiError && e.message ? e : new Error('home.couldNotStart');
  }
}
