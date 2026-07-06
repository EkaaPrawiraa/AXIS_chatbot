'use client';

import { useEffect, useState } from 'react';

/**
 * Tracks how many pixels of the layout viewport are currently covered by
 * on-screen chrome that `visualViewport` knows about but plain CSS doesn't —
 * primarily the iOS on-screen keyboard (+ its accessory bar).
 *
 * `100dvh` only shrinks for Safari's OWN chrome (the address bar auto-hide);
 * it does NOT shrink for the keyboard, so a `h-[100dvh]` flex column leaves
 * a dead gap between the last in-flow element (e.g. a chat composer) and
 * the actually-visible area above the keyboard. Resizing a container to
 * `visualViewport.height` alone isn't reliable either: iOS sometimes moves
 * the visual viewport DOWN (`offsetTop`) instead of only shrinking its
 * height, particularly once the page has auto-scrolled the focused input
 * into view. Combining `innerHeight - (height + offsetTop)` covers both
 * cases and is the technique documented for this exact WebKit quirk (the
 * same one apps like ChatGPT's mobile web rely on).
 *
 * Returns 0 until measured / on unsupported browsers.
 */
export function useKeyboardInset(): number {
  const [inset, setInset] = useState(0);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;

    const update = () => {
      const covered = window.innerHeight - (viewport.height + viewport.offsetTop);
      setInset(Math.max(0, Math.round(covered)));
    };
    update();
    viewport.addEventListener('resize', update);
    viewport.addEventListener('scroll', update);
    return () => {
      viewport.removeEventListener('resize', update);
      viewport.removeEventListener('scroll', update);
    };
  }, []);

  return inset;
}
