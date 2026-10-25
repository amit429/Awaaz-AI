import { useEffect, useState } from 'react';

/**
 * The part of the screen the user can actually see. When the on-screen keyboard opens (iOS Safari
 * does not shrink the page), this shrinks, so a screen sized to it keeps its input bar visible.
 */
export function useVisualViewport() {
  const read = () => ({
    height: window.visualViewport?.height ?? window.innerHeight,
    top: window.visualViewport?.offsetTop ?? 0,
  });
  const [box, setBox] = useState(read);
  useEffect(() => {
    const vv = window.visualViewport;
    const update = () => setBox(read());
    vv?.addEventListener('resize', update);
    vv?.addEventListener('scroll', update);
    window.addEventListener('resize', update);
    return () => {
      vv?.removeEventListener('resize', update);
      vv?.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);
  return box;
}
