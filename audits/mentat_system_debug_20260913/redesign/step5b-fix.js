/* between was validated but not admitted to the worksheet operator list. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-math.js',
    eol: 'lf',
    edits: [{
      find: `      if (!['equals','contains','gte','lte','in','notin'].includes(f.op)) throw new Error('Choose a filter operation.');`,
      replace: `      if (!['equals','contains','gte','lte','in','notin','between'].includes(f.op)) throw new Error('Choose a filter operation.');`
    }]
  }]
};
