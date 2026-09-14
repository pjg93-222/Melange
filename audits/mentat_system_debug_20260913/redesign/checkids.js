/* Every id chart-studio.js and chart-comparison.js reach for must exist in
   index.html, and every studio id in index.html should be reachable. */
'use strict';
const fs = require('fs');
const path = require('path');
const root = 'C:\\Users\\pgoff\\Mentat\\mentat\\app';
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const present = new Set([...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]));

const wanted = new Map();
for (const file of ['chart-studio.js', 'chart-comparison.js']) {
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  for (const m of source.matchAll(/\bel\('([a-z0-9-]+)'\)/g)) wanted.set('studio-' + m[1], file);
  for (const m of source.matchAll(/getElementById\('([a-z0-9-]+)'\)/g)) wanted.set(m[1], file);
}
const missing = [...wanted].filter(([id]) => !present.has(id));
const studioIds = [...present].filter(id => id.startsWith('studio-'));
const unused = studioIds.filter(id => !wanted.has(id));
console.log('ids referenced: ' + wanted.size);
console.log('missing from index.html: ' + (missing.length ? missing.map(([id, file]) => id + ' (' + file + ')').join(', ') : 'none'));
console.log('studio ids in html never referenced by id: ' + (unused.length ? unused.join(', ') : 'none'));
process.exit(missing.length ? 1 : 0);
