import { ArrowRight, Check, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brand } from '@/components/Brand';
import { Centered } from '@/components/AppShell';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useMe, useSaveMe } from '@/hooks/useData';
import { emptyProfile } from '@/lib/profile';
import type { Profile } from '@/lib/types';
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

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-2xl flex-col px-4 py-8">
      <Brand />
      <div className="mt-8 flex gap-1.5" aria-label={`Step ${step} of 2`}>
        <span className="h-1.5 flex-1 rounded-full bg-primary" />
        <span className={`h-1.5 flex-1 rounded-full ${step === 2 ? 'bg-primary' : 'bg-muted'}`} />
      </div>

      {step === 1 ? (
        <div className="mt-8 grid gap-8">
          <div>
            <h1 className="text-3xl font-semibold sm:text-4xl">Let’s set up your calls</h1>
            <p className="mt-2 text-muted-foreground">Two quick questions. You can change everything later in Me.</p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="name" className="text-base">What should we call you?</Label>
            <Input id="name" autoFocus className="h-12 text-base" value={profile.display_name} onChange={(e) => setProfile({ ...profile, display_name: e.target.value })} />
            <p className="text-sm text-muted-foreground">This name is said to the other person at the start of every call.</p>
          </div>
          <div className="grid gap-3">
            <h2 className="text-base font-medium">How do you use the phone?</h2>
            <PresetChips value={profile} presets={presets} onChange={setProfile} />
          </div>
          <Button size="lg" disabled={!ready} onClick={() => setStep(2)}>Continue <ArrowRight className="size-4" /></Button>
        </div>
      ) : (
        <div className="mt-8 grid gap-8">
          <div>
            <h1 className="text-3xl font-semibold sm:text-4xl">Fine-tune</h1>
            <p className="mt-2 text-muted-foreground">Turn on any mix. The first way of talking is your default on calls.</p>
          </div>
          <ProfileForm value={profile} presets={presets} onChange={setProfile} showPresets={false} />
          {save.isError && <Alert variant="destructive" role="alert"><AlertDescription>Could not save. Please try again.</AlertDescription></Alert>}
          <div className="grid gap-2 sm:grid-cols-[auto_1fr]">
            <Button variant="outline" size="lg" onClick={() => setStep(1)}>Back</Button>
            <Button size="lg" disabled={save.isPending} onClick={() => save.mutate(profile, { onSuccess: () => nav('/', { replace: true }) })}>
              {save.isPending ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />} Finish
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
