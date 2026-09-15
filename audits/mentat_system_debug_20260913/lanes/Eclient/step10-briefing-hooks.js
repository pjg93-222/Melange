/* E4 hooks. Three surfaces draw charts - the studio, the Graph export row and
   the classic builder - and all three put charts in the same tray, because a
   briefing assembled from one surface only is a briefing missing half the
   argument. Each hook hands over the same description the tray stores. */
'use strict';

const STUDIO_HOOK = [
  '  // The tray itself lives in chart-briefing.js. A console that is not yet',
  '  // serving it says so rather than answering the click with nothing.',
  '  const toBriefing = () => {',
  '    if (!window.MentatBriefing) {',
  "      failure('The briefing tray is not served by this console yet. Restart the console and try again.');",
  '      return;',
  '    }',
  '    window.MentatBriefing.capture(currentChart());',
  '  };',
  "  el('briefing-add').onclick = toBriefing;",
  "  el('briefing-menu-add').onclick = toBriefing;"
].join('\n');

const GRAPH_HOOK = [
  "  get('briefing').onclick=()=>{",
  '    const subject=exportSubject();',
  "    if(!subject){error('This chart has no image to add. Export its CSV instead.');return;}",
  "    if(!window.MentatBriefing){error('The briefing tray is not served by this console yet. Restart the console and try again.');return;}",
  "    error('');",
  '    const report=(subject.reports||[])[0]||{};',
  '    window.MentatBriefing.capture({svg:subject.svg,title:subject.title,scope:subject.context,',
  "      chip:get('scope').textContent,note:'',basis:'Graph totals',sheetId:subject.name,sheetName:subject.title,",
  "      source:report.name||'',provenance:report.sha256||'',origin:'graph'});",
  '  };',
  ''
].join('\n');

const CHARTS_HOOK = [
  "  el('briefing').onclick=()=>{",
  '    if(!chart)return;',
  "    if(!window.MentatBriefing){error('The briefing tray is not served by this console yet. Restart the console and try again.');return;}",
  "    error('');",
  "    const report=(el('report').selectedOptions[0]||{}).textContent||'';",
  "    window.MentatBriefing.capture({svg:el('image').firstChild,title:el('title').textContent,",
  "      scope:el('scope').textContent,chip:report,note:'',basis:'Worksheet values',",
  "      sheetId:'classic',sheetName:el('title').textContent,source:report,",
  "      provenance:(data&&data.sha256)||'',origin:'classic'});",
  '  };',
  ''
].join('\n');

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-E',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {find: "  el('open-views').onclick = () => openViews();",
         replace: "  el('open-views').onclick = () => openViews();\n" + STUDIO_HOOK}
      ]
    },
    {
      path: 'graph.js',
      eol: 'crlf',
      edits: [
        {find: "    get('copy-image').disabled=get('export').disabled;",
         replace: "    get('copy-image').disabled=get('export').disabled;\n" +
           "    get('briefing').disabled=get('export').disabled;"},
        {find: "  function renderFreshness() {",
         replace: GRAPH_HOOK + "  function renderFreshness() {"}
      ]
    },
    {
      path: 'charts.js',
      eol: 'crlf',
      edits: [
        {find: "  el('save-csv').onclick=()=>{",
         replace: CHARTS_HOOK + "  el('save-csv').onclick=()=>{"}
      ]
    }
  ]
};
