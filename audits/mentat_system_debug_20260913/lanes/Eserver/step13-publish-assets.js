/* Step 13 (lane E-server addendum): the publish ships a complete snapshot.

   Three changes, per the coordinator's ruling on items 8 and 9:

   1. icon-180.png and manifest.webmanifest are copied into the output folder.
      The page links both as siblings, so a snapshot published without them is a
      page a phone will not install -- which is what ride step 31 is for. They
      are copied right after the folder is made, so they are present for the
      self-check whatever happens to the children afterwards.

   2. job.json carries output_files: every deliverable actually on disk at the
      end, so a reader knows what was produced without guessing at names.

   3. The moved selfcheck.py runs over the output folder as a post-check and its
      verdict is recorded as selfcheck / selfcheck_message. It is ADVISORY: it
      never changes done/failed, which stay governed by whether the children
      exited cleanly and the page exists. A published page that fails its own
      check is a visible fact, not a failed publish.

   Note on escapes: the `\\n` sequences below are JS escapes that emit a literal
   backslash-n into the Python source, which is what the source needs.

   Usage: node apply-e.js step13-publish-assets.js [--check] */
'use strict';

const DELIVERABLES = "('mentat-pocket.html', 'pocket-data.json', 'pocket-integrity.json',\n" +
                     "                                    'icon-180.png', 'manifest.webmanifest')";

const SELFCHECK =
  '            return process.wait()\n' +
  '\n' +
  '        def run_selfcheck(log):\n' +
  '            """Check what was published. Advisory: the verdict is recorded, not enforced."""\n' +
  '            log.write(\'\\n--- selfcheck ---\\n\')\n' +
  '            log.flush()\n' +
  '            try:\n' +
  "                finished = subprocess.run([sys.executable, str(tools / 'selfcheck.py'),\n" +
  "                                           '--dir', str(out_directory)], capture_output=True,\n" +
  '                                          text=True, creationflags=flags, timeout=600)\n' +
  '            except (OSError, subprocess.SubprocessError) as error:\n' +
  "                log.write('could not run: ' + str(error) + '\\n')\n" +
  "                return 'fail', 'The published page could not be checked: ' + str(error)\n" +
  "            output = (finished.stdout or '') + (finished.stderr or '')\n" +
  '            log.write(output)\n' +
  '            summary = next((line.strip() for line in reversed(output.splitlines())\n' +
  "                            if line.startswith('ALL CHECKS PASSED') or 'CHECK(S) FAILED' in line),\n" +
  "                           'The self-check produced no summary. See ' + str(log_path))\n" +
  "            return ('pass' if finished.returncode == 0 else 'fail'), summary\n" +
  '\n' +
  '        def publish():\n';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  suffix: '20260914-E2',
  files: [{
    path: 'server.py',
    edits: [
      // 1. Job state gains the three new fields.
      {find: "               'console_pid': os.getpid(), 'started_at': time.time(), 'finished_at': None}\n",
       replace: "               'console_pid': os.getpid(), 'output_files': [], 'selfcheck': None,\n" +
                "               'selfcheck_message': '', 'started_at': time.time(), 'finished_at': None}\n"},

      // 2. The self-check helper, beside step().
      {find: '            return process.wait()\n\n        def publish():\n', replace: SELFCHECK},

      // 3. The page's sibling assets are deliverables, not source.
      {find: '                out_directory.mkdir(parents=True, exist_ok=True)\n',
       replace: '                out_directory.mkdir(parents=True, exist_ok=True)\n' +
                '                # The page links these as siblings. A snapshot published without\n' +
                '                # them is a page a phone cannot install, so they ship with it.\n' +
                "                for name in ('icon-180.png', 'manifest.webmanifest'):\n" +
                '                    shutil.copyfile(tools / name, out_directory / name)\n'},

      // 4. Check the page once it has been built.
      {find: "                            failure = 'The page could not be built from the snapshot. See ' + str(log_path)\n",
       replace: "                            failure = 'The page could not be built from the snapshot. See ' + str(log_path)\n" +
                '                        else:\n' +
                "                            job.update(message='Checking the published page.')\n" +
                '                            record()\n' +
                "                            job['selfcheck'], job['selfcheck_message'] = run_selfcheck(log)\n"},

      // 5. Record what actually landed, before the verdict.
      {find: "            if not failure and not Path(job['output_path']).is_file():\n",
       replace: "            job['output_files'] = [str(out_directory / name) for name in\n" +
                '                                   ' + DELIVERABLES + '\n' +
                '                                   if (out_directory / name).is_file()]\n' +
                "            if not failure and not Path(job['output_path']).is_file():\n"}
    ]
  }]
};
