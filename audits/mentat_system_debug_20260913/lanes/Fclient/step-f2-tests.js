/* F2 core tests: the four zones a single click can choose. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'tests/chart-studio-core.test.js',
      eol: 'crlf',
      edits: [
        {
          find: "test('a cycle carried from Graph is translated into the spelling the index stores', () => {\n",
          replace: "test('a single click sends a grouping across the top and a measure down the side', () => {\n" +
            "  const meta = core.classifyFields(COLUMNS);\n" +
            "  const dimension = core.fieldAt(meta, CATEGORY), measure = core.fieldAt(meta, AMOUNT);\n" +
            "  const empty = sheet({});\n" +
            "  assert.strictEqual(core.quickAddZone(dimension, empty), 'columns');\n" +
            "  assert.strictEqual(core.quickAddZone(measure, empty), 'rows');\n" +
            "  const taken = sheet({columns: [{column: CYCLE, aggregation: 'sum'}],\n" +
            "    rows: [{column: AMOUNT, aggregation: 'sum'}]});\n" +
            "  assert.strictEqual(core.quickAddZone(dimension, taken), 'rows');\n" +
            "  assert.strictEqual(core.quickAddZone(measure, taken), 'columns');\n" +
            "});\n\n" +
            "test('the click zone reads the shelves only, never a field selection', () => {\n" +
            "  const meta = core.classifyFields(COLUMNS);\n" +
            "  const dimension = core.fieldAt(meta, CATEGORY);\n" +
            "  // Marks channels are not shelves: a coloured view still sends the next\n" +
            "  // grouping to the empty Columns shelf.\n" +
            "  const coloured = sheet({marks: marks({color: {column: TIER, aggregation: 'sum'}})});\n" +
            "  assert.strictEqual(core.quickAddZone(dimension, coloured), 'columns');\n" +
            "  assert.strictEqual(core.quickAddZone(null, sheet({})), 'columns');\n" +
            "  assert.strictEqual(core.quickAddZone(dimension, {}), 'columns');\n" +
            "});\n\n" +
            "test('a cycle carried from Graph is translated into the spelling the index stores', () => {\n"
        }
      ]
    }
  ]
};
