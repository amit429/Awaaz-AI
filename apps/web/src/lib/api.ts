import { getToken } from './auth';
import { API_BASE } from './config';

export interface CreatedCall {
  session_id: string;
  ws_url: string;
}

export async function createCall(to: string, callee?: string): Promise<CreatedCall> {
  const res = await fetch(`${API_BASE}/calls`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${await getToken()}` },
    body: JSON.stringify({ to, callee }),
  });
  if (!res.ok) throw new Error(res.status === 422 ? 'Check the phone number' : 'Could not start the call');
  return (await res.json()) as CreatedCall;
}
