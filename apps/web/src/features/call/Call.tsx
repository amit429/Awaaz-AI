import { useEffect, useReducer, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import starterPhrases from '../../data/phrases.json';
import { useMe, usePhrases } from '../../hooks/useData';
import { applyEvent, initialState, SCAM_COPY, splitByEntities, type FeedItem } from '../../lib/feed';
import { RelayClient } from '../../lib/relay';

const STATUS_LABEL = {
  connecting: 'Connecting…',
  ringing: 'Calling…',
  connected: 'Connected',
  ended: 'Call ended',
  failed: 'Call failed',
} as const;

const starter = starterPhrases.filter((p) => !p.text.includes('{')); // address/number need profile data

function Them({ item }: { item: Extract<FeedItem, { kind: 'them' }> }) {
  return (
    <div className={item.partial ? 'them partial' : 'them'}>
      {splitByEntities(item.text, item.entities).map((p, i) =>
        p.entity ? (
          <button key={i} className="chip" type="button" aria-label={`${p.entity.type}: ${p.text}`}>{p.text}</button>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
      {item.translated && <span className="sub">{item.translated}</span>}
    </div>
  );
}

export function Call() {
  const { sessionId = '' } = useParams();
  const location = useLocation();
  const nav = useNavigate();
  const who = (location.state as { name?: string; number?: string } | null) ?? {};
  const [state, dispatch] = useReducer(applyEvent, initialState);
  const mine = usePhrases();
  const me = useMe();
  const canHelp = Boolean(me.data?.profile.talk_modes?.includes('help'));
  const [mode, setMode] = useState<'type' | 'help'>('type');
  const usablePhrases = mine.data && mine.data.length > 0 ? mine.data : starter;
  const [online, setOnline] = useState(false);
  const [text, setText] = useState('');
  const [sheet, setSheet] = useState<'phrases' | 'keypad' | null>(null);
  const [scamSeen, setScamSeen] = useState(false);
  const client = useRef<RelayClient | null>(null);
  const feedEnd = useRef<HTMLDivElement>(null);
  const lastTyping = useRef(0);

  useEffect(() => {
    const c = new RelayClient(sessionId, dispatch, setOnline);
    client.current = c;
    void c.connect();
    return () => c.close();
  }, [sessionId]);

  useEffect(() => {
    feedEnd.current?.scrollIntoView({ block: 'end' });
  }, [state.feed]);

  const preview = state.feed.find((i): i is Extract<FeedItem, { kind: 'preview' }> => i.kind === 'preview');
  const live = state.status === 'connected' || state.status === 'ringing';

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = text.trim();
    if (!v && preview) {
      client.current?.send({ t: 'say.confirm', preview_id: preview.id });
      return;
    }
    if (!v) return;
    if (mode === 'help') client.current?.send({ t: 'draft.request', words: v });
    else client.current?.send({ t: 'user.say', text: v, source: 'typed' });
    setText('');
  }

  function onType(v: string) {
    setText(v);
    if (Date.now() - lastTyping.current > 1500) {
      lastTyping.current = Date.now();
      client.current?.send({ t: 'user.typing' });
    }
  }

  const name = who.name ?? who.number ?? 'Call';
  const initials = name.replace(/[^\p{L}\s]/gu, '').split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase() || '#';

  return (
    <div className="app call">
      <div className="callbar">
        <button className="round dim" type="button" aria-label="Back" onClick={() => nav('/')}><Icon name="back" /></button>
        <span className="av">{initials}</span>
        <div className="who">
          <b>{name}</b>
          <small><span className="dot" style={{ background: live && online ? '#3DD68C' : '#9097A3' }} />{online ? STATUS_LABEL[state.status] : 'Reconnecting…'}</small>
        </div>
      </div>

      {state.scam && !scamSeen && state.status !== 'ended' && (
        <div className="alert" role="alert">
          <b><Icon name="shield" size="sm" />{(SCAM_COPY[state.scamReason ?? 'other'] ?? SCAM_COPY.other!).title}</b>
          <p>{(SCAM_COPY[state.scamReason ?? 'other'] ?? SCAM_COPY.other!).body}</p>
          <button type="button" onClick={() => client.current?.send({ t: 'call.end' })}>End call</button>
          <button type="button" className="o" onClick={() => setScamSeen(true)}>Continue</button>
        </div>
      )}

      <div className="feed" aria-live="polite">
        {state.feed.map((item, i) => {
          switch (item.kind) {
            case 'them':
              return <Them key={`t${item.turn}`} item={item} />;
            case 'you':
              return (
                <div key={`y${item.turn}`} className="you">
                  {item.text}
                  {item.original && <small>You typed: {item.original}</small>}
                </div>
              );
            case 'note':
              return <div key={item.id} className="note">{item.text}</div>;
            case 'draft':
              return (
                <div key={`d${item.id}`} className="draft">
                  <div className="h"><Icon name="spark" size="sm" />Drafted for you. Check it before it’s spoken</div>
                  <p>{item.text}</p>
                  {item.risk && <small style={{ color: '#FFAE3D' }}>Your words were a little unclear. Check this says what you mean.</small>}
                  <div className="b">
                    <button className="go" type="button" onClick={() => client.current?.send({ t: 'user.say', text: item.text, source: 'draft' })}>Say it</button>
                    <button className="no" type="button" onClick={() => { setMode('type'); setText(item.text); }}>Edit</button>
                  </div>
                </div>
              );
            case 'preview':
              return (
                <div key={`p${i}`} className="draft">
                  <div className="h"><Icon name="lang" size="sm" />Check before it’s spoken</div>
                  <p>{item.text}</p>
                  {item.original && <small style={{ opacity: 0.6 }}>You typed: {item.original}</small>}
                  <div className="b">
                    <button className="go" type="button" onClick={() => client.current?.send({ t: 'say.confirm', preview_id: item.id })}>Say it</button>
                    <button className="no" type="button" onClick={() => { setText(item.original ?? ''); }}>Edit</button>
                  </div>
                </div>
              );
          }
        })}
        <div ref={feedEnd} />
      </div>

      {state.suggestions.length > 0 && (
        <div className="replies">
          {state.suggestions.map((s) => (
            <button key={s} type="button" onClick={() => client.current?.send({ t: 'user.say', text: s, source: 'reply' })}>{s}</button>
          ))}
        </div>
      )}

      <div className="dock">
        {live && canHelp && (
          <div className="talkmode" role="group" aria-label="How you talk">
            <button type="button" aria-pressed={mode === 'type'} onClick={() => setMode('type')}><Icon name="keyboard" size="sm" />Type</button>
            <button type="button" aria-pressed={mode === 'help'} onClick={() => setMode('help')}><Icon name="spark" size="sm" />Help me say</button>
          </div>
        )}
        {live ? (
          <form className="compose" onSubmit={submit}>
            <input value={text} onChange={(e) => onType(e.target.value)} placeholder={mode === 'help' ? 'A few words, I’ll make a sentence' : 'Type, they hear it'} aria-label={mode === 'help' ? 'A few words' : 'Type a message'} autoFocus />
            <button className="round send" type="submit" aria-label={mode === 'help' ? 'Draft' : 'Speak'}><Icon name={mode === 'help' ? 'spark' : 'send'} /></button>
          </form>
        ) : (
          <button className="cta soft" type="button" onClick={() => nav('/')}>Back to calls</button>
        )}
        <div className="toolsrow">
          <button type="button" disabled={!live} onClick={() => setSheet('phrases')}><Icon name="chat" />Phrases</button>
          <button type="button" disabled={!live} onClick={() => setSheet('keypad')}><Icon name="grid" />Keypad</button>
          <button type="button" disabled={!live} onClick={() => client.current?.send({ t: 'user.ask_repeat' })}><Icon name="repeat" />Ask again</button>
          <button type="button" disabled={!live} style={{ color: '#FF6B6F' }} onClick={() => client.current?.send({ t: 'call.end' })}>
            <Icon name="phone" style={{ transform: 'rotate(135deg)' }} />End
          </button>
        </div>
      </div>

      <div className={sheet === 'phrases' ? 'sheet open' : 'sheet'}>
        <div className="grab" />
        <h5>Phrases <button type="button" onClick={() => setSheet(null)}>Done</button></h5>
        {usablePhrases.map((p) => (
          <button key={p.label + p.text} className="phr" type="button" onClick={() => { client.current?.send({ t: 'user.say', text: p.text, source: 'phrase' }); setSheet(null); }}>
            {p.label}<small>{p.text}</small>
          </button>
        ))}
      </div>

      <div className={sheet === 'keypad' ? 'sheet open' : 'sheet'}>
        <div className="grab" />
        <h5>Keypad <button type="button" onClick={() => setSheet(null)}>Done</button></h5>
        <div className="kp">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((d) => (
            <button key={d} type="button" onClick={() => client.current?.send({ t: 'user.dtmf', digits: d })}>{d}</button>
          ))}
        </div>
      </div>
    </div>
  );
}
