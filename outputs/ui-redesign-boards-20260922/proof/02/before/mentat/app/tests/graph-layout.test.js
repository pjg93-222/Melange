/* The bar-row geometry, asserted without a browser.

   graph.js returns at its own `typeof document === 'undefined'` guard, so
   requiring it here costs one pure function and no DOM. The invariant is the
   point: dot, label, bar, value, share and sparkline are pairwise disjoint and
   all inside [0, W], at every width the panels are drawn at.

   Run this suite with the glob form; Node 24 rejects a bare directory, and the
   glob cannot live in the block comment above because it closes it:
     node --test "app/tests/**"/"*.test.js"      (cwd: mentat/) */
const test = require('node:test');
const assert = require('node:assert/strict');
const layout = require('../graph.js');
const theme = require('../theme.js');

// 506/508 is the candidates panel in the 1fr column at a 1920 viewport and
// 888 the categories panel in the 1.7fr column beside it; 520 is
// panelWidth()'s own fallback for a panel with no width yet, and 920 is the
// clamp ceiling.
const WIDTHS = [420, 508, 520, 585, 760, 888, 920];
// $0.00 through a trillion, and then two value columns wider than the panel can
// hold - the case a fixed 96px gutter and an unclamped measurement both lose.
const VALUE_WIDTHS = [0, 34, 78, 102, 137, 400, 4000];

function boxes(box) {
  const named = [];
  if (box.dotColumn > 0) named.push(['dot', 0, box.dotColumn]);
  named.push(['label', box.labelLeft, box.labelRight]);
  named.push(['bar', box.barLeft, box.barLeft + box.barMax]);
  if (box.valueWidth > 0) named.push(['value', box.valueRight - box.valueWidth, box.valueRight]);
  named.push(['share', box.shareRight - box.shareWidth, box.shareRight]);
  if (box.sparkWidth > 0) named.push(['spark', box.sparkX, box.sparkX + box.sparkWidth]);
  return named;
}

for (const width of WIDTHS) {
  for (const party of [false, true]) {
    for (const spark of [false, true]) {
      test('[graph-layout] W=' + width + ' party=' + party + ' spark=' + spark
        + ': the six columns are pairwise disjoint and inside the panel', () => {
        for (const valueWidth of VALUE_WIDTHS) {
          const box = layout.layoutColumns(width, {party: party, spark: spark, valueWidth: valueWidth});
          const named = boxes(box);
          const where = 'W=' + width + ' party=' + party + ' spark=' + spark + ' valueWidth=' + valueWidth;
          assert.equal(box.width, width, where + ': the width came back changed');
          for (const entry of named) {
            assert.ok(entry[2] > entry[1], where + ': the ' + entry[0] + ' box has no width');
            assert.ok(entry[1] >= 0, where + ': ' + entry[0] + ' starts at ' + entry[1] + ', outside the panel');
            assert.ok(entry[2] <= box.width, where + ': ' + entry[0] + ' ends at ' + entry[2] + ', past W=' + box.width);
          }
          for (let i = 0; i < named.length; i += 1) {
            for (let j = i + 1; j < named.length; j += 1) {
              const a = named[i], b = named[j];
              assert.ok(a[2] <= b[1] || b[2] <= a[1],
                where + ': ' + a[0] + ' [' + a[1] + ', ' + a[2] + '] overlaps '
                  + b[0] + ' [' + b[1] + ', ' + b[2] + ']');
            }
          }
        }
      });
    }
  }
}

/* The approved board's card rhythm. These are constants because two drawings
   read them - the single-line panels and the two-line Top organizations - and a
   pitch decided twice is a pitch that drifts. */
test('[graph-layout] the row rhythm is the board\u2019s, and the two-line row is taller', () => {
  assert.equal(layout.ROW_PITCH, 34, 'the board measures 34px between row baselines');
  assert.equal(layout.ROW_HEAD, 24, 'and 24px of head room above the first');
  assert.equal(layout.LABEL_SIZE, 13, 'label and value are 13px');
  assert.equal(layout.SHARE_SIZE, 12, 'the share is 12px and muted');
  // Top organizations gives the name its own line at the card's full width, so
  // its rows are taller than a single-line row by the drop plus the bar band.
  assert.ok(layout.TWO_LINE_PITCH > layout.ROW_PITCH,
    'a two-line row cannot be shorter than a one-line row');
  assert.ok(layout.TWO_LINE_NAME_DROP > 0 && layout.TWO_LINE_NAME_DROP < layout.TWO_LINE_PITCH,
    'the bar line sits below the name and inside the row');
  // A row is drawn from top-15 for pitch-4, so consecutive rows never touch.
  for (const pitch of [layout.ROW_PITCH, layout.TWO_LINE_PITCH]) {
    assert.ok(pitch - 4 < pitch, 'the row band leaves a gap to the next row');
    assert.ok(pitch - 4 > layout.LABEL_SIZE, 'and is taller than the text it holds');
  }
});

