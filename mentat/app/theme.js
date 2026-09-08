/* Share the locally served brand tokens with inline SVG and image exports. */
(() => {
  const style=getComputedStyle(document.documentElement);
  const token=name=>style.getPropertyValue(name).trim();
  globalThis.MentatTheme=Object.freeze({
    sans:token('--font-sans'),serif:token('--font-serif'),
    ink:token('--chart-ink'),muted:token('--muted'),grid:token('--chart-grid'),negative:token('--chart-negative'),
    palette:['--acu-teal','--acu-purple','--acu-mauve','--acu-gold','--acu-aqua','--acu-lilac','--acu-taupe'].map(token)
  });
})();
