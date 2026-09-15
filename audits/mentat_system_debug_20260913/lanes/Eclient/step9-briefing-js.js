/* E4 + E3 + E6 client: place chart-briefing.js. The source is kept beside this
   step file so the replayable edit log holds the exact bytes that were written. */
'use strict';
const fs = require('fs');
const path = require('path');

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-E',
  eol: 'crlf',
  files: [
    {
      path: 'chart-briefing.js',
      eol: 'lf',
      create: true,
      overwrite: true,
      content: fs.readFileSync(path.join(__dirname, 'chart-briefing.src.js'), 'utf8')
    }
  ]
};
