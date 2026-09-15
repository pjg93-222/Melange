/* Exact-text patch engine for build lane E-client (copy of
   audits\mentat_system_debug_20260913\redesign\apply.js with the backup suffix
   made a parameter, because this lane's backups are .bak-20260914-E).
   Usage: node apply.js <patch module>
   A patch module exports {root, eol, bak, files:[{path, eol, edits:[...]}]}.
   Every edit must match exactly `count` times (default 1) or nothing is written.
   Text is compared with \n newlines; afterwards every line whose text is
   unchanged from the backup regains its original end-of-line byte and new lines
   take the file's default, so mixed files stay mixed. */
'use strict';
const fs = require('fs');
const path = require('path');

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
const root = spec.root;
const suffix = spec.bak || '.bak-20260914-E';
const results = [];
for (const file of spec.files) {
  const target = path.join(root, file.path);
  if (file.create) {
    const fallbackNew = (file.eol || spec.eol) === 'lf' ? '\n' : '\r\n';
    if (fs.existsSync(target) && !file.overwrite) throw new Error('Refusing to overwrite ' + file.path);
    fs.writeFileSync(target, file.content.split('\r\n').join('\n').split('\n').join(fallbackNew));
    results.push(file.path + ': created, ' + file.content.split('\n').length + ' lines');
    continue;
  }
  const backup = target + suffix;
  if (!fs.existsSync(backup)) throw new Error('Missing backup for ' + file.path);
  let text = fs.readFileSync(target, 'utf8').split('\r\n').join('\n');
  for (const edit of file.edits) {
    if (edit.from != null) {
      const start = text.indexOf(edit.from);
      if (start === -1 || text.indexOf(edit.from, start + 1) !== -1) {
        throw new Error(file.path + ': span start anchor is missing or not unique:\n' + edit.from.slice(0, 200));
      }
      const stop = edit.to == null ? text.length : text.indexOf(edit.to, start + edit.from.length);
      if (stop === -1) throw new Error(file.path + ': span end anchor is missing:\n' + edit.to.slice(0, 200));
      text = text.slice(0, start) + edit.replace + text.slice(stop);
      continue;
    }
    const want = edit.count == null ? 1 : edit.count;
    let seen = 0, at = 0;
    for (;;) {
      const found = text.indexOf(edit.find, at);
      if (found === -1) break;
      seen++; at = found + edit.find.length;
    }
    if (seen !== want) {
      throw new Error(file.path + ': expected ' + want + ' match(es), found ' + seen +
        ' for:\n---\n' + edit.find.slice(0, 220) + '\n---');
    }
    text = want === 1 ? text.replace(edit.find, () => edit.replace) : text.split(edit.find).join(edit.replace);
  }
  const fallback = (file.eol || spec.eol) === 'lf' ? '\n' : '\r\n';
  const edited = splitLines(text);
  const original = splitLines(fs.readFileSync(backup, 'utf8'));
  const pairs = pairUp(edited, original);
  const out = edited.map((line, index) => {
    if (!line.eol) return line.text;
    return line.text + (pairs.has(index) ? original[pairs.get(index)].eol || fallback : fallback);
  }).join('');
  fs.writeFileSync(target, out);
  results.push(file.path + ': ' + file.edits.length + ' edit(s), ' + edited.length +
    ' lines, ' + pairs.size + ' lines unchanged');
}
console.log(results.join('\n'));
