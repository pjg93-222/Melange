/* The Chart Studio HTTP contract, from both ends, against the same worked example
   payloads the Python suite sends to the server (mentat/app/studio-contract-examples.json).

   Two defects made this file necessary, and neither was visible to a per-side unit test.
   The server required a saved view's `source` to be an object and the client sent a
   caption, so every Save view answered 400. The server keeps a briefing item's
   provenance as an object and the export code did String(item.provenance), so every
   .pptx and HTML bundle printed "[object Obje" where the workbook SHA-256 belongs.
   Both sides passed their own tests throughout.

   So this file tests both directions. The PRODUCER tests run the real builders the
   browser uses and deep-equal what they make against the payloads below - they fail if
   `source` ever goes back to being a string. The READER tests prove nothing that comes
   back is ever stringified into a slide. */

// Run this suite with the glob form; Node 24 rejects a bare directory:
//   node --test "mentat/app/tests/**/*.test.js"
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const model = require('../chart-briefing.js');
const core = require('../chart-studio-core.js');

const examples = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'studio-contract-examples.json'), 'utf8'));
const item = examples.briefing_add;
const expected = examples.expected;
const producer = examples.producer;

/* ------------------------------------------------------- the producer: what we send */

test('the builder makes the saved-view payload the server accepts, from the live sheet', () => {
  const made = core.viewSourceRecord(producer.view_verified.sheet_source,
    producer.view_verified.chosen_dataset);
  assert.deepStrictEqual(made, examples.views_save.source);
  // The point of the whole fixture: this is an object on the wire, not a caption.
  assert.strictEqual(typeof made, 'object');
  assert.notStrictEqual(typeof examples.views_save.source, 'string',
    'the contract payload itself must not regress to a caption string');
});

test('a worksheet with no verified dataset still names its report and digest', () => {
  assert.deepStrictEqual(
    core.viewSourceRecord(producer.view_worksheet.sheet_source,
      producer.view_worksheet.chosen_dataset),
    producer.view_worksheet.expected_source);
});

test('a view recovered from the old browser store sends its caption as an object', () => {
  // This is the path that was still sending a bare string after the first fix, so every
  // migrated view was refused 400 and the refusal was swallowed by a bare catch.
  const made = core.captionSource(producer.view_recovered.label);
  assert.deepStrictEqual(made, producer.view_recovered.expected_source);
  assert.strictEqual(typeof made, 'object');
  assert.deepStrictEqual(core.captionSource(''), {});
});

test('the builder makes the briefing source and provenance the exports read back', () => {
  assert.deepStrictEqual(core.chartSourceRecord(producer.chart.sheet_source), item.source);
  assert.deepStrictEqual(
    core.chartProvenanceRecord(producer.chart.sheet_source, producer.chart.sha,
      producer.chart.generated_at),
    item.provenance);
});

test('no builder can be talked into emitting a string, whatever it is handed', () => {
  const inputs = [undefined, null, {}, 'a caption', {reportName: 'Book.xlsx'}];
  for (const input of inputs) {
    for (const made of [core.viewSourceRecord(input, null), core.chartSourceRecord(input),
                        core.chartProvenanceRecord(input, ''), core.captionSource(input)]) {
      assert.strictEqual(typeof made, 'object', 'builder returned ' + typeof made);
      assert.ok(made !== null);
    }
  }
});

test('what the builder makes round-trips back through the readers', () => {
  const source = core.viewSourceRecord(producer.view_verified.sheet_source,
    producer.view_verified.chosen_dataset);
  assert.strictEqual(core.sourceLabelOf(source), expected.view_source_caption);
  const provenance = core.chartProvenanceRecord(producer.chart.sheet_source, producer.chart.sha,
    producer.chart.generated_at);
  assert.strictEqual(model.provenanceSha({provenance}), expected.workbook_sha256);
  assert.strictEqual(model.shortSha({provenance}), expected.short_sha);
});

/* ------------------------------------------------------- the readers: what comes back */

test('the example item yields the real workbook digest, not a stringified object', () => {
  assert.strictEqual(model.provenanceSha(item), expected.workbook_sha256);
  assert.strictEqual(model.shortSha(item), expected.short_sha);
});

test('the source caption comes off the object, so the picker never prints one', () => {
  assert.strictEqual(model.sourceText(item), expected.source_caption);
});

test('the export source line carries the true short SHA and never the word object', () => {
  const line = model.sourceNoteText(item, 'September 14, 2026');
  assert.ok(line.includes(expected.short_sha),
    'the short SHA-256 must appear verbatim in the line every export carries: ' + line);
  assert.ok(!line.includes('[object'),
    'a stringified object reached the export line: ' + line);
  assert.ok(line.includes(expected.source_caption), line);
  assert.ok(line.includes(item.basis), line);
});

test('no reader ever stringifies an object, whatever shape the item arrives in', () => {
  const shapes = [
    item,
    {provenance: {}, source: {}},
    {provenance: {workbook_sha256: expected.workbook_sha256}, source: {reportName: 'Book.xlsx'}},
    {provenance: expected.workbook_sha256, source: expected.source_caption},
    {provenance: null, source: undefined},
    {},
    {provenance: {generatedAt: '2026-09-14T16:30:00.000Z'}, source: {mode: 'contributions'}}
  ];
  for (const shape of shapes) {
    const line = model.sourceNoteText(shape, 'September 14, 2026');
    assert.ok(!line.includes('[object'), 'stringified object for ' + JSON.stringify(shape));
    assert.strictEqual(typeof model.provenanceSha(shape), 'string');
    assert.strictEqual(typeof model.sourceText(shape), 'string');
    assert.strictEqual(typeof core.sourceLabelOf(shape.source), 'string');
  }
});

test('an item with no digest at all says so in words rather than printing nothing', () => {
  const line = model.sourceNoteText({provenance: {}, source: {}, basis: ''}, 'September 14, 2026');
  assert.ok(line.includes('SHA-256 unstated'), line);
  assert.ok(line.includes('basis unstated'), line);
});

test('what the browser sends the server is an object, so a caption is wrapped not dropped', () => {
  // The server replaces a non-object with an empty one, which is how a digest sent as
  // a bare string vanished between the console and the slide.
  assert.deepStrictEqual(model.provenanceRecord(expected.workbook_sha256),
    {sha: expected.workbook_sha256});
  assert.deepStrictEqual(model.sourceRecord(expected.source_caption),
    {label: expected.source_caption});
  assert.deepStrictEqual(model.provenanceRecord(item.provenance), item.provenance);
  assert.deepStrictEqual(model.sourceRecord(item.source), item.source);
  assert.deepStrictEqual(model.provenanceRecord(''), {});
  assert.deepStrictEqual(model.sourceRecord(null), {});
});

test('a record that survives the round trip still reads back as the same digest', () => {
  const sent = model.provenanceRecord(item.provenance);
  assert.strictEqual(model.provenanceSha({provenance: sent}), expected.workbook_sha256);
  const wrapped = model.provenanceRecord(expected.workbook_sha256);
  assert.strictEqual(model.provenanceSha({provenance: wrapped}), expected.workbook_sha256);
});
