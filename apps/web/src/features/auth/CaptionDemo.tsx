import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

type Piece = string | { chip: string };
interface Line { who: 'them' | 'you'; text: Piece[] }

const SCRIPT: Line[] = [
  { who: 'them', text: ['हाँ, मिल जाएगी। ', { chip: '₹420' }, ' होंगे, ', { chip: 'शाम 6 बजे' }, ' तक तैयार।'] },
  { who: 'you', text: ['Kya ghar bhej sakte hain?'] },
  { who: 'them', text: ['होम डिलीवरी ', { chip: '₹30' }, ' एक्स्ट्रा। पता बताइए।'] },
];

const flat = (l: Line) => l.text.map((p) => (typeof p === 'string' ? p : p.chip)).join('');
const prefersReduced = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** A short captioned call that types itself once: the product, shown before sign-in. */
export function CaptionDemo() {
  const [shown, setShown] = useState(() => (prefersReduced() ? SCRIPT.map(flat).map((t) => t.length) : [0]));

  useEffect(() => {
    if (prefersReduced()) return;
    let line = 0;
    let chars = 0;
    const id = setInterval(() => {
      const total = flat(SCRIPT[line]!).length;
      if (chars < total) {
        chars += 2;
        setShown((s) => s.map((v, i) => (i === line ? Math.min(chars, total) : v)));
      } else if (line < SCRIPT.length - 1) {
        line += 1;
        chars = 0;
        setShown((s) => [...s, 0]);
      } else {
        clearInterval(id);
      }
    }, line === 1 ? 40 : 28);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="dark w-full max-w-md" aria-label="Example of a captioned call">
      <div className="rounded-[2rem] border border-white/10 bg-gradient-to-b from-white/[0.07] to-white/[0.02] p-4 shadow-2xl">
        <div className="mb-4 flex items-center gap-2 px-1 text-sm text-muted-foreground">
          <span className="size-2 rounded-full bg-live shadow-[0_0_0_4px] shadow-live/20" /> Sharma Medical
        </div>
        <div className="flex flex-col gap-2.5" aria-live="off">
          {SCRIPT.map((line, i) => {
            const count = shown[i];
            if (count === undefined) return null;
            let left = count;
            return (
              <div
                key={i}
                className={cn(
                  'max-w-[92%] rounded-3xl px-4 py-2.5 text-lg leading-snug',
                  line.who === 'them' ? 'self-start rounded-bl-md border border-white/10 bg-white/10 text-foreground' : 'self-end rounded-br-md bg-accent text-base font-medium text-accent-foreground',
                )}
              >
                {line.text.map((p, j) => {
                  const text = typeof p === 'string' ? p : p.chip;
                  const part = text.slice(0, Math.max(0, left));
                  left -= text.length;
                  return typeof p === 'string' ? (
                    <span key={j}>{part}</span>
                  ) : (
                    part && <span key={j} className="rounded-md bg-accent px-1.5 font-semibold text-accent-foreground">{part}</span>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
