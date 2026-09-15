/* F3 defect found by its own test: the progress row lives inside the Data
   source panel, and the panel folds itself away after the first load - so a
   prepare, its elapsed time and its Cancel button were all invisible exactly
   when they mattered. The panel now opens itself for the duration of a prepare
   and returns to where it was afterwards. */
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
          find: "  let progressStart = 0, progressTimer = 0, progressDepth = 0;\n",
          replace: "  let progressStart = 0, progressTimer = 0, progressDepth = 0, progressOpened = false;\n"
        },
        {
          find: "  function showProgress(message) {\n    if (!progressStart) { progressStart = Date.now(); progressTimer = setInterval(tickProgress, 1000); }\n",
          replace: "  function showProgress(message) {\n" +
            "    // A prepare nobody can see is a console that looks frozen, and the way\n" +
            "    // out of it is the Cancel button in this panel, so the panel opens for\n" +
            "    // the duration and returns to where it was afterwards.\n" +
            "    const details = el('source-details');\n" +
            "    if (details && !details.open) { progressOpened = true; details.open = true; }\n" +
            "    if (!progressStart) { progressStart = Date.now(); progressTimer = setInterval(tickProgress, 1000); }\n"
        },
        {
          find: "  function clearProgress() {\n    clearInterval(progressTimer);\n    progressTimer = 0; progressStart = 0;\n    el('progress').hidden = true;\n  }\n",
          replace: "  function clearProgress() {\n" +
            "    clearInterval(progressTimer);\n" +
            "    progressTimer = 0; progressStart = 0;\n" +
            "    el('progress').hidden = true;\n" +
            "    const details = el('source-details');\n" +
            "    if (progressOpened && details) details.open = false;\n" +
            "    progressOpened = false;\n" +
            "  }\n"
        }
      ]
    }
  ]
};
