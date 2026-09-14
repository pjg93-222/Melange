/* 750 is inside 500..2000 as well; the expectation, not the engine, was wrong. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'tests/chart-studio-core.test.js',
    edits: [{
      find: "  assert.strictEqual(selectedRows([{column: AMOUNT, op: 'between', value: ['500', '2000']}]), 3);",
      replace: "  assert.strictEqual(selectedRows([{column: AMOUNT, op: 'between', value: ['500', '2000']}]), 4);"
    }]
  }]
};
