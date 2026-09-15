/* Step 8 (lane E-server): two races closed in publish_pocket.

   1. The reply shared the live job dict with the worker thread. The worker adds
      a 'pid' key the moment the first child starts, and json.dumps iterating a
      dict that gains a key raises RuntimeError -- the POST would have failed
      intermittently, after the job had already started. The reply now carries a
      snapshot, and every state write serialises a snapshot too.

   2. os.replace fails on Windows while another process holds the destination
      open, and a poller reading job.json is exactly such a process. A lost
      state write would strand the job in 'running' with no way to notice, since
      the owning console is still alive. State writes now retry briefly.

   Each anchor carries the line above it: the bare call appears at four
   indentation depths, and the deeper ones contain the shallower ones as
   substrings, so indentation alone would not have identified them.

   Usage: node apply-e.js step8-pocket-hardening.js [--check] */
'use strict';

const RECORD =
  '\n' +
  '        def record():\n' +
  '            """Write the job state, retrying a reader\'s brief hold on the file.\n' +
  '\n' +
  '            os.replace fails while another process has the destination open,\n' +
  '            and a poller reading job.json is such a process. A state write lost\n' +
  "            that way would strand the job in 'running'. A copy is written: the\n" +
  '            reply below shares this dict with the worker thread.\n' +
  '            """\n' +
  '            for attempt in range(5):\n' +
  '                try:\n' +
  "                    return atomic_json(root / 'job.json', dict(job))\n" +
  '                except OSError:\n' +
  '                    time.sleep(0.05)\n' +
  '\n' +
  '        record()\n';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  files: [{
    path: 'server.py',
    edits: [
      {find: "               'console_pid': os.getpid(), 'started_at': time.time(), 'finished_at': None}\n" +
             "        atomic_json(root / 'job.json', job)\n",
       replace: "               'console_pid': os.getpid(), 'started_at': time.time(), 'finished_at': None}\n" + RECORD},

      {find: "            job['pid'] = process.pid\n" +
             "            atomic_json(root / 'job.json', job)\n",
       replace: "            job['pid'] = process.pid\n            record()\n"},

      {find: "                job.update(status='running', message='Reading the published report through this console.')\n" +
             "                atomic_json(root / 'job.json', job)\n",
       replace: "                job.update(status='running', message='Reading the published report through this console.')\n" +
             '                record()\n'},

      {find: "                        job.update(message='Building the page.')\n" +
             "                        atomic_json(root / 'job.json', job)\n",
       replace: "                        job.update(message='Building the page.')\n" +
             '                        record()\n'},

      {find: '                       finished_at=time.time())\n' +
             "            atomic_json(root / 'job.json', job)\n",
       replace: '                       finished_at=time.time())\n            record()\n'},

      {find: "        return {'job': job}\n", replace: "        return {'job': dict(job)}\n"}
    ]
  }]
};
