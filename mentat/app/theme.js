/* Share the locally served brand tokens with inline SVG and image exports.

   This file also owns the one measured text fitter the console draws labels
   with. A budget counted in CHARACTERS cannot fit a proportional face: the
   6.6px-per-character guess it replaces is 28% short of Arial's mean uppercase
   advance, which is how a candidate name grew leftwards out of its column and
   through the party dot. The budget here is pixels, measured on a canvas
   context cached for the life of the page.

   node:test has no canvas, so measurement falls back to a deterministic
   per-character estimate in em. The same code path runs either way, so the
   geometry tests are reproducible without a browser. */
(function (root) {
  'use strict';
  const hasDocument = typeof document !== 'undefined' && !!document.documentElement;
  const style = hasDocument && typeof getComputedStyle === 'function'
    ? getComputedStyle(document.documentElement) : null;
  const token = name => (style ? style.getPropertyValue(name).trim() : '');

  // One canvas for the life of the page. A context per measurement is what
  // would make a measured fitter slower than the guess it replaces.
  let context;
  function measureContext() {
    if (context !== undefined) return context;
    context = null;
    try {
      if (hasDocument && typeof document.createElement === 'function') {
        const canvas = document.createElement('canvas');
        context = (canvas.getContext && canvas.getContext('2d')) || null;
      }
    } catch (error) { context = null; }
    return context;
  }

  // Advance widths in em for the no-canvas case. These are averages, not a
  // font: they are here so a budget is still refused rather than unbounded.
  const UPPER = 0.68, LOWER = 0.50, DIGIT = 0.556, SPACE = 0.278, OTHER = 0.30;
  function estimate(text, sizePx) {
    let em = 0;
    for (const character of text) {
      if (character === ' ') em += SPACE;
      else if (character >= '0' && character <= '9') em += DIGIT;
      else if (character >= 'A' && character <= 'Z') em += UPPER;
      else if (character >= 'a' && character <= 'z') em += LOWER;
      else em += OTHER;
    }
    return em * sizePx;
  }

  function measureText(text, sizePx, family) {
    const value = text == null ? '' : String(text);
    const size = Number(sizePx) || 0;
    if (!value || size <= 0) return 0;
    const ctx = measureContext();
    if (!ctx) return estimate(value, size);
    ctx.font = size + 'px ' + (family || theme.sans || 'sans-serif');
    return ctx.measureText(value).width;
  }

  const ELLIPSIS = '\u2026';
  // A cut name may not end on the comma or the middle dot that was only there
  // to separate it from the part just removed.
  const TRAILING = /[\s,\u00b7]+$/;

  // `suffix` is the part that must survive the cut - a candidate's party, so a
  // truncated row still says which side of the aisle it is on.
  function fitText(text, maxPx, sizePx, family, suffix) {
    const value = text == null ? '' : String(text);
    const tail = suffix == null ? '' : String(suffix);
    const budget = Number(maxPx);
    if (!(budget > 0)) return ELLIPSIS + tail;
    if (measureText(value + tail, sizePx, family) <= budget) return value + tail;
    const room = budget - measureText(ELLIPSIS, sizePx, family) - measureText(tail, sizePx, family);
    if (!(room > 0)) return ELLIPSIS + tail;
    const characters = Array.from(value);
    let low = 0, high = characters.length;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      if (measureText(characters.slice(0, mid).join(''), sizePx, family) <= room) low = mid;
      else high = mid - 1;
    }
    const head = characters.slice(0, low).join('').replace(TRAILING, '');
    return head ? head + ELLIPSIS + tail : ELLIPSIS + tail;
  }

  const theme = Object.freeze({
    sans:token('--font-sans'),serif:token('--font-serif'),
    ink:token('--chart-ink'),muted:token('--muted'),grid:token('--chart-grid'),negative:token('--chart-negative'),
    palette:['--acu-teal','--acu-purple','--acu-mauve','--acu-gold','--acu-aqua','--acu-lilac','--acu-taupe'].map(token),
    measureText: measureText, fitText: fitText
  });

  if (typeof module !== 'undefined' && module.exports) module.exports = theme;
  root.MentatTheme = theme;
})(typeof globalThis === 'undefined' ? this : globalThis);
