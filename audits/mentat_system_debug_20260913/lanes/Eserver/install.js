/* File installer for build lane E-server.

   Some files in this lane are written whole rather than patched: build_page.py
   (its body carries backslash escapes that a JS patch string would have to
   double, and the memory note on heredoc mangling applies to the shell route
   too) and the new python test suites. Authoring them under the scratchpad and
   copying them in keeps one reviewable source per file and keeps the write out
   of the Melange worktree's refusal.

   Every file this installs is LF, matching its measured siblings
   (mentat\tests and mentat\tools\pocket are pure LF).

   Usage: node install.js <manifest> [--check]
   A manifest exports [{from, to, eol}] with paths relative to this folder. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const here = __dirname;
const manifest = require(path.resolve(process.argv[2]));
const check = process.argv.includes('--check');
const digest = b => crypto.createHash('sha256').update(b).digest('hex');

for (const entry of manifest) {
  const source = path.resolve(here, entry.from);
  const target = path.resolve(entry.to);
  let text = fs.readFileSync(source, 'utf8').split('\r\n').join('\n');
  if (entry.eol !== 'lf' && entry.eol !== 'crlf') throw new Error(entry.to + ': declare eol');
  if (entry.eol === 'crlf') text = text.split('\n').join('\r\n');
  const out = Buffer.from(text, 'utf8');
  const had = fs.existsSync(target) ? fs.readFileSync(target) : null;
  if (!check) {
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, out);
  }
  const crlf = (text.match(/\r\n/g) || []).length;
  const lf = (text.match(/\n/g) || []).length - crlf;
  console.log(path.basename(target) + ': ' + out.length + ' bytes, CRLF ' + crlf + ' lone LF ' + lf +
    ', sha256 ' + digest(out).slice(0, 16) + (had ? ' (was ' + had.length + ' bytes ' + digest(had).slice(0, 16) + ')' : ' (new file)') +
    (check ? '  [CHECK ONLY, not written]' : ''));
}
