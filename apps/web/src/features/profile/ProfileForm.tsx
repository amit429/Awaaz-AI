import { Icon } from '../../components/Icons';
import {
  applyPreset, HEAR_OPTIONS, PRESET_ICONS, READ_LANGS, summary, TALK_OPTIONS, toggle, TYPE_LANGS, withModes, type Option,
} from '../../lib/profile';
import type { HearMode, PresetDef, Profile, TalkMode } from '../../lib/types';

function Options<K extends string>({ options, selected, onToggle }: { options: Option<K>[]; selected: K[]; onToggle: (k: K) => void }) {
  return (
    <div className="opts">
      {options.map((o) => (
        <button key={o.key} className="opt" type="button" aria-pressed={selected.includes(o.key)} onClick={() => onToggle(o.key)}>
          <span className="ic"><Icon name={o.icon} /></span>
          <span>
            <b>{o.title}</b>
            <small>{o.hint}</small>
            {(o.soon || o.tag) && <span className="tag">{o.tag ?? 'Coming soon'}</span>}
            {selected[0] === o.key && selected.length > 1 && <span className="tag">Default</span>}
          </span>
        </button>
      ))}
    </div>
  );
}

export function PresetChips({ value, presets, onChange }: { value: Profile; presets: Record<string, PresetDef>; onChange: (p: Profile) => void }) {
  return (
    <div className="presets">
      {Object.entries(presets).map(([key, def]) => (
        <button key={key} type="button" aria-pressed={value.preset === key} onClick={() => onChange(applyPreset(value, key, def))}>
          <Icon name={PRESET_ICONS[key] ?? 'user'} size="sm" />
          {def.label}
        </button>
      ))}
    </div>
  );
}

export function ProfileForm({ value, presets, onChange }: { value: Profile; presets: Record<string, PresetDef>; onChange: (p: Profile) => void }) {
  const talk = value.talk_modes ?? [];
  const hear = value.hear_modes ?? [];
  return (
    <div>
      <h3>Start from</h3>
      <p className="sub" style={{ color: 'var(--ink-2)', fontSize: '.88rem', margin: '.2rem 0 .9rem' }}>A preset only sets defaults.</p>
      <PresetChips value={value} presets={presets} onChange={onChange} />

      <h3>How I talk</h3>
      <p className="sub" style={{ color: 'var(--ink-2)', fontSize: '.88rem', margin: '.2rem 0 .9rem' }}>Choose all that you use. The first one is your default.</p>
      <Options<TalkMode> options={TALK_OPTIONS} selected={talk} onToggle={(k) => onChange(withModes(value, { talk_modes: toggle(talk, k) }))} />

      <h3>How I hear them</h3>
      <p className="sub" style={{ color: 'var(--ink-2)', fontSize: '.88rem', margin: '.2rem 0 .9rem' }}>Mix freely, for example captions and clear voice together.</p>
      <Options<HearMode> options={HEAR_OPTIONS} selected={hear} onToggle={(k) => onChange(withModes(value, { hear_modes: toggle(hear, k) }))} />

      <h3>Languages</h3>
      <div className="row2" style={{ marginTop: '.6rem' }}>
        <div className="sel">
          <label htmlFor="lr">I read</label>
          <select id="lr" value={value.read_lang} onChange={(e) => onChange({ ...value, read_lang: e.target.value })}>
            {READ_LANGS.map(([k, n]) => <option key={k} value={k}>{n}</option>)}
          </select>
        </div>
        <div className="sel">
          <label htmlFor="lt">I type</label>
          <select id="lt" value={value.type_lang} onChange={(e) => onChange({ ...value, type_lang: e.target.value })}>
            {TYPE_LANGS.map(([k, n]) => <option key={k} value={k}>{n}</option>)}
          </select>
        </div>
      </div>

      <div style={{ marginTop: '1rem' }}>
        <div className="toggle">
          <span>Use the easy-reading font</span>
          <button className="sw" type="button" role="switch" aria-checked={value.easy_font} aria-label="Easy-reading font" onClick={() => onChange({ ...value, easy_font: !value.easy_font })} />
        </div>
        <div className="toggle">
          <span>Tell the other person I’m using an assistant</span>
          <button className="sw" type="button" role="switch" aria-checked="true" aria-label="Disclosure" disabled />
        </div>
      </div>
      <div className="summary" aria-live="polite">{summary(value)}</div>
    </div>
  );
}
