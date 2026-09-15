/* Step 1 (lane E-server): write mentat/tools/pocket/mentat-pocket.html as a full
   HTML document built from the audit copy.

   The audit copy is an artifact fragment: the publisher supplied <!doctype>,
   <html>, <head> and <body>. A file served from the report folder has no such
   publisher, so the moved template carries its own wrappers. Every other byte
   is copied unchanged, CRLF and all, including the 2026-09-13 snapshot already
   inlined between the data markers (build_page.py replaces it on each publish).

   Usage: node step1-template.js [--check]
*/
'use strict';
const fs = require('fs');
const crypto = require('crypto');

const SOURCE = 'C:\\Users\\pgoff\\Mentat\\audits\\mentat_system_debug_20260913\\pocket\\mentat-pocket.html';
const TARGET = 'C:\\Users\\pgoff\\Mentat\\mentat\\tools\\pocket\\mentat-pocket.html';

const SPLIT = '</style>\r\n\r\n<header class="band">';
const HEAD_OPEN = '<!doctype html>\r\n<html lang="en">\r\n<head>\r\n';
const HEAD_CLOSE = '</style>\r\n</head>\r\n<body>\r\n\r\n<header class="band">';
const TAIL = '</body>\r\n</html>\r\n';

const source = fs.readFileSync(SOURCE, 'latin1'); // byte-preserving round trip
if (source.split(SPLIT).length !== 2) throw new Error('split anchor is not unique');
if (!source.endsWith('</script>\r\n')) throw new Error('unexpected tail');

const built = HEAD_OPEN + source.replace(SPLIT, HEAD_CLOSE) + TAIL;
const bytes = Buffer.from(built, 'latin1');

// Byte-identical elsewhere: removing the three inserted runs must restore the
// source exactly. This is checked, not assumed.
const restored = built.slice(HEAD_OPEN.length, built.length - TAIL.length)
  .replace('</style>\r\n</head>\r\n<body>\r\n\r\n<header class="band">', SPLIT);
if (restored !== source) throw new Error('the copy is not byte-identical outside the wrappers');

if (process.argv.includes('--check')) {
  console.log('check only; would write ' + bytes.length + ' bytes');
} else {
  fs.writeFileSync(TARGET, bytes);
  console.log('wrote ' + TARGET);
}
const digest = t => crypto.createHash('sha256').update(t).digest('hex');
console.log('source bytes ' + Buffer.byteLength(source, 'latin1') + ' sha256 ' + digest(Buffer.from(source, 'latin1')));
console.log('target bytes ' + bytes.length + ' sha256 ' + digest(bytes));
console.log('added bytes  ' + (bytes.length - Buffer.byteLength(source, 'latin1')));
