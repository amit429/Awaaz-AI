import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { TabBar } from '../../components/TabBar';
import { useMe, useSaveMe } from '../../hooks/useData';
import type { Profile } from '../../lib/types';
import { ProfileForm } from './ProfileForm';

export function Me() {
  const me = useMe();
  const save = useSaveMe();
  const [draft, setDraft] = useState<Profile | null>(null);

  useEffect(() => {
    if (me.data && !draft) setDraft(me.data.profile);
  }, [me.data, draft]);

  const dirty = draft && me.data && JSON.stringify(draft) !== JSON.stringify(me.data.profile);

  return (
    <div className="app">
      <div className="navtitle"><h4>How I talk and hear</h4></div>
      <div className="scroll">
        {me.data && draft ? (
          <>
            <div className="cardx">
              <h5>Name</h5>
              <input className="sel" style={{ width: '100%', font: 'inherit' }} aria-label="Your name" value={draft.display_name} onChange={(e) => setDraft({ ...draft, display_name: e.target.value })} />
            </div>
            <div className="cardx"><ProfileForm value={draft} presets={me.data.presets} onChange={setDraft} /></div>
            <div className="group">
              <Link className="rowi" to="/me/phrases" style={{ textDecoration: 'none', color: 'inherit' }}>
                <span className="av"><Icon name="chat" /></span><span className="tx"><b>My phrases</b><small>Quick things to say on calls</small></span>
                <Icon name="chev" size="sm" style={{ color: 'var(--ink-3)' }} />
              </Link>
            </div>
            {save.isError && <p className="err" role="alert">Could not save. Please try again.</p>}
            <button className="cta" type="button" disabled={!dirty || save.isPending || !draft.display_name.trim()} onClick={() => save.mutate(draft)}>
              <Icon name="check" /> {save.isSuccess && !dirty ? 'Saved' : 'Save changes'}
            </button>
          </>
        ) : <p>Loading…</p>}
      </div>
      <TabBar />
    </div>
  );
}
