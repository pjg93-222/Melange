/* Step 14 (lane E-server addendum): two selfcheck assertions were inherited
   from the audit packet and are wrong for a published snapshot.

   Measured: the first re-publish produced a correct page and selfcheck reported
   6 CHECK(S) FAILED. All six were the checker's assumptions, not the page's:

     FAIL  no <!DOCTYPE> (the publisher wraps the file)
     FAIL  no <html> wrapper
     FAIL  no <head> wrapper
     FAIL  no <body> wrapper      -- the audit file WAS a fragment; the moved
                                     template is required to be a full document
     FAIL  8 industries: Crypto   (x2, once for the inlined copy and once for
                                     pocket-data.json) -- a --datasets Crypto
                                     publish has one industry by design

   So the assertions are corrected rather than the page. The wrapper checks are
   inverted (the document must now be complete on its own) and the industry
   count becomes a non-empty check that still prints what was published. Every
   other assertion in the file is untouched, including the reconciliation that
   recomputes totals from the raw result sets.

   Both edits are spans whose anchors contain no backslashes, with the
   replacements read from files, because the surrounding code carries regex
   escapes a JS patch string would have to double.

   Usage: node apply-e.js step14-selfcheck-assertions.js [--check] */
'use strict';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tools\\pocket',
  suffix: '20260914-E2',
  files: [{
    path: 'selfcheck.py',
    edits: [
      {from: "    check('<!doctype' not in lowered, ",
       to: "    check(lowered.count('<title>') == 1",
       replaceFile: 'files/selfcheck-wrappers.py'},
      {from: "    check(len(payload['ind']) == 8, ",
       to: "    for industry in payload['ind']:",
       replaceFile: 'files/selfcheck-industries.py'}
    ]
  }]
};
