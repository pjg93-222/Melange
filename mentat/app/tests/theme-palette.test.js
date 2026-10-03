/* The categorical palette's brand slots and the stylesheet they come from
   (code-review finding 12, 2026-09-25).

   theme.js reads slots 1-4 of MentatTheme.categorical from the same four
   tokens MentatTheme.palette reads first (--acu-teal, --acu-purple,
   --acu-mauve, --acu-gold), so a brand change moves categoryColour(0..3) with
   palette[0..3]. node has no stylesheet, so here those slots fall back to four
   literal hexes: this suite parses acu-theme.css and fails when a token and
   its literal drift apart, then loads theme.js against a stand-in computed
   style to show the slots follow the tokens in the forms a browser reports. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const APP = path.join(__dirname, '..');
const BRAND_TOKENS = ['--acu-teal', '--acu-purple', '--acu-mauve', '--acu-gold'];
const CSS = fs.readFileSync(path.join(APP, 'acu-theme.css'), 'utf8');
const SOURCE = fs.readFileSync(path.join(APP, 'theme.js'), 'utf8');
const fallback = require('../theme.js');   // node: no stylesheet, so the literals

// The value acu-theme.css gives a custom property; each brand token is set once.
function declared(name) {
  const found = [...CSS.matchAll(new RegExp('(?:^|[;{\\s])' + name + '\\s*:\\s*([^;}]+)', 'g'))].map(m => m[1].trim().toLowerCase());
  assert.equal(found.length, 1, name + ' is declared once in acu-theme.css');
  return found[0];
}
// theme.js in a fresh context whose computed style answers from `tokens`.
function themeWith(tokens) {
  const sandbox = {document: {documentElement: {}}, getComputedStyle: () => ({getPropertyValue: name => tokens[name] || ''})};
  vm.runInNewContext(SOURCE, sandbox, {filename: path.join(APP, 'theme.js')});
  return sandbox.MentatTheme;
}
// Arrays from another context fail deepStrictEqual on their prototype alone.
const plain = list => [...list];

test('[theme-palette] the fallback literals for slots 1-4 are the acu-theme.css brand tokens', () => {
  const tokens = BRAND_TOKENS.map(declared);
  for (const value of tokens) assert.match(value, /^#[0-9a-f]{6}$/, 'a brand token is a #rrggbb hex');
  assert.deepEqual(fallback.categorical.slice(0, 4), tokens,
    'theme.js BRAND_FALLBACK drifted from acu-theme.css: change both together');
});

test('[theme-palette] with the stylesheet, slots 1-4 are the four tokens palette reads first', () => {
  const tokens = Object.fromEntries(BRAND_TOKENS.map(name => [name, declared(name)]));
  const theme = themeWith(tokens);
  assert.deepEqual(plain(theme.categorical.slice(0, 4)), plain(theme.palette.slice(0, 4)));
  assert.deepEqual(plain(theme.categorical), plain(fallback.categorical));
  assert.ok(Object.isFrozen(theme.categorical));
});

test('[theme-palette] a changed brand token moves categoryColour with it, in every form and past slot 12', () => {
  const theme = themeWith({'--acu-teal': ' #ABC ', '--acu-purple': 'rgb(1, 2, 3)',
    '--acu-mauve': 'rgba(255, 128, 0, 0.5)', '--acu-gold': 'rgb(16 32 48 / 50%)'});
  assert.deepEqual([0, 1, 2, 3].map(i => theme.categoryColour(i)), ['#aabbcc', '#010203', '#ff8000', '#102030']);
  assert.equal(theme.categoryColour(12), '#d0dae3', 'the tint rule reads the token too: #aabbcc 45% toward white');
  assert.equal(theme.categoryColour(24), '#77838f', 'and the shade rule: #aabbcc 30% toward black');
  assert.deepEqual(plain(theme.categorical.slice(4)), fallback.categorical.slice(4), 'slots 5-12 stay literal');
});

test('[theme-palette] a token it cannot read keeps that slot’s fallback', () => {
  const theme = themeWith({'--acu-teal': 'teal', '--acu-purple': 'rgb(300, 0, 0)', '--acu-mauve': '#12345'});
  assert.deepEqual(plain(theme.categorical.slice(0, 4)), fallback.categorical.slice(0, 4));
});