test('[graph-layout] a left-read label starts at labelLeft and still fits its column', () => {
  // Candidates and companies read left from one x (the board), so the first
  // glyph lands at labelLeft rather than at labelRight minus the measured
  // width. Either way the drawn text has to fit between the two.
  for (const width of WIDTHS) {
    for (const party of [false, true]) {
      const box = layout.layoutColumns(width, {party: party, spark: false, valueWidth: 78});
      const drawn = theme.fitText('AMERICAN BANKERS ASSOCIATION PAC', box.labelWidth,
        box.labelSize, '', party ? ' \u00b7 D' : '');
      const drawnWidth = theme.measureText(drawn, box.labelSize, '');
      assert.ok(box.labelLeft + drawnWidth <= box.labelRight + 1e-9,
        'W=' + width + ': a left-read label runs past its column into the bar');
      assert.ok(box.labelLeft + drawnWidth <= box.barLeft,
        'W=' + width + ': and must never reach the bar');
    }
  }
});

test('[graph-layout] the label column is the same in every panel at the same width', () => {
  for (const width of WIDTHS) {
    const plain = layout.layoutColumns(width, {party: false, spark: false, valueWidth: 78});
    const withSpark = layout.layoutColumns(width, {party: false, spark: true, valueWidth: 78});
    const withDot = layout.layoutColumns(width, {party: true, spark: false, valueWidth: 78});
    assert.equal(plain.labelRight, withSpark.labelRight, 'bars start at the same x with or without a sparkline');
    assert.equal(plain.labelRight, withDot.labelRight, 'and with or without a party dot');
    assert.equal(plain.barLeft, withSpark.barLeft);
    assert.equal(plain.barLeft, withDot.barLeft);
    assert.ok(plain.labelRight >= 130 && plain.labelRight <= 260, 'the label column stays inside its clamp');
  }
});

test('[graph-layout] the party dot sits inside the column reserved for it', () => {
  for (const width of WIDTHS) {
    const box = layout.layoutColumns(width, {party: true, spark: true, valueWidth: 78});
    assert.equal(box.dotColumn, layout.DOT_COL);
    assert.ok(box.dotCX - 4.5 >= 0, 'the dot does not run off the left edge');
    assert.ok(box.dotCX + 4.5 <= box.dotColumn, 'and does not reach into the label');
    assert.equal(box.labelLeft, box.dotColumn, 'the label starts where the dot column ends');
    const plain = layout.layoutColumns(width, {party: false, spark: true, valueWidth: 78});
    assert.equal(plain.labelLeft, 0, 'a panel with no dots uses the whole label column');
    assert.equal(plain.labelWidth - box.labelWidth, layout.DOT_COL);
  }
});

test('[graph-layout] the sparkline slot is the width the sparkline is drawn at', () => {
  for (const width of WIDTHS) {
    const box = layout.layoutColumns(width, {party: false, spark: true, valueWidth: 78});
    assert.equal(box.sparkWidth, layout.SPARK_W);
    // drawSparklines() lays its last point at SPARK_W - 2 and the end dot has
    // r = 1.8, so the line and its dot stay inside the slot.
    assert.ok(layout.SPARK_W - 2 + 1.8 <= box.sparkWidth);
    assert.equal(box.sparkX + box.sparkWidth, box.width - 4, 'the slot ends where the panel does');
    assert.equal(box.shareRight, box.sparkX - layout.SPARK_GAP,
      'the share is anchored to its own column, not to the panel edge');
    const plain = layout.layoutColumns(width, {party: false, spark: false, valueWidth: 78});
    assert.equal(plain.sparkWidth, 0, 'a panel with no sparkline reserves nothing for one');
    assert.equal(plain.shareRight, box.width - 4);
  }
});

test('[graph-layout] the bar keeps its 48px minimum even against an absurd value column', () => {
  for (const width of WIDTHS) {
    for (const spark of [false, true]) {
      const box = layout.layoutColumns(width, {party: true, spark: spark, valueWidth: 4000});
      assert.ok(box.barMax >= layout.BAR_MIN, 'the bar never shrinks below its minimum');
      assert.ok(box.valueWidth < 4000, 'and the value column is clamped to what is left');
      assert.ok(box.barLeft + box.barMax <= box.valueRight - box.valueWidth,
        'so the bar cannot run into the value column');
    }
  }
});

