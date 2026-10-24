import { User } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { applyPreset, HEAR_OPTIONS, PRESET_ICONS, READ_LANGS, summary, TALK_OPTIONS, toggle, TYPE_LANGS, withModes, type Option } from '@/lib/profile';
import type { HearMode, PresetDef, Profile, TalkMode } from '@/lib/types';
import { cn } from '@/lib/utils';

function Choice({ pressed, onClick, children, className }: { pressed: boolean; onClick: () => void; children: React.ReactNode; className?: string }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        'text-left transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50',
        'rounded-xl border bg-card hover:bg-secondary/60 aria-pressed:border-primary aria-pressed:bg-secondary aria-pressed:shadow-[inset_0_0_0_1px_var(--primary)]',
        className,
      )}
    >
      {children}
    </button>
  );
}

function Options<K extends string>({ options, selected, onToggle }: { options: Option<K>[]; selected: K[]; onToggle: (k: K) => void }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {options.map((o) => {
        const on = selected.includes(o.key);
        return (
          <Choice key={o.key} pressed={on} onClick={() => onToggle(o.key)} className="flex items-start gap-3 p-3.5">
            <span className={cn('grid size-9 shrink-0 place-items-center rounded-lg', on ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground')}>
              <o.icon className="size-[18px]" />
            </span>
            <span className="min-w-0">
              <span className="block font-medium leading-tight">{o.title}</span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{o.hint}</span>
              <span className="mt-1.5 flex flex-wrap gap-1.5">
                {(o.soon || o.tag) && <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">{o.tag ?? 'Coming soon'}</span>}
                {on && selected[0] === o.key && selected.length > 1 && <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground">Default</span>}
              </span>
            </span>
          </Choice>
        );
      })}
    </div>
  );
}

export function PresetChips({ value, presets, onChange }: { value: Profile; presets: Record<string, PresetDef>; onChange: (p: Profile) => void }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {Object.entries(presets).map(([key, def]) => {
        const Icon = PRESET_ICONS[key] ?? User;
        const on = value.preset === key;
        return (
          <Choice key={key} pressed={on} onClick={() => onChange(applyPreset(value, key, def))} className="flex items-center gap-3 p-3.5">
            <span className={cn('grid size-9 shrink-0 place-items-center rounded-lg', on ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground')}>
              <Icon className="size-[18px]" />
            </span>
            <span className="font-medium">{def.label}</span>
          </Choice>
        );
      })}
    </div>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-3">
      <div>
        <h3 className="text-lg font-semibold">{title}</h3>
        {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

export function ProfileForm({ value, presets, onChange, showPresets = true }: { value: Profile; presets: Record<string, PresetDef>; onChange: (p: Profile) => void; showPresets?: boolean }) {
  const talk = value.talk_modes ?? [];
  const hear = value.hear_modes ?? [];
  return (
    <div className="grid gap-8">
      {showPresets && (
        <Section title="Start from" hint="A preset only sets defaults. You can change anything below.">
          <PresetChips value={value} presets={presets} onChange={onChange} />
        </Section>
      )}

      <Section title="How I talk" hint="Choose all that you use. The first one is your default.">
        <Options<TalkMode> options={TALK_OPTIONS} selected={talk} onToggle={(k) => onChange(withModes(value, { talk_modes: toggle(talk, k) }))} />
      </Section>

      <Section title="How I hear them" hint="Mix freely, for example captions and clear voice together.">
        <Options<HearMode> options={HEAR_OPTIONS} selected={hear} onToggle={(k) => onChange(withModes(value, { hear_modes: toggle(hear, k) }))} />
      </Section>

      <Section title="Languages and reading">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="read-lang">I read</Label>
            <Select value={value.read_lang} onValueChange={(v) => onChange({ ...value, read_lang: v })}>
              <SelectTrigger id="read-lang" className="h-11 w-full"><SelectValue /></SelectTrigger>
              <SelectContent>{READ_LANGS.map(([k, n]) => <SelectItem key={k} value={k}>{n}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="type-lang">I type</Label>
            <Select value={value.type_lang} onValueChange={(v) => onChange({ ...value, type_lang: v })}>
              <SelectTrigger id="type-lang" className="h-11 w-full"><SelectValue /></SelectTrigger>
              <SelectContent>{TYPE_LANGS.map(([k, n]) => <SelectItem key={k} value={k}>{n}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </div>
        <div className="divide-y rounded-xl border bg-card">
          <div className="flex items-center justify-between gap-4 p-3.5">
            <Label htmlFor="large-text" className="font-normal">Larger text</Label>
            <Switch id="large-text" checked={value.easy_font} onCheckedChange={(v) => onChange({ ...value, easy_font: v })} />
          </div>
          <div className="flex items-center justify-between gap-4 p-3.5">
            <Label htmlFor="disclosure" className="font-normal">Tell the other person an assistant is helping</Label>
            <Switch id="disclosure" checked disabled aria-label="Always on" />
          </div>
        </div>
      </Section>

      <p aria-live="polite" className="rounded-xl bg-secondary px-4 py-3 text-sm">{summary(value)}</p>
    </div>
  );
}
