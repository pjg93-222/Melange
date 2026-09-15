/* Step 12 (lane E-server addendum): selfcheck.py gains --dir.

   The script resolved every input against its own folder, which made the moved
   copy unrunnable: its inputs live in the report folder the publish writes to.
   --dir points it at that folder; --data names the snapshot; with neither it
   behaves exactly as it did in the audit packet, because --dir defaults to the
   directory of the pocket-data.json being checked and that defaults to HERE.

   The size table splits: the five deliverables come from --dir, while
   extract_pocket_data.py is source rather than a deliverable and stays resolved
   against the script's own folder, so the table reads correctly in both modes.

   main() is replaced as a span, with the new body read from a file rather than
   written into a JS string: the body contains newline escapes a JS literal
   would have to double.

   Usage: node apply-e.js step12-selfcheck-dir.js [--check] */
'use strict';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tools\\pocket',
  suffix: '20260914-E2',
  files: [{
    path: 'selfcheck.py',
    edits: [
      {find: 'import json\nimport re\nimport struct\n',
       replace: 'import argparse\nimport json\nimport re\nimport struct\n'},
      {from: 'def main():\n', to: "if __name__ == '__main__':\n",
       replaceFile: 'files/selfcheck-main.py'}
    ]
  }]
};
