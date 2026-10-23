import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { api } from '../../lib/api';
import { maskNumber, STATUS_TEXT, when } from '../../lib/format';
import { splitByEntities } from '../../lib/feed';

export function CallDetail() {
  const { id = '' } = useParams();
  const q = useQuery({ queryKey: ['call', id], queryFn: () => api.call(id) });
  const call = q.data?.call;

  return (
    <div className="app">
      <div className="navtitle">
        <Link to="/" aria-label="Back" style={{ display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: '50%', background: 'var(--surface)', color: 'inherit' }}><Icon name="back" /></Link>
        <h4>{call?.name ?? (call ? maskNumber(call.other_number) : 'Call')}</h4>
      </div>
      <div className="scroll">
        {q.isLoading && <p>Loading…</p>}
        {q.isError && <p className="err" role="alert">Could not load this call.</p>}
        {call && (
          <>
            <div className="cardx">
              <dl className="kv">
                <dt>When</dt><dd>{when(call.created_at)}</dd>
                <dt>Number</dt><dd>{maskNumber(call.other_number)}</dd>
                <dt>Result</dt><dd>{STATUS_TEXT[call.status] ?? call.status}</dd>
              </dl>
            </div>
            <div className="label">Transcript</div>
            <div className="cardx" style={{ display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
              {(q.data?.turns ?? []).length === 0 && <small>Nothing was said on this call.</small>}
              {(q.data?.turns ?? []).map((t) => (
                <div key={t.seq} style={{ alignSelf: t.speaker === 'other' ? 'flex-start' : 'flex-end', maxWidth: '88%', background: t.speaker === 'other' ? 'var(--surface-2)' : 'var(--accent-soft)', color: t.speaker === 'user' || t.speaker === 'system' ? 'var(--accent-ink)' : 'inherit', borderRadius: 14, padding: '.45rem .7rem' }}>
                  <small style={{ display: 'block', opacity: 0.65 }}>{t.speaker === 'other' ? 'Them' : t.source === 'disclosure' ? 'Awaaz (opening line)' : t.source === 'keeper' ? 'Awaaz (please hold)' : 'You'}</small>
                  {splitByEntities(t.text, (t.entities ?? []) as never).map((p, i) => (p.entity ? <b key={i} className="chip">{p.text}</b> : <span key={i}>{p.text}</span>))}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
