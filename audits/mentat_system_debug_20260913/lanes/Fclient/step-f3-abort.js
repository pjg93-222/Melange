/* F3 hardening found while writing the Cancel test: the poll loop only checked
   its abort signal after the wait, so a cancelled prepare could put the progress
   row back up for one more poll before it noticed. Check before polling too. */
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
          find: "      for(;;){const result=await contributionAPI(path,query,signal);",
          replace: "      for(;;){if(signal?.aborted)throw new DOMException('View changed','AbortError');const result=await contributionAPI(path,query,signal);"
        }
      ]
    }
  ]
};
