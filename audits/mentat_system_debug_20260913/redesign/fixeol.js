/* Restore each unchanged line's original end-of-line byte after an edit.
   Usage: node fixeol.js <edited file> <original backup> <default eol: crlf|lf>
   Lines whose text is unchanged (matched by an LCS over line text) keep the
   end-of-line they had in the backup; new or changed lines get the default. */
'use strict';
const fs = require('fs');

function split(text) {
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

function lcs(a, b) {
  const n = a.length, m = b.length;
  const table = new Uint32Array((n + 1) * (m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      table[i * (m + 1) + j] = a[i].text === b[j].text
        ? table[(i + 1) * (m + 1) + j + 1] + 1
        : Math.max(table[(i + 1) * (m + 1) + j], table[i * (m + 1) + j + 1]);
    }
  }
  const pairs = new Map();
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i].text === b[j].text) { pairs.set(i, j); i++; j++; }
    else if (table[(i + 1) * (m + 1) + j] >= table[i * (m + 1) + j + 1]) i++;
    else j++;
  }
  return pairs;
}

const [target, backup, kind] = process.argv.slice(2);
const fallback = kind === 'lf' ? '\n' : '\r\n';
const edited = split(fs.readFileSync(target, 'utf8'));
const original = split(fs.readFileSync(backup, 'utf8'));
const pairs = lcs(edited, original);
let restored = 0, fixed = 0;
const out = edited.map((line, index) => {
  if (!line.eol) return line.text;
  const source = pairs.has(index) ? original[pairs.get(index)].eol || fallback : fallback;
  if (source !== line.eol) { if (pairs.has(index)) restored++; else fixed++; }
  return line.text + source;
}).join('');
fs.writeFileSync(target, out);
console.log(target + ': lines=' + edited.length + ' matched=' + pairs.size +
  ' eol-restored=' + restored + ' eol-normalised=' + fixed);
