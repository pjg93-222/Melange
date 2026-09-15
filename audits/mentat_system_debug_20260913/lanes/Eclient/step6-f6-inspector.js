/* F6 follow-up, per render R2: Canvas only keeps the header Inspector button
   with its filter-count badge at every width. A canvas showing filtered data
   with no way to read the filters is a chart that hides its own scope; the
   panel opens as a drawer over the chart instead of putting the builder back. */
'use strict';

const HIDDEN_SET_BEFORE =
  '.studio-options-hidden .studio-side,.studio-options-hidden .studio-inspector,' +
  '.studio-options-hidden .studio-cards,.studio-options-hidden .studio-showme,' +
  '.studio-options-hidden .studio-shelves,.studio-options-hidden .studio-shelf,' +
  '.studio-options-hidden .studio-quick-tools label {display:none!important}';

const HIDDEN_SET_AFTER = [
  '.studio-options-hidden .studio-side,',
  '.studio-options-hidden .studio-cards,.studio-options-hidden .studio-showme,',
  '.studio-options-hidden .studio-shelves,.studio-options-hidden .studio-shelf,',
  '.studio-options-hidden .studio-quick-tools label {display:none!important}',
  '/* Canvas only is still a reading of filtered data, so the Inspector button',
  '   stays in the header with its count at every width and opens the panel as',
  '   a drawer over the chart rather than restoring the whole builder. */',
  '.studio-options-hidden .studio-inspector-toggle {display:inline-flex;align-items:center}',
  '.studio-options-hidden .studio-inspector-toggle[aria-expanded=false] {border-color:var(--acu-gold)}',
  '.studio-options-hidden .studio-inspector {display:flex!important;position:fixed;top:0;right:0;bottom:0;',
  '  width:min(340px,92vw);z-index:9;max-height:none;overflow-y:auto;border-left:1px solid var(--line);',
  '  box-shadow:-8px 0 24px rgba(52,38,73,.16)}',
  '.studio-options-hidden .studio-inspector[hidden] {display:none!important}',
  '.studio-options-hidden .studio-inspector-close {display:inline-block}'
].join('\n');

const SET_OPTIONS_AFTER = [
  '  function setOptionsHidden(hidden) {',
  "    const host = document.querySelector('#view-chart-studio .studio');",
  "    if (host) host.classList.toggle('studio-options-hidden', !!hidden);",
  "    el('view-builder').setAttribute('aria-checked', String(!hidden));",
  "    el('view-canvas').setAttribute('aria-checked', String(!!hidden));",
  '    el(\'view-builder\').tabIndex = hidden ? -1 : 0;',
  '    el(\'view-canvas\').tabIndex = hidden ? 0 : -1;',
  '    // Canvas only puts the Inspector behind its header button the way a narrow',
  '    // window does: the filter count stays readable and the panel stays off the',
  '    // chart until it is asked for.',
  "    const narrow = !!(window.matchMedia && window.matchMedia('(max-width: 1200px)').matches);",
  '    const closed = !!hidden || narrow;',
  "    el('inspector').hidden = closed;",
  "    el('inspector-toggle').setAttribute('aria-expanded', String(!closed));",
  '  }'
].join('\n');

const SYNC_AFTER = [
  '  const syncInspector = isNarrow => {',
  "    const host = document.querySelector('#view-chart-studio .studio');",
  "    const closed = !!isNarrow || !!(host && host.classList.contains('studio-options-hidden'));",
  "    el('inspector').hidden = closed;",
  "    el('inspector-toggle').setAttribute('aria-expanded', String(!closed));",
  '  };'
].join('\n');

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-E',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.css',
      eol: 'crlf',
      edits: [{find: HIDDEN_SET_BEFORE, replace: HIDDEN_SET_AFTER}]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {from: '  function setOptionsHidden(hidden) {\n',
         to: '  const applyOptionsHidden = hidden => {',
         replace: SET_OPTIONS_AFTER + '\n'},
        {from: '  const syncInspector = isNarrow => {\n',
         to: '  if (narrowStudio) {',
         replace: SYNC_AFTER + '\n'}
      ]
    }
  ]
};
