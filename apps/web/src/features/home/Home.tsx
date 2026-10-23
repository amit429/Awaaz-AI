import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { createCall } from '../../lib/api';

interface Contact {
  name: string;
  detail: string;
  number: string;
  callee: string; // practice caller from specs/fixtures (mock mode)
}

const PRACTICE: Contact[] = [
  { name: 'Sharma Medical', detail: 'Practice call: pharmacy, Hindi', number: '+919800000001', callee: 'pharmacy' },
  { name: 'Netra Clinic', detail: 'Practice call: clinic, Marathi', number: '+919800000002', callee: 'clinic_mr' },
  { name: 'Unknown number', detail: 'Practice call: bank scam', number: '+919800000003', callee: 'bank_scam' },
];

const initials = (name: string) =>
  name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

export function Home() {
  const nav = useNavigate();
  const [number, setNumber] = useState('');
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function start(name: string, to: string, callee?: string) {
    setBusy(true);
    setError('');
    try {
      const call = await createCall(to, callee);
      nav(`/call/${call.session_id}`, { state: { name, number: to } });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start the call');
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <div className="navtitle">
        <h4>Awaaz</h4>
      </div>
      <div className="scroll">
        <div className="hero-actions">
          <button className="qa primary" type="button" onClick={() => setAsking(true)}>
            <span className="ic"><Icon name="phone" /></span>
            <span><b>New call</b><small>Type, talk or let AI help</small></span>
          </button>
          <button className="qa" type="button" disabled title="Coming soon">
            <span className="ic"><Icon name="bot" /></span>
            <span><b>Call for me</b><small>Coming soon</small></span>
          </button>
        </div>

        {asking && (
          <form
            className="cardx"
            onSubmit={(e) => {
              e.preventDefault();
              void start(number, number.startsWith('+') ? number : `+91${number}`);
            }}
          >
            <h5>Who are you calling?</h5>
            <input
              className="sel"
              style={{ width: '100%', font: 'inherit' }}
              inputMode="tel"
              autoFocus
              placeholder="Phone number, for example 98765 43210"
              aria-label="Phone number"
              value={number}
              onChange={(e) => setNumber(e.target.value.replace(/[^\d+]/g, ''))}
            />
            <button className="cta" type="submit" disabled={busy || number.length < 8} style={{ marginTop: '.6rem' }}>
              <Icon name="phone" /> Call
            </button>
          </form>
        )}
        {error && <p className="err" role="alert">{error}</p>}

        <div className="label">Practice calls</div>
        <div className="group">
          {PRACTICE.map((c, i) => (
            <button key={c.number} className="rowi" type="button" disabled={busy} onClick={() => void start(c.name, c.number, c.callee)}>
              <span className={i === 0 ? 'av acc' : 'av'}>{initials(c.name)}</span>
              <span className="tx"><b>{c.name}</b><small>{c.detail}</small></span>
              <Icon name="chev" size="sm" style={{ color: 'var(--ink-3)' }} />
            </button>
          ))}
        </div>
      </div>
      <div className="tabbar">
        <span className="on"><Icon name="phone" />Calls</span>
        <span><Icon name="bot" />Tasks</span>
        <span><Icon name="people" />Face to face</span>
        <span><Icon name="user" />Me</span>
      </div>
    </div>
  );
}
