/* Step 7 (lane E-server): two tracking exceptions appended to .gitignore.

   Measured before writing: .gitignore is MIXED (57 CRLF, 17 lone LF) and the
   tail region is LF, so new lines take LF and every existing line keeps its own
   ending through the engine's pairing pass.

   What each line is for, measured with `git check-ignore -v` before the edit:

     mentat/tools/pocket/mentat-pocket.html  ->  .gitignore:20:*.html   IGNORED
     mentat/app/vendor/pptxgen.bundle.js     ->  NOT IGNORED today

   So the .html exception is load-bearing now and the .js exception is not: no
   pattern currently hides the vendor bundle. It is added as instructed, and it
   is the line that keeps the bundle tracked if a future `*.js` rule lands.
   Neither file sits under an excluded directory, which would have made a
   negation impossible to honour.

   Usage: node apply-e.js step7-gitignore.js [--check] */
'use strict';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat',
  files: [{
    path: '.gitignore',
    eol: 'lf',
    edits: [
      {find: 'mentat/state/contribution-source-proofs/\n',
       replace: 'mentat/state/contribution-source-proofs/\n' +
                '\n' +
                '# Mentat Pocket page template and the vendored PptxGenJS bundle\n' +
                '!mentat/tools/pocket/*.html\n' +
                '!mentat/app/vendor/*.js\n'}
    ]
  }]
};
