import { getToken } from './auth';
import { WS_BASE } from './config';
import type { ServerEvent } from './feed';

export type ClientEvent =
  | { t: 'user.typing' }
  | { t: 'user.say'; text: string; source: 'typed' | 'reply' | 'phrase' | 'draft' | 'voice'; preview_id?: string }
  | { t: 'say.confirm'; preview_id: string }
  | { t: 'draft.request'; words: string }
  | { t: 'say.prefetch'; text: string }
  | { t: 'read.set'; lang: string }
  | { t: 'user.ask_repeat' }
  | { t: 'user.dtmf'; digits: string }
  | { t: 'call.end' }
  | { t: 'ping' };

/** One WebSocket to the relay session, with reconnect and replay of missed turns. */
export class RelayClient {
  private ws: WebSocket | null = null;
  private lastTurn = 0;
  private closed = false;
  private retry = 0;
  private pingTimer: ReturnType<typeof setInterval> | undefined;

  constructor(
    private sessionId: string,
    private onEvent: (ev: ServerEvent) => void,
    private onConnection: (up: boolean) => void,
  ) {}

  async connect(): Promise<void> {
    const token = await getToken();
    const url = `${WS_BASE}/v1/relay/${this.sessionId}?token=${encodeURIComponent(token)}&last_turn=${this.lastTurn}`;
    const ws = new WebSocket(url);
    this.ws = ws;
    ws.onopen = () => {
      this.retry = 0;
      this.onConnection(true);
      this.pingTimer = setInterval(() => this.send({ t: 'ping' }), 15000);
    };
    ws.onmessage = (m) => {
      const ev = JSON.parse(String(m.data)) as ServerEvent;
      if ('turn' in ev && typeof ev.turn === 'number') this.lastTurn = Math.max(this.lastTurn, ev.turn);
      this.onEvent(ev);
    };
    ws.onclose = () => {
      clearInterval(this.pingTimer);
      this.onConnection(false);
      if (!this.closed && this.retry < 5) setTimeout(() => void this.connect(), Math.min(1000 * 2 ** this.retry++, 8000));
    };
  }

  send(ev: ClientEvent): void {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(ev));
  }

  close(): void {
    this.closed = true;
    clearInterval(this.pingTimer);
    this.ws?.close();
  }
}
