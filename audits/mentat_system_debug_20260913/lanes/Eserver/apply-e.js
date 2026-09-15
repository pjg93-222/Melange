/* Exact-text patch engine for build lane E-server (backups `.bak-20260914-E`).

   Same pattern as redesign\apply.js. Line endings are handled by measured class,
   not by assumption -- a first pass of this lane assumed pure CRLF everywhere on
   the strength of a grep census that was wrong, and the assertion below is what
   caught it. Measured with Python on 2026-09-14:

     server.py                  1737 CRLF, 0 lone LF   -> pure CRLF
     README.md                   356 CRLF, 188 lone LF -> MIXED
     .gitignore                   57 CRLF, 17 lone LF  -> MIXED
     test_contribution_http.py     0 CRLF, 327 lone LF -> pure LF
     extract_pocket_data.py        0 CRLF, 331 lone LF -> pure LF
     build_page.py                 0 CRLF, 33 lone LF  -> pure LF

   Pure files are asserted on the way in and re-emitted in their own class.
   A mixed file keeps every unchanged line's original ending, recovered by
   pairing lines against the pristine reference (longest common subsequence);
   lines this lane introduces take spec/file `eol`, which a mixed file must
   declare. A file containing a lone CR is refused outright.

   Usage: node apply-e.js <patch module> [--check]
   A patch module exports {root, eol?, files:[{path, pristine?, eol?, edits:[{find, replace, count}]}]}.
   Every edit must match exactly `count` times (default 1) or nothing is written. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function census(text) {
  let crlf = 0, loneLF = 0, loneCR = 0;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '\n') { if (i > 0 && text[i - 1] === '\r') crlf++; else loneLF++; }
    else if (text[i] === '\r' && text[i + 1] !== '\n') loneCR++;
  }
  const kind = loneCR ? 'cr' : (crlf && !loneLF) ? 'crlf' : (!crlf) ? 'lf' : 'mixed';
  return {crlf, loneLF, loneCR, kind};
}

function splitLines(text) {
  const out = [];
  let start = 0;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '\n') {
      const crlf = i > start && text[i - 1] === '\r';
      out.push({text: text.slice(start, crlf ? i - 1 : i), eol: crlf ? '\r\n' : '\n'});
      start = i + 1;
    }
  }
  if (start < text.length) out.push({text: text.slice(start), eol: ''});
  return out;
}

function pairUp(a, b) {
  const n = a.length, m = b.length;
  const table = new Uint32Array((n + 1) * (m + 1));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      table[i * (m + 1) + j] = a[i].text === b[j].text
        ? table[(i + 1) * (m + 1) + j + 1] + 1
        : Math.max(table[(i + 1) * (m + 1) + j], table[i * (m + 1) + j + 1]);
  const pairs = new Map();
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i].text === b[j].text) { pairs.set(i, j); i++; j++; }
    else if (table[(i + 1) * (m + 1) + j] >= table[i * (m + 1) + j + 1]) i++;
    else j++;
  }
  return pairs;
}

const spec = require(path.resolve(process.argv[2]));
const check = process.argv.includes('--check');
const results = [];

for (const file of spec.files) {
  const target = path.join(spec.root, file.path);
  // A file this lane created by copying keeps its pristine reference where the
  // copy came from (the audit packet), so no .bak is minted beside the new file.
  const backup = file.pristine
    ? path.resolve(file.pristine)
    : target + '.bak-' + (file.suffix || spec.suffix || '20260914-E');
  if (!fs.existsSync(backup)) throw new Error('Missing pristine reference for ' + file.path + ': ' + backup);
  const before = fs.readFileSync(target);
  const text = before.toString('utf8');
  const start = census(text);
  if (start.kind === 'cr') throw new Error(file.path + ': lone CR present; refusing to guess');

  let body = text.split('\r\n').join('\n');
  let applied = 0;
  for (const edit of file.edits) {
    // Replacement text may come from a file. Python bodies carry backslash
    // escapes that a JS patch string would have to double, and doubling them by
    // hand is exactly the class of error the memory note on heredoc mangling
    // warns about; reading the replacement as bytes removes the question.
    const replacement = edit.replaceFile
      ? fs.readFileSync(path.resolve(path.dirname(process.argv[2]), edit.replaceFile), 'utf8')
          .split('\r\n').join('\n')
      : edit.replace;
    if (edit.from != null) {
      // Span edit: replace everything between two unique anchors, keeping the
      // trailing anchor. Used when a whole function body is being rewritten.
      const start = body.indexOf(edit.from);
      if (start === -1 || body.indexOf(edit.from, start + 1) !== -1) {
        throw new Error(file.path + ': span start anchor missing or not unique:\n' + edit.from.slice(0, 200));
      }
      const stop = body.indexOf(edit.to, start + edit.from.length);
      if (stop === -1) throw new Error(file.path + ': span end anchor missing:\n' + edit.to.slice(0, 200));
      body = body.slice(0, start) + replacement + body.slice(stop);
      applied++;
      continue;
    }
    const want = edit.count == null ? 1 : edit.count;
    let seen = 0, at = 0;
    for (;;) {
      const found = body.indexOf(edit.find, at);
      if (found === -1) break;
      seen++; at = found + edit.find.length;
    }
    if (seen !== want) {
      throw new Error(file.path + ': expected ' + want + ' match(es), found ' + seen +
        ' for:\n---\n' + edit.find.slice(0, 260) + '\n---');
    }
    body = want === 1 ? body.replace(edit.find, () => replacement) : body.split(edit.find).join(replacement);
    applied++;
  }

  let out;
  let how;
  if (start.kind === 'crlf') { out = Buffer.from(body.split('\n').join('\r\n'), 'utf8'); how = 'pure CRLF'; }
  else if (start.kind === 'lf') { out = Buffer.from(body, 'utf8'); how = 'pure LF'; }
  else {
    const fallback = (file.eol || spec.eol);
    if (fallback !== 'lf' && fallback !== 'crlf') {
      throw new Error(file.path + ': mixed endings need an explicit eol ("lf" or "crlf") for new lines');
    }
    const newline = fallback === 'lf' ? '\n' : '\r\n';
    const edited = splitLines(body);
    const original = splitLines(fs.readFileSync(backup, 'utf8'));
    const pairs = pairUp(edited, original);
    out = Buffer.from(edited.map((line, index) => line.eol
      ? line.text + (pairs.has(index) ? original[pairs.get(index)].eol || newline : newline)
      : line.text).join(''), 'utf8');
    how = 'mixed; ' + pairs.size + ' line(s) kept their own ending, new lines ' + fallback.toUpperCase();
  }

  const after = census(out.toString('utf8'));
  if (start.kind !== 'mixed' && after.kind !== start.kind) {
    throw new Error(file.path + ': line-ending class changed ' + start.kind + ' -> ' + after.kind);
  }
  const digest = b => crypto.createHash('sha256').update(b).digest('hex');
  if (!check) fs.writeFileSync(target, out);
  results.push(file.path + ': ' + applied + ' edit(s); ' + how + '; CRLF ' + start.crlf + '/' + start.loneLF +
    ' -> ' + after.crlf + '/' + after.loneLF + '; ' + before.length + ' -> ' + out.length + ' bytes; sha256 ' +
    digest(before).slice(0, 16) + ' -> ' + digest(out).slice(0, 16) + (check ? '  [CHECK ONLY, not written]' : ''));
}
console.log(results.join('\n'));
