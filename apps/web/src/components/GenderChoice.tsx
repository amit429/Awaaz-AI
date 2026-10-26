import { useTranslation } from 'react-i18next';
import type { Gender } from '@/lib/types';
import { cn } from '@/lib/utils';

/** Hindi and Marathi change "I am coming" for men and women; this picks the words Awaaz uses. */
export function GenderChoice({ value, onChange }: { value: Gender; onChange: (g: Gender) => void }) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-2">
      <p className="text-base font-medium">{t('profile.genderLabel')}</p>
      <div role="radiogroup" aria-label={t('profile.genderLabel')} className="grid grid-cols-3 gap-2">
        {(['male', 'female', 'unspecified'] as const).map((g) => (
          <button
            key={g}
            type="button"
            role="radio"
            aria-checked={value === g}
            onClick={() => onChange(g)}
            className={cn(
              'rounded-xl border bg-card px-3 py-2.5 text-sm font-medium transition-colors hover:bg-secondary/60',
              value === g && 'border-primary bg-secondary shadow-[inset_0_0_0_1px_var(--primary)]',
            )}
          >
            {t(`profile.gender.${g}`)}
          </button>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">{t('profile.genderHint')}</p>
    </div>
  );
}
