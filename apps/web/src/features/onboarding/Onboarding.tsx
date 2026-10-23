import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../../components/Icons';
import { useMe, useSaveMe } from '../../hooks/useData';
import { emptyProfile } from '../../lib/profile';
import type { Profile } from '../../lib/types';
import { PresetChips, ProfileForm } from '../profile/ProfileForm';

export function Onboarding() {
  const nav = useNavigate();
  const me = useMe();
  const save = useSaveMe();
  const [step, setStep] = useState<1 | 2>(1);
  const [profile, setProfile] = useState<Profile>(emptyProfile());

  useEffect(() => {
    if (me.data?.onboarded) nav('/', { replace: true });
  }, [me.data, nav]);

  if (!me.data) return <div className="app"><div className="scroll"><p>Loading…</p></div></div>;
  const presets = me.data.presets;
  const ready = profile.display_name.trim().length > 0 && profile.preset !== null;

  function choose(p: Profile) {
    setProfile(p);
  }

  return (
    <div className="app">
      <div className="navtitle"><h4>{step === 1 ? 'Welcome to Awaaz' : 'Fine-tune'}</h4></div>
      <div className="scroll">
        {step === 1 ? (
          <>
            <p style={{ color: 'var(--ink-2)' }}>Phone calls for people who can’t hear or speak. Two quick questions.</p>
            <div className="cardx">
              <h5>What should we call you?</h5>
              <p style={{ color: 'var(--ink-2)', fontSize: '.85rem' }}>This name is said to the other person at the start of every call.</p>
              <input
                className="sel" style={{ width: '100%', font: 'inherit' }} autoFocus aria-label="Your name" placeholder="Your name"
                value={profile.display_name} onChange={(e) => choose({ ...profile, display_name: e.target.value })}
              />
            </div>
            <div className="cardx">
              <h5>How do you use the phone?</h5>
              <p style={{ color: 'var(--ink-2)', fontSize: '.85rem', marginBottom: '.7rem' }}>You can change every detail next, and later in Me.</p>
              <PresetChips value={profile} presets={presets} onChange={choose} />
            </div>
            <button className="cta" type="button" disabled={!ready} onClick={() => setStep(2)}>Continue <Icon name="chev" /></button>
          </>
        ) : (
          <>
            <ProfileForm value={profile} presets={presets} onChange={setProfile} />
            {save.isError && <p className="err" role="alert">Could not save. Please try again.</p>}
            <button className="cta" type="button" disabled={save.isPending} onClick={() => save.mutate(profile, { onSuccess: () => nav('/', { replace: true }) })}>
              <Icon name="check" /> Finish
            </button>
            <button className="cta soft" type="button" onClick={() => setStep(1)}>Back</button>
          </>
        )}
      </div>
    </div>
  );
}
