import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { TabBar } from '../../components/TabBar';
import { useCalls, useContacts } from '../../hooks/useData';
import { createCall } from '../../lib/api';
import { initials, maskNumber, STATUS_TEXT, when } from '../../lib/format';

const PRACTICE = [
  { name: 'Sharma Medical', detail: 'Practice call: pharmacy, Hindi', number: '+919800000001', callee: 'pharmacy' },
  { name: 'Netra Clinic', detail: 'Practice call: clinic, Marathi', number: '+919800000002', callee: 'clinic_mr' },
  { name: 'Unknown number', detail: 'Practice call: bank scam', number: '+919800000003', callee: 'bank_scam' },
];

export function Home() {
  const nav = useNavigate();
  const contacts = useContacts();
  const calls = useCalls();
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

  const favourites = (contacts.data ?? []).filter((c) => c.favourite);
  const recent = (calls.data ?? []).filter((c) => c.kind !== 'task').slice(0, 8);

  return (
    <div className="app">
      <div className="navtitle"><h4>Awaaz</h4></div>
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
          <form className="cardx" onSubmit={(e) => { e.preventDefault(); const n = number.length === 10 ? `+91${number}` : number; void start(n, n); }}>
            <h5>Who are you calling?</h5>
            <input className="sel" style={{ width: '100%', font: 'inherit' }} inputMode="tel" autoFocus placeholder="Phone number, for example 98765 43210" aria-label="Phone number" value={number} onChange={(e) => setNumber(e.target.value.replace(/[^\d+]/g, ''))} />
            <button className="cta" type="submit" disabled={busy || number.length < 8} style={{ marginTop: '.6rem' }}><Icon name="phone" /> Call</button>
          </form>
        )}
        {error && <p className="err" role="alert">{error}</p>}

        {favourites.length > 0 && (
          <>
            <div className="label">Favourites</div>
            <div className="group">
              {favourites.map((c) => (
                <button key={c.id} className="rowi" type="button" disabled={busy} onClick={() => void start(c.name, c.phone_e164)}>
                  <span className="av acc">{initials(c.name)}</span>
                  <span className="tx"><b>{c.name}</b><small>{c.notes || c.phone_e164}</small></span>
                  <Icon name="chev" size="sm" style={{ color: 'var(--ink-3)' }} />
                </button>
              ))}
            </div>
          </>
        )}

        {recent.length > 0 && (
          <>
            <div className="label">Recent</div>
            <div className="group">
              {recent.map((c) => (
                <button key={c.id} className="rowi" type="button" onClick={() => nav(`/calls/${c.id}`)}>
                  <span className="av">{initials(c.name ?? 'Unknown')}</span>
                  <span className="tx"><b>{c.name ?? maskNumber(c.other_number)}</b><small>{when(c.created_at)} · {STATUS_TEXT[c.status] ?? c.status}</small></span>
                  <Icon name="chev" size="sm" style={{ color: 'var(--ink-3)' }} />
                </button>
              ))}
            </div>
          </>
        )}

        <div className="label">Practice calls</div>
        <div className="group">
          {PRACTICE.map((c) => (
            <button key={c.number} className="rowi" type="button" disabled={busy} onClick={() => void start(c.name, c.number, c.callee)}>
              <span className="av">{initials(c.name)}</span>
              <span className="tx"><b>{c.name}</b><small>{c.detail}</small></span>
              <Icon name="chev" size="sm" style={{ color: 'var(--ink-3)' }} />
            </button>
          ))}
        </div>
      </div>
      <TabBar />
    </div>
  );
}
