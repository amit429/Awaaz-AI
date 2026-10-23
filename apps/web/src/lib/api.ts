import { getToken } from './auth';
import { API_BASE } from './config';
import type { CallRow, Contact, Me, Phrase, Profile, Turn } from './types';

export interface CreatedCall {
  session_id: string;
  ws_url: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${await getToken()}`, ...init.headers },
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
  saveMe: (p: Profile) => request<Me>('/me', send('PUT', p)),
  contacts: () => request<Contact[]>('/contacts'),
  saveContact: (c: Omit<Contact, 'id'>, id?: string) =>
    request<Contact>(id ? `/contacts/${id}` : '/contacts', send(id ? 'PUT' : 'POST', c)),
  deleteContact: (id: string) => request<void>(`/contacts/${id}`, send('DELETE')),
  phrases: () => request<Phrase[]>('/phrases'),
  addPhrase: (p: Omit<Phrase, 'id'>) => request<Phrase>('/phrases', send('POST', p)),
  deletePhrase: (id: string) => request<void>(`/phrases/${id}`, send('DELETE')),
  calls: () => request<CallRow[]>('/calls'),
  call: (id: string) => request<{ call: CallRow; turns: Turn[] }>(`/calls/${id}`),
  createCall: (to: string, callee?: string) => request<CreatedCall>('/calls', send('POST', { to, callee })),
};

export async function createCall(to: string, callee?: string): Promise<CreatedCall> {
  try {
    return await api.createCall(to, callee);
  } catch (e) {
    if (e instanceof ApiError && e.status === 422) throw new Error('Check the phone number');
    throw e instanceof ApiError && e.message ? e : new Error('Could not start the call');
  }
}
