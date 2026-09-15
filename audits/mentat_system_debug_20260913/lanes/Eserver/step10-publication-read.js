/* Step 10 (lane E-server): the publication reader tolerates the swap it races.

   Measured on this machine, 2026-09-14, with one thread calling os.replace on a
   JSON file and one thread reading it for three seconds:

     reads 22582, read failures 2010 (8.9%), all PermissionError
     writes 1412, write failures 1789 (os.replace refused while the reader held it)

   Windows refuses both sides of that collision. read_json turns the reader's
   PermissionError into {}, and publication() was reading that as "no such job"
   -- a spurious 404 to a client polling a job that was running normally. The
   full suite reproduced it; the test alone did not.

   A job that never existed still answers immediately: it has no directory. Only
   a directory that exists with an unreadable state file is retried.

   Usage: node apply-e.js step10-publication-read.js [--check] */
'use strict';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  files: [{
    path: 'server.py',
    edits: [
      {find: "        job = read_json(self.root / 'publish' / identifier / 'job.json')\n" +
             "        if job.get('id') != identifier:\n" +
             '            return None\n',
       replace:
             "        path = self.root / 'publish' / identifier / 'job.json'\n" +
             '        if not path.parent.is_dir():\n' +
             '            return None\n' +
             '        # A reader and the worker\'s os.replace collide on Windows: the read\n' +
             '        # fails with PermissionError while the state file is being swapped,\n' +
             '        # and read_json reports that as an empty object. Measured at 8.9% of\n' +
             '        # reads under contention, so a state that will not read is retried\n' +
             '        # rather than reported missing. A job that never existed has no\n' +
             '        # directory and is answered on the first pass.\n' +
             '        for attempt in range(6):\n' +
             '            job = read_json(path)\n' +
             "            if job.get('id') == identifier:\n" +
             '                break\n' +
             '            time.sleep(0.05)\n' +
             '        else:\n' +
             '            return None\n'}
    ]
  }]
};
