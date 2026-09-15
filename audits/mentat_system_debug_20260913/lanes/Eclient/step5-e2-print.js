/* E2 print chart. A printed sheet outlives the console window it came from,
   so the page has to say what it is on its own: title, scope, accounting
   basis, workbook SHA-256 and the date it left. Everything that belongs to
   the builder - the rail, the panels, the shelves, the status line - comes
   off the paper. */
'use strict';

const PRINT_CSS = [
  '',
  '/* -------------------------------------------------------------------- print */',
  '',
  '/* The provenance footer never shows on screen and always shows on paper, so',
  '   a printed chart can never be separated from the basis and the workbook',
  '   hash it was drawn from. */',
  '.studio-print-only { display: none; }',
  '@media print {',
  '  /* Printing the chart means printing the chart: the console rail, the',
  '     builder surfaces and the live status line all come off the page. */',
  '  body.studio-printing .app-navigation,',
  '  body.studio-printing .analysis-tabs,',
  '  body.studio-printing .app-footer { display: none !important; }',
  '  .studio-header, .studio-toolbar, .studio-quick-tools, .studio-shelves,',
  '  .studio-side, .studio-inspector, .studio-cards, .studio-showme,',
  '  .studio-sheets, .studio-status, .studio-inspection, .studio-result-controls,',
  '  .studio-briefing, .studio-share, .studio-reconcile, .studio-verified-summary,',
  '  #studio-note { display: none !important; }',
  '  .studio, .studio-grid, .studio-view { display: block !important; border: 0 !important; box-shadow: none !important; }',
  '  .studio-canvas-wrap { display: flex; flex-direction: column; overflow: visible !important; padding: 0 !important; }',
  '  .studio-canvas { max-height: none !important; overflow: visible !important; }',
  '  .studio-canvas svg, .studio-canvas-wrap svg { max-height: none !important; width: 100% !important; height: auto !important; }',
  '  .studio-print-only {',
  '    display: block; order: 99; margin-top: 10px;',
  '    border-top: 1px solid var(--line); padding-top: 8px;',
  '  }',
  '  .studio-print-title { font-family: var(--font-serif); font-weight: 400; font-size: 15px; margin: 0 0 3px; color: var(--acu-plum); }',
  '  .studio-print-line { font-size: 10px; line-height: 1.45; color: var(--muted); margin: 0 0 2px; }',
  '  .studio-print-mark { font-size: 10px; font-weight: 700; letter-spacing: .09em; color: var(--acu-plum); margin: 5px 0 0; }',
  '  @page { size: landscape; margin: 14mm; }',
  '}'
].join('\n');

const PRINT_JS = [
  '',
  '  // A printed sheet is still on a desk long after this window is closed, so',
  '  // it states its own title, scope, basis, workbook hash and date instead of',
  '  // relying on whoever printed it to remember them.',
  '  function printChart() {',
  '    const chart = currentChart();',
  "    if (!chart.svg) { failure('This view has no image to print. Download the data CSV instead.'); return; }",
  "    failure('');",
  "    el('print-title').textContent = chart.title;",
  "    el('print-scope').textContent = [chart.scope, chart.note].filter(Boolean).join(' \\u00b7 ');",
  "    el('print-source').textContent = [chart.basis,",
  "      chart.source ? 'Source ' + chart.source : '',",
  "      chart.provenance ? 'Workbook SHA-256 ' + chart.provenance : '',",
  "      'Printed ' + new Date().toLocaleDateString('en-US', {year: 'numeric', month: 'long', day: 'numeric'})]",
  "      .filter(Boolean).join(' \\u00b7 ');",
  "    document.body.classList.add('studio-printing');",
  '    const done = () => {',
  "      document.body.classList.remove('studio-printing');",
  "      window.removeEventListener('afterprint', done);",
  '      clearTimeout(timer);',
  '    };',
  '    // A dialog dismissed in a way that never fires afterprint must not leave',
  '    // the console wearing its print skin.',
  '    const timer = setTimeout(done, 60000);',
  "    window.addEventListener('afterprint', done);",
  '    window.print();',
  '  }',
  ''
].join('\n');

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-E',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.css',
      eol: 'crlf',
      edits: [
        {find: '@media (prefers-reduced-motion: reduce) { .studio * { transition: none !important; } }',
         replace: '@media (prefers-reduced-motion: reduce) { .studio * { transition: none !important; } }' + PRINT_CSS}
      ]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {find: '  }\n\n  /* --------------------------------------------------------------- filters */',
         replace: '  }\n' + PRINT_JS + '\n  /* --------------------------------------------------------------- filters */'},
        {find: "  el('copy-image').onclick = () => copyImage();",
         replace: "  el('copy-image').onclick = () => copyImage();\n  el('print-chart').onclick = () => printChart();"}
      ]
    }
  ]
};
