/* E1 copy image. A chart that can only leave as a file cannot be pasted into
   the message that is asking about it. The clipboard copy carries the same
   composed drawing the download carries - title and scope caption included -
   so a pasted image is never a chart with no account of itself. */
'use strict';

const STUDIO_COPY = [
  '',
  '  // The clipboard gets the same drawing the download would write, caption and',
  '  // all: an image pasted into a message has to carry its own scope.',
  '  async function copyImage() {',
  '    const chart = currentChart();',
  "    if (!chart.svg) { failure('This view has no image to copy. Download the data CSV instead.'); return; }",
  "    failure('');",
  '    try {',
  '      const size = await MentatExport.copy(chart.svg, chart.title, chart.scope);',
  "      status('Copied ' + size.width + 'x' + size.height + ' PNG with title and scope caption.');",
  '    } catch (error) { failure(error.message); }',
  '  }',
  ''
].join('\n');

const GRAPH_SUBJECT = [
  "  get('export-target').onchange=syncExport;",
  '  // One account of the chart being exported, read by the download, the',
  '  // clipboard copy and the briefing, so the three can never disagree.',
  '  function exportSubject() {',
  '    if(!view)return null;',
  "    const name=get('export-target').value;",
  "    if(name==='candidates'&&!view.candidate_available)return null;",
  "    const svg=get(name).querySelector('svg');",
  '    if(!svg)return null;',
  "    const note=name==='candidates'?view.candidate_note:view.note;",
  "    const context=`${get('scope').textContent}. ${name==='candidates'?get('mode').selectedOptions[0].textContent+'. '+(view.filters.mode==='direct'?'':view.filters.direction+'. '):''}${note} Preview: ${get(name).querySelectorAll('svg .graph-bar-button').length} of ${view[name].length} groups. `+view.reports.map(r=>`${r.name} SHA-256 ${r.sha256}`).join('; ');",
  '    return {name,svg,title:titleFor[name],context,reports:view.reports};',
  '  }',
  "  get('export').onclick=async()=>{",
  '    if(!view)return;',
  "    const format=get('export-format').value,subject=exportSubject();",
  '    if(!subject)return;',
  "    if(format==='csv'){exportChart(subject.name);return;}",
  "    try {await MentatExport.image(subject.svg,format,subject.title,subject.context,'mentat-'+subject.name);}",
  '    catch(e){error(e.message);}',
  '  };',
  "  get('copy-image').onclick=async()=>{",
  '    const subject=exportSubject();',
  "    if(!subject){error('This chart has no image to copy. Export its CSV instead.');return;}",
  "    error('');",
  '    try {await MentatExport.copy(subject.svg,subject.title,subject.context);}',
  '    catch(e){error(e.message);}',
  '  };',
  ''
].join('\n');

const CHARTS_COPY = [
  "  el('copy-image').onclick=async()=>{",
  '    if(!chart)return;',
  "    error('');",
  "    try {await MentatExport.copy(el('image').firstChild,el('title').textContent,el('scope').textContent);}",
  '    catch(e){error(e.message);}',
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
        {find: '  }\n\n  /* --------------------------------------------------------------- filters */',
         replace: '  }\n' + STUDIO_COPY + '\n  /* --------------------------------------------------------------- filters */'},
        {find: "  el('download-csv').onclick = () => download('csv');",
         replace: "  el('download-csv').onclick = () => download('csv');\n  el('copy-image').onclick = () => copyImage();"}
      ]
    },
    {
      path: 'graph.js',
      eol: 'crlf',
      edits: [
        {from: "  get('export-target').onchange=syncExport;\n  get('export').onclick=async()=>{\n",
         to: '  function renderFreshness() {',
         replace: GRAPH_SUBJECT},
        {find: "    get('full-table').disabled=get('export').disabled;",
         replace: "    get('full-table').disabled=get('export').disabled;\n" +
           "    get('copy-image').disabled=get('export').disabled;"}
      ]
    },
    {
      path: 'charts.js',
      eol: 'crlf',
      edits: [
        {find: "  el('save-csv').onclick=()=>{",
         replace: CHARTS_COPY + "  el('save-csv').onclick=()=>{"}
      ]
    }
  ]
};
