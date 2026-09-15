/* F4(c) fix found by its own test: graph-direction defaults to 'Support' (see
   index.html's first option, and graph.js hides the control entirely while the
   candidate view is 'direct'), so treating '' as its default reported "Support
   or opposition: not carried" on every ordinary hand-off. Its default is
   'Support'. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "    ['direction', 'Support or opposition', 'that distinction exists only in Graph', '']\n",
          replace: "    ['direction', 'Support or opposition', 'that distinction exists only in Graph', 'Support']\n"
        }
      ]
    }
  ]
};
