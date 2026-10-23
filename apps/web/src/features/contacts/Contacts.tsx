import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { TabBar } from '../../components/TabBar';
import { useContacts, useDeleteContact, useSaveContact } from '../../hooks/useData';
import { createCall } from '../../lib/api';
import { initials } from '../../lib/format';
import type { Contact } from '../../lib/types';

type Draft = Omit<Contact, 'id'> & { id?: string };
const blank: Draft = { name: '', phone_e164: '', call_lang: 'hi', notes: '', favourite: false };

const normalise = (raw: string) => {
  const d = raw.replace(/[^\d+]/g, '');
  if (d.startsWith('+')) return d;
  return d.length === 10 ? `+91${d}` : d.startsWith('91') && d.length === 12 ? `+${d}` : d;
};

export function Contacts() {
  const nav = useNavigate();
  const contacts = useContacts();
  const save = useSaveContact();
  const del = useDeleteContact();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState('');

  async function call(c: Contact) {
    setError('');
    try {
      const made = await createCall(c.phone_e164);
      nav(`/call/${made.session_id}`, { state: { name: c.name, number: c.phone_e164 } });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start the call');
    }
  }

  const valid = draft && draft.name.trim() && /^\+[1-9]\d{7,14}$/.test(normalise(draft.phone_e164));

  return (
    <div className="app">
      <div className="navtitle">
        <h4>Contacts</h4>
        <button className="ib" type="button" aria-label="Add contact" onClick={() => setDraft({ ...blank })}><Icon name="plus" /></button>
      </div>
      <div className="scroll">
        {draft && (
          <form
            className="cardx"
            onSubmit={(e) => {
              e.preventDefault();
              if (!valid) return;
              const { id, ...rest } = draft;
              save.mutate({ id, contact: { ...rest, phone_e164: normalise(rest.phone_e164), notes: rest.notes || null } }, { onSuccess: () => setDraft(null) });
            }}
          >
            <h5>{draft.id ? 'Edit contact' : 'New contact'}</h5>
            <input className="sel" style={{ width: '100%', font: 'inherit', marginBottom: '.5rem' }} aria-label="Name" placeholder="Name" autoFocus value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
            <input className="sel" style={{ width: '100%', font: 'inherit', marginBottom: '.5rem' }} aria-label="Phone number" inputMode="tel" placeholder="Phone number" value={draft.phone_e164} onChange={(e) => setDraft({ ...draft, phone_e164: e.target.value })} />
            <input className="sel" style={{ width: '100%', font: 'inherit', marginBottom: '.5rem' }} aria-label="Notes" placeholder="Notes Awaaz may use, for example: my BP medicine is Telma 40" value={draft.notes ?? ''} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} />
            <div className="toggle"><span>Favourite</span><button className="sw" type="button" role="switch" aria-checked={draft.favourite} aria-label="Favourite" onClick={() => setDraft({ ...draft, favourite: !draft.favourite })} /></div>
            {save.isError && <p className="err" role="alert">Could not save. Check the number.</p>}
            <div className="two">
              <button className="cta" type="submit" disabled={!valid || save.isPending}>Save</button>
              <button className="cta soft" type="button" onClick={() => setDraft(null)}>Cancel</button>
            </div>
          </form>
        )}
        {error && <p className="err" role="alert">{error}</p>}
        <div className="group">
          {contacts.data?.length === 0 && !draft && <div className="rowi"><span className="tx"><small>No contacts yet. Tap + to add one.</small></span></div>}
          {(contacts.data ?? []).map((c) => (
            <div key={c.id} className="rowi">
              <span className={c.favourite ? 'av acc' : 'av'}>{initials(c.name)}</span>
              <span className="tx"><b>{c.name}</b><small>{c.notes || c.phone_e164}</small></span>
              <button className="ib" type="button" aria-label={`Edit ${c.name}`} style={{ border: 0, background: 'transparent' }} onClick={() => setDraft({ ...c })}><Icon name="sliders" size="sm" /></button>
              <button className="ib" type="button" aria-label={`Delete ${c.name}`} style={{ border: 0, background: 'transparent' }} onClick={() => del.mutate(c.id)}><Icon name="x" size="sm" /></button>
              <button className="round send" type="button" aria-label={`Call ${c.name}`} onClick={() => void call(c)}><Icon name="phone" /></button>
            </div>
          ))}
        </div>
      </div>
      <TabBar />
    </div>
  );
}
