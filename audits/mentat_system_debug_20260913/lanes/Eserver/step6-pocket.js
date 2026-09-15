/* Step 6 (lane E-server): Console.publish_pocket, modelled on collect_evidence.

   The publisher reads this console over HTTP, so the console has to know the
   port it was given: Console.port, set in main() before serve_forever.

   The job id carries a 'publish-' prefix. That one decision does three jobs:
   the second publish finds the first in Console.jobs and gets a 409; a running
   pocket job makes Console.busy() true through the existing jobs check, with no
   edit to busy() (an edit there would break the SimpleNamespace stand-in that
   test_contribution_http.py calls it with); and the GET route can validate the
   id it is handed before touching the filesystem.

   No lock is held while the children run. The extractor calls back into this
   same server, and holding Console.lock across that wait would be a deadlock
   the moment any handler wanted the lock.

   Usage: node apply-e.js step6-pocket.js [--check] */
'use strict';

const METHOD = `    def publish_pocket(self, data):
        """Publish the phone snapshot: read this console, then build the page.

        Modelled on collect_evidence. One publication at a time per console;
        the job state lives at <data root>/publish/<id>/job.json so a reader
        that arrives after the answer was sent still sees the outcome.
        """
        port = int(getattr(self, 'port', 0) or 0)
        if not port:
            raise ValueError('This console does not know its own port. Restart it and publish again.')
        datasets = data.get('datasets')
        if not isinstance(datasets, list) or not datasets:
            raise ValueError('Choose at least one dataset to publish.')
        datasets = list(dict.fromkeys(str(value).strip() for value in datasets))
        if any(not value or ',' in value for value in datasets):
            raise ValueError('Choose datasets from the report catalog.')
        known = {str(entry.get('id')) for entry in
                 contribution_query.semantics.catalog(self.report_directory).get('datasets', [])}
        unknown = [value for value in datasets if value not in known]
        if unknown:
            raise ValueError('Not in this report: ' + ', '.join(unknown) + '.')
        identifier = 'publish-' + uuid.uuid4().hex
        with self.lock:
            if any(str(job).startswith('publish-') for job in self.jobs):
                raise Conflict('A phone snapshot is already being published. Wait for it to finish.')
            self.jobs.add(identifier)
        root = self.root / 'publish' / identifier
        root.mkdir(parents=True, exist_ok=True)
        out_directory = Path(self.report_directory) / 'pocket'
        tools = PROJECT / 'tools' / 'pocket'
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        log_path = root / 'publish.log'
        job = {'id': identifier, 'status': 'queued', 'message': 'Preparing the snapshot.',
               'datasets': datasets, 'output_path': str(out_directory / 'mentat-pocket.html'),
               'console_pid': os.getpid(), 'started_at': time.time(), 'finished_at': None}
        atomic_json(root / 'job.json', job)

        def step(script, arguments, log):
            process = subprocess.Popen([sys.executable, str(tools / script)] + arguments, stdout=log,
                                       stderr=subprocess.STDOUT, creationflags=flags)
            job['pid'] = process.pid
            atomic_json(root / 'job.json', job)
            return process.wait()

        def publish():
            failure = ''
            try:
                out_directory.mkdir(parents=True, exist_ok=True)
                job.update(status='running', message='Reading the published report through this console.')
                atomic_json(root / 'job.json', job)
                with log_path.open('w', encoding='utf-8') as log:
                    if step('extract_pocket_data.py', ['--port', str(port), '--out-dir', str(out_directory),
                                                       '--datasets', ','.join(datasets)], log):
                        failure = 'The snapshot reader did not finish. See ' + str(log_path)
                    else:
                        job.update(message='Building the page.')
                        atomic_json(root / 'job.json', job)
                        if step('build_page.py', ['--data', str(out_directory / 'pocket-data.json'),
                                                  '--out', job['output_path']], log):
                            failure = 'The page could not be built from the snapshot. See ' + str(log_path)
            except OSError as error:
                failure = 'The publisher could not be started: ' + str(error)
            if not failure and not Path(job['output_path']).is_file():
                failure = 'The page was not written. See ' + str(log_path)
            job.update(status='failed' if failure else 'done',
                       message=failure or ('Snapshot published to ' + job['output_path']),
                       finished_at=time.time())
            atomic_json(root / 'job.json', job)

        def guarded():
            try:
                publish()
            finally:
                self.jobs.discard(identifier)

        threading.Thread(target=guarded, daemon=True).start()
        return {'job': job}

    def publication(self, identifier):
        """The stored state of one publication, or None when there is no such job.

        A console that dies mid-publish leaves 'running' on disk forever, so a
        state whose owning console is gone is reported failed. The owner is
        checked, not the child: between the child exiting and this thread
        writing 'done' the child pid is already dead and the job is fine.
        """
        if not re.fullmatch(r'publish-[a-f0-9]{32}', identifier or ''):
            raise ValueError('That is not a phone snapshot publication.')
        job = read_json(self.root / 'publish' / identifier / 'job.json')
        if job.get('id') != identifier:
            return None
        if job.get('status') in ('queued', 'running') and not process_alive(job.get('console_pid')):
            job['status'] = 'failed'
            job['message'] = 'The console that was publishing this snapshot is no longer running.'
        return job

`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  files: [{
    path: 'server.py',
    edits: [
      // 1. The console learns its own port; main() fills it in.
      {find: '        self.read_only = read_only\n',
       replace: '        self.read_only = read_only\n' +
                '        # The pocket publisher reads this console over HTTP, so the console\n' +
                "        # needs the port it was given. main() sets it before serve_forever.\n" +
                '        self.port = 0\n'},

      // 2. The method, beside collect_evidence in the job section.
      {find: '    def runs(self):\n        values = []\n',
       replace: METHOD + '    def runs(self):\n        values = []\n'},

      // 3. GET route.
      {find: "            if parsed.path == '/api/studio/briefing':\n",
       replace:
        "            if parsed.path == '/api/publish/pocket':\n" +
        "                job = app.publication(query.get('id', [''])[0])\n" +
        '                if job is None:\n' +
        "                    return self.send({'error': 'That publication is not on this console.'}, 404)\n" +
        '                return self.send(job)\n' +
        "            if parsed.path == '/api/studio/briefing':\n"},

      // 4. POST route.
      {find: "            if self.path == '/api/studio/briefing/add':\n",
       replace:
        "            if self.path == '/api/publish/pocket':\n" +
        '                return self.send(self.server.app.publish_pocket(data))\n' +
        "            if self.path == '/api/studio/briefing/add':\n"},

      // 5. main() hands the console the port it parsed.
      {find: '    server.app = Console(data_root, keys_file, rscript, options.read_only)\n',
       replace: '    server.app = Console(data_root, keys_file, rscript, options.read_only)\n' +
                '    server.app.port = options.port or server.server_port\n'}
    ]
  }]
};