/* A3. fitText() protects a suffix from the cut so a truncated candidate still
   says which side of the aisle it is on. A party CODE is worth that; a party
   VALUE is not. Live, a row rendered as "\u2026 \u00b7 Other / Unclassified":
   21 of the column's characters were spent on a suffix that had to survive,
   and the name - the thing the row is about - was the bare ellipsis. */
const LONG_PARTY = 'Other / Unclassified';

test('[graph-layout] only a party code is protected from the cut', () => {
  for (const code of ['D', 'R', 'DFL', 'REP', 'IND']) {
    const parts = layout.labelParts('WARNER, MARK ROBERT', code);
    assert.equal(parts.text, 'WARNER, MARK ROBERT', code + ': the name is not touched');
    assert.equal(parts.suffix, ' \u00b7 ' + code, code + ': the code is the protected suffix');
  }
  for (const party of [LONG_PARTY, 'DEMOCRAT', 'Unknown']) {
    const parts = layout.labelParts('WARNER, MARK ROBERT', party);
    assert.equal(parts.suffix, '', party + ': a long party is not protected');
    assert.equal(parts.text, 'WARNER, MARK ROBERT \u00b7 ' + party,
      party + ': it rides on the label and is fitted with it');
  }
  for (const empty of ['', null, undefined, '   ']) {
    const parts = layout.labelParts('KHANNA, ROHIT', empty);
    assert.equal(parts.suffix, '', 'no party, no suffix');
    assert.equal(parts.text, 'KHANNA, ROHIT', 'and nothing appended');
  }
  assert.ok(layout.PARTY_CODE_MAX >= 3, 'a three-letter code such as DFL is still a code');
});

test('[graph-layout] a long party never leaves the name a bare ellipsis', () => {
  const names = ['WARNER, MARK ROBERT', 'BLUNT ROCHESTER, LISA',
    'AMERICA\u2019S CREDIT UNIONS PAC OF CREDIT UNION NATIONAL ASSOCIATION, INC.'];
  for (const width of WIDTHS) {
    const box = layout.layoutColumns(width, {party: true, spark: false, valueWidth: 78});
    for (const name of names) {
      const parts = layout.labelParts(name, LONG_PARTY);
      const drawn = theme.fitText(parts.text, box.labelWidth, box.labelSize, '', parts.suffix);
      assert.notEqual(drawn[0], '\u2026',
        'W=' + width + ': "' + drawn + '" starts with the cut mark, so no name is shown');
      assert.ok(theme.measureText(drawn, box.labelSize, '') <= box.labelWidth + 1e-9,
        'W=' + width + ': "' + drawn + '" is wider than its column');
      // A code, by contrast, still survives the cut whole.
      const coded = layout.labelParts(name, 'D');
      const codedDrawn = theme.fitText(coded.text, box.labelWidth, box.labelSize, '', coded.suffix);
      assert.ok(codedDrawn.endsWith(' \u00b7 D'),
        'W=' + width + ': "' + codedDrawn + '" lost the party code');
    }
  }
});

test('[graph-layout] a measured label always fits the column the layout gives it', () => {
  const names = ['WARNER, MARK ROBERT', 'BLUNT ROCHESTER, LISA', 'KHANNA, ROHIT',
    'AMERICA\u2019S CREDIT UNIONS PAC OF CREDIT UNION NATIONAL ASSOCIATION, INC.'];
  for (const width of WIDTHS) {
    for (const party of [false, true]) {
      const box = layout.layoutColumns(width, {party: party, spark: false, valueWidth: 78});
      for (const name of names) {
        const drawn = theme.fitText(name, box.labelWidth, box.labelSize, '', party ? ' \u00b7 D' : '');
        const drawnWidth = theme.measureText(drawn, box.labelSize, '');
        assert.ok(drawnWidth <= box.labelWidth + 1e-9,
          '"' + drawn + '" is ' + drawnWidth + 'px in a ' + box.labelWidth + 'px column at W=' + width);
        // the text is anchored at labelRight, so this is where its first glyph lands
        assert.ok(box.labelRight - drawnWidth >= box.labelLeft - 1e-9,
          '"' + drawn + '" starts at ' + (box.labelRight - drawnWidth) + ', left of the label column');
      }
    }
  }
});
