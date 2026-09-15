/* Step 5 (lane E-server): extract_pocket_data.py gains --out-dir.

   The data and the integrity block land in the report folder instead of beside
   the script. --datasets already existed (audit copy line 277) and is left
   alone apart from its help text. --out/--audit keep working and still win when
   given explicitly; only their defaults move under --out-dir.

   The audit packet copy is the pristine reference; it is not edited.
   build_page.py is not patched here: its body carries backslash escapes that a
   JS patch string would have to double, so step5b installs that file whole.

   Usage: node apply-e.js step5-tools.js [--check] */
'use strict';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tools\\pocket',
  files: [
    {
      path: 'extract_pocket_data.py',
      pristine: 'C:\\Users\\pgoff\\Mentat\\audits\\mentat_system_debug_20260913\\pocket\\extract_pocket_data.py',
      edits: [
        {find: "    parser.add_argument('--out', default=str(Path(__file__).with_name('pocket-data.json')))\n" +
               "    parser.add_argument('--audit', default=str(Path(__file__).with_name('pocket-integrity.json')))\n" +
               "    parser.add_argument('--datasets', default='')\n" +
               "    parser.add_argument('--no-spot-checks', action='store_true')\n" +
               '    options = parser.parse_args()\n',
         replace:
               "    parser.add_argument('--out-dir', default='',\n" +
               "                        help='Folder for pocket-data.json and pocket-integrity.json')\n" +
               "    parser.add_argument('--out', default='')\n" +
               "    parser.add_argument('--audit', default='')\n" +
               "    parser.add_argument('--datasets', default='', help='Comma-separated catalog ids; default all')\n" +
               "    parser.add_argument('--no-spot-checks', action='store_true')\n" +
               '    options = parser.parse_args()\n' +
               '    # --out and --audit still win when given; --out-dir only moves their\n' +
               '    # defaults, so a caller can redirect both by naming one folder.\n' +
               '    directory = Path(options.out_dir) if options.out_dir else Path(__file__).parent\n' +
               '    directory.mkdir(parents=True, exist_ok=True)\n' +
               "    options.out = options.out or str(directory / 'pocket-data.json')\n" +
               "    options.audit = options.audit or str(directory / 'pocket-integrity.json')\n"}
      ]
    }
  ]
};
