/* F1 step 7 - DETACHED_PROCESS gives powershell.exe no console, so its
   ConsoleHost exits 0 without running the script: POST /api/restart answered
   200 and nothing happened. Measured on this machine (flags_probe.py):
     DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP  ran=False exit=0
     CREATE_NO_WINDOW|CREATE_NEW_PROCESS_GROUP  ran=True  exit=0
   CREATE_NO_WINDOW is also what collect_evidence already uses here. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat',
  eol: 'lf',
  files: [
    {path: 'app/server.py', eol: 'crlf', edits: [
      {find: "        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0",
       replace: "        # DETACHED_PROCESS would leave powershell.exe without a console: it\n" +
                "        # exits 0 without running the launcher, so the restart silently fails.\n" +
                "        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0"}
    ]},
    {path: 'tests/test_contribution_http.py', eol: 'lf', edits: [
      {find: "            self.assertTrue(flags & app.subprocess.DETACHED_PROCESS)\n" +
             "            self.assertTrue(flags & app.subprocess.CREATE_NEW_PROCESS_GROUP)",
       replace: "            # DETACHED_PROCESS gives powershell.exe no console and it exits\n" +
                "            # without running the launcher; the restart must not use it.\n" +
                "            self.assertTrue(flags & app.subprocess.CREATE_NO_WINDOW)\n" +
                "            self.assertTrue(flags & app.subprocess.CREATE_NEW_PROCESS_GROUP)\n" +
                "            self.assertFalse(flags & app.subprocess.DETACHED_PROCESS)"}
    ]}
  ]
};
