import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { useAddPhrase, useDeletePhrase, usePhrases } from '../../hooks/useData';

export function Phrases() {
  const phrases = usePhrases();
  const add = useAddPhrase();
  const del = useDeletePhrase();
  const [label, setLabel] = useState('');
  const [text, setText] = useState('');

  return (
    <div className="app">
      <div className="navtitle">
        <Link className="ib" to="/me" aria-label="Back" style={{ display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: '50%', background: 'var(--surface)', color: 'inherit' }}><Icon name="back" /></Link>
        <h4>My phrases</h4>
      </div>
      <div className="scroll">
        <form
          className="cardx"
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate({ label: label.trim(), text: text.trim() }, { onSuccess: () => { setLabel(''); setText(''); } });
          }}
        >
          <h5>Add a phrase</h5>
          <input className="sel" style={{ width: '100%', font: 'inherit', marginBottom: '.5rem' }} aria-label="Short name" placeholder="Short name, for example My address" value={label} onChange={(e) => setLabel(e.target.value)} />
          <input className="sel" style={{ width: '100%', font: 'inherit' }} aria-label="What is said" placeholder="What is said on the call" value={text} onChange={(e) => setText(e.target.value)} />
          {add.isError && <p className="err" role="alert">Could not save the phrase.</p>}
          <button className="cta" type="submit" style={{ marginTop: '.6rem' }} disabled={!label.trim() || !text.trim() || add.isPending}><Icon name="plus" /> Add</button>
        </form>
        <div className="group">
          {(phrases.data ?? []).length === 0 && <div className="rowi"><span className="tx"><small>No phrases yet. The call screen shows a starter set.</small></span></div>}
          {(phrases.data ?? []).map((p) => (
            <div key={p.id} className="rowi">
              <span className="tx"><b>{p.label}</b><small>{p.text}</small></span>
              <button className="ib" type="button" aria-label={`Delete ${p.label}`} onClick={() => del.mutate(p.id)} style={{ border: 0, background: 'transparent' }}><Icon name="x" size="sm" /></button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
