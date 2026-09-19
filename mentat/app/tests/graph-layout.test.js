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

// 508 is the candidates panel in the 1fr column at a 1920 viewport; 520 is
// panelWidth()'s own fallback for a panel with no width yet.
const WIDTHS = [420, 508, 520, 585, 760];
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

test('[graph-layout] the label column is the same in every panel at the same width', () => {
  for (const width of WIDTHS) {
    const plain = layout.layoutColumns(width, {party: false, spark: false, valueWidth: 78});
    const withSpark = layout.layoutColumns(width, {party: false, spark: true, valueWidth: 78});
    const withDot = layout.layoutColumns(width, {party: true, spark: false, valueWidth: 78});
    assert.equal(plain.labelRight, withSpark.labelRight, 'bars start at the same x with or without a sparkline');
    assert.equal(plain.labelRight, withDot.labelRight, 'and with or without a party dot');
    assert.equal(plain.barLeft, withSpark.barLeft);
    assert.equal(plain.barLeft, withDot.barLeft);
    assert.ok(plain.labelRight >= 120 && plain.labelRight <= 220, 'the label column stays inside its clamp');
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
