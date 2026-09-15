/* E0 (remainder): one description of the chart on screen, so every export
   shape - download, clipboard, print sheet, slide, briefing card - reads the
   same title, scope, basis and source instead of each rebuilding its own.
   Also the CSV Note row: the note under the chart carries the accounting
   basis and the paging caveat, and a spreadsheet that drops it is a chart
   without its footnote. */
'use strict';

const CURRENT =
`  // Everything that takes a chart out of this console needs the same account
  // of it. One reader of the live view, so a download, a clipboard image, a
  // print sheet and a slide can never disagree about what they are showing.
  function currentChart() {
    const state = sheet(), source = state.source || {};
    const basisLabel = verified()
      ? (contributions.BASIS[basis()] || [])[0] || ''
      : 'Worksheet values';
    return {
      svg: el('canvas').querySelector('svg'),
      title: lastTitle || el('title').textContent || 'Chart Studio',
      scope: lastScope || scopeText() || '',
      note: el('note').textContent || '',
      basis: basisLabel,
      sheetId: state.id,
      sheetName: state.name,
      source: source.reportName || '',
      provenance: source.sha256 || (data && data.sha256) || ''
    };
  }

`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-E',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        // The CSV a reader opens in Excel keeps the note the screen shows.
        {find: "      const rows = [['Chart', lastTitle], ['Scope', lastScope], ...paint.tableRows(lastResult, lastConfig, data)];",
         replace: "      const rows = [['Chart', lastTitle], ['Scope', lastScope], ['Note', el('note').textContent],\n        ...paint.tableRows(lastResult, lastConfig, data)];"},
        {find: "  /* --------------------------------------------------------------- filters */",
         replace: CURRENT + "  /* --------------------------------------------------------------- filters */"}
      ]
    }
  ]
};
