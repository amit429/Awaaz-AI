import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LANGUAGES, SPOKEN } from '@/i18n';

/** A language list showing each language in its own script, so people can find theirs. */
export function LanguageSelect({ id, value, onChange, spokenOnly, className }: { id?: string; value: string; onChange: (code: string) => void; spokenOnly?: boolean; className?: string }) {
  const list = spokenOnly ? SPOKEN : LANGUAGES;
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className={className ?? 'h-11 w-full'}><SelectValue /></SelectTrigger>
      <SelectContent>
        {list.map((l) => (
          <SelectItem key={l.code} value={l.code}>
            {l.native}{l.native !== l.english && <span className="ml-2 text-muted-foreground">{l.english}</span>}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
