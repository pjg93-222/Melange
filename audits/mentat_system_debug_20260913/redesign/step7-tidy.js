/* The operator list now lives in chart-studio-core.js and every reader goes
   through core.filterSummary / the filter editor, so the alias is dead. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-studio.js',
    edits: [{
      find: `  const OPERATORS = core.FILTER_OPS;
  const AGG_LABEL`,
      replace: `  const AGG_LABEL`
    }]
  }]
};
