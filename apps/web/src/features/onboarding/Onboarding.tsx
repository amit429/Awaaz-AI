import { ArrowRight, Check, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Centered } from '@/components/AppShell';
import { Brand } from '@/components/Brand';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useMe, useSaveMe } from '@/hooks/useData';
import { initialLanguage, LANGUAGES, setAppLanguage } from '@/i18n';
import { emptyProfile, withLanguage } from '@/lib/profile';
import type { Profile } from '@/lib/types';
import { cn } from '@/lib/utils';
import { PresetChips, ProfileForm } from '../profile/ProfileForm';

const TOTAL = 3;

export function Onboarding() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const me = useMe();
  const save = useSaveMe();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [profile, setProfile] = useState<Profile>(() => withLanguage(emptyProfile(), initialLanguage()));

  useEffect(() => {
    if (me.data && !me.data.consented) nav('/consent', { replace: true });
    else if (me.data?.onboarded) nav('/', { replace: true });
  }, [me.data, nav]);

  if (!me.data) {
    return (
      <Centered>
        <Skeleton className="h-8 w-40" />
        <Skeleton className="mt-6 h-40 w-full" />
      </Centered>
    );
  }
  const presets = me.data.presets;
  const ready = profile.display_name.trim().length > 0 && profile.preset !== null;

  function pickLanguage(code: string) {
    void setAppLanguage(code);
    setProfile((p) => withLanguage(p, code));
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-2xl flex-col px-4 py-8">
      <Brand />
      <div className="mt-8 flex gap-1.5" role="progressbar" aria-valuemin={1} aria-valuemax={TOTAL} aria-valuenow={step} aria-label={t('onboarding.step', { n: step, total: TOTAL })}>
        {[1, 2, 3].map((n) => <span key={n} className={cn('h-1.5 flex-1 rounded-full', n <= step ? 'bg-primary' : 'bg-muted')} />)}
      </div>

      {step === 1 && (
        <div className="mt-8 grid gap-6">
          <div>
            <h1 className="text-3xl font-semibold sm:text-4xl">{t('onboarding.languageTitle')}</h1>
            <p className="mt-2 text-muted-foreground">{t('onboarding.languageHint')}</p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {LANGUAGES.map((l) => (
              <button
                key={l.code}
                type="button"
                aria-pressed={profile.app_lang === l.code}
                onClick={() => pickLanguage(l.code)}
                className="rounded-xl border bg-card px-4 py-3.5 text-left outline-none transition-colors hover:bg-secondary/60 focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-pressed:border-primary aria-pressed:bg-secondary aria-pressed:shadow-[inset_0_0_0_1px_var(--primary)]"
              >
                <span className="block text-xl font-medium leading-tight">{l.native}</span>
                {l.native !== l.english && <span className="block text-sm text-muted-foreground">{l.english}</span>}
              </button>
            ))}
          </div>
          <Button size="lg" onClick={() => setStep(2)}>{t('onboarding.continue')} <ArrowRight className="size-4" /></Button>
        </div>
      )}

      {step === 2 && (
        <div className="mt-8 grid gap-8">
          <div>
            <h1 className="text-3xl font-semibold sm:text-4xl">{t('onboarding.title')}</h1>
            <p className="mt-2 text-muted-foreground">{t('onboarding.hint')}</p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="name" className="text-base">{t('onboarding.nameLabel')}</Label>
            <Input id="name" autoFocus className="h-12 text-base" value={profile.display_name} onChange={(e) => setProfile({ ...profile, display_name: e.target.value })} />
            <p className="text-sm text-muted-foreground">{t('onboarding.nameHint')}</p>
          </div>
          <div className="grid gap-3">
            <h2 className="text-base font-medium">{t('onboarding.howPhone')}</h2>
            <PresetChips value={profile} presets={presets} onChange={setProfile} />
          </div>
          <div className="grid gap-2 sm:grid-cols-[auto_1fr]">
            <Button variant="outline" size="lg" onClick={() => setStep(1)}>{t('common.back')}</Button>
            <Button size="lg" disabled={!ready} onClick={() => setStep(3)}>{t('onboarding.continue')} <ArrowRight className="size-4" /></Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="mt-8 grid gap-8">
          <div>
            <h1 className="text-3xl font-semibold sm:text-4xl">{t('onboarding.fineTune')}</h1>
            <p className="mt-2 text-muted-foreground">{t('onboarding.fineTuneHint')}</p>
          </div>
          <ProfileForm value={profile} presets={presets} onChange={setProfile} showPresets={false} />
          {save.isError && <Alert variant="destructive" role="alert"><AlertDescription>{t('common.couldNotSave')}</AlertDescription></Alert>}
          <div className="grid gap-2 sm:grid-cols-[auto_1fr]">
            <Button variant="outline" size="lg" onClick={() => setStep(2)}>{t('common.back')}</Button>
            <Button size="lg" disabled={save.isPending} onClick={() => save.mutate(profile, { onSuccess: () => nav('/', { replace: true }) })}>
              {save.isPending ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />} {t('onboarding.finish')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
