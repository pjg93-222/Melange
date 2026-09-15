/* F0 cycle carry. Graph option values are the cycle END YEAR (graph.js:73,
   graph_data.py cycles), the verified index stores the pair the cycle covers
   (contribution_data.py:322 -> f'{cycle-1}-{cycle}'), so a hand-off carrying
   '2024' filtered on a value the index never holds and the studio answered
   "No matching observations". */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio-core.js',
      eol: 'crlf',
      edits: [
        {
          find: "  /* --------------------------------------------------------------- compile */\n",
          replace: "  /* ------------------------------------------------------- carried scope */\n\n" +
            "  // Graph names an election cycle by the year it ends in ('2024'); the\n" +
            "  // verified index stores the pair that cycle covers ('2023-2024'). A scope\n" +
            "  // carried from Graph without this translation filtered on a value the\n" +
            "  // index never holds, so the studio answered \"No matching observations\"\n" +
            "  // for a company that plainly has receipts. Every other field is carried\n" +
            "  // unchanged: this is a spelling difference, not a rule.\n" +
            "  function carriedFilterValue(fieldId, value) {\n" +
            "    const text = value == null ? '' : String(value);\n" +
            "    if (fieldId !== 'cycle' || !/^\\d{4}$/.test(text)) return text;\n" +
            "    return (Number(text) - 1) + '-' + text;\n" +
            "  }\n\n" +
            "  // The reverse, for the Graph query the reconciliation strip fires. A label\n" +
            "  // that is not a consecutive pair is not a cycle Graph can answer for, so\n" +
            "  // it returns '' rather than a year the reader never chose.\n" +
            "  function graphCycleValue(cycleLabel) {\n" +
            "    const text = cycleLabel == null ? '' : String(cycleLabel);\n" +
            "    const pair = /^(\\d{4})-(\\d{4})$/.exec(text);\n" +
            "    if (pair) return Number(pair[2]) === Number(pair[1]) + 1 ? pair[2] : '';\n" +
            "    return /^\\d{4}$/.test(text) ? text : '';\n" +
            "  }\n\n" +
            "  /* --------------------------------------------------------------- compile */\n"
        },
        {
          find: "    classifyFields, fieldAt, subjectField, pill, shelf, createSheet, clearSheet, swapShelves, sourceKey,\n",
          replace: "    classifyFields, fieldAt, subjectField, pill, shelf, createSheet, clearSheet, swapShelves, sourceKey,\n" +
            "    carriedFilterValue, graphCycleValue,\n"
        }
      ]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "      const value = read(control);\n      if (value) scope.filters.push({field, value});\n",
          replace: "      const value = read(control);\n" +
            "      // Graph spells a cycle by its end year and the verified index spells it\n" +
            "      // as the pair it covers, so the carried value is translated here rather\n" +
            "      // than filtered on a spelling the index never holds.\n" +
            "      if (value) scope.filters.push({field, value: core.carriedFilterValue(field, value)});\n"
        }
      ]
    },
    {
      path: 'tests/chart-studio-core.test.js',
      eol: 'crlf',
      edits: [
        {
          find: "test('company overview names the fields a source does not have', () => {\n",
          replace: "test('a cycle carried from Graph is translated into the spelling the index stores', () => {\n" +
            "  // graph.js option values are the end year; contribution_data.py stores the pair.\n" +
            "  assert.strictEqual(core.carriedFilterValue('cycle', '2024'), '2023-2024');\n" +
            "  assert.strictEqual(core.carriedFilterValue('cycle', 2026), '2025-2026');\n" +
            "  assert.strictEqual(core.carriedFilterValue('cycle', '2023-2024'), '2023-2024');\n" +
            "  assert.strictEqual(core.carriedFilterValue('cycle', ''), '');\n" +
            "  assert.strictEqual(core.carriedFilterValue('company', '2024'), '2024');\n" +
            "});\n\n" +
            "test('the reverse map gives Graph the end year, and refuses anything that is not a cycle', () => {\n" +
            "  assert.strictEqual(core.graphCycleValue('2023-2024'), '2024');\n" +
            "  assert.strictEqual(core.graphCycleValue('2024'), '2024');\n" +
            "  assert.strictEqual(core.graphCycleValue('2020-2024'), '');\n" +
            "  assert.strictEqual(core.graphCycleValue(''), '');\n" +
            "  assert.strictEqual(core.graphCycleValue(null), '');\n" +
            "});\n\n" +
            "test('company overview names the fields a source does not have', () => {\n"
        }
      ]
    }
  ]
};
