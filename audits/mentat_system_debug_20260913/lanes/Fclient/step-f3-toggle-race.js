/* F3 race, exposed when the F2 dedupe change shifted the timing: the summary
   line was refreshed only from the <details> 'toggle' event, and that event is
   queued as a task rather than fired synchronously. Code that opens or closes
   the panel itself therefore left the summary describing the previous state
   until a later task ran - briefly showing the folded line over an open panel.
   Every place that changes .open now refreshes the summary itself; the toggle
   listener stays for the reader's own clicks on the summary. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "    const details = el('source-details');\n    if (details && !details.open) { progressOpened = true; details.open = true; }\n",
          replace: "    const details = el('source-details');\n" +
            "    if (details && !details.open) { progressOpened = true; details.open = true; renderSourceSummary(); }\n"
        },
        {
          find: "    const details = el('source-details');\n    if (progressOpened && details) details.open = false;\n    progressOpened = false;\n  }\n",
          replace: "    const details = el('source-details');\n" +
            "    if (progressOpened && details) { details.open = false; renderSourceSummary(); }\n" +
            "    progressOpened = false;\n  }\n"
        },
        {
          find: "    progressOpened = false;\n    el('source-details').open = true;\n    el('source-details').querySelector('summary').focus();\n  };\n",
          replace: "    progressOpened = false;\n" +
            "    el('source-details').open = true;\n" +
            "    renderSourceSummary();\n" +
            "    el('source-details').querySelector('summary').focus();\n  };\n"
        }
      ]
    }
  ]
};
