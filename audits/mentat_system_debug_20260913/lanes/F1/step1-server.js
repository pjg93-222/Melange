/* F1 step 1 - server.py: build identity block, busy state, health/session
   build fields, POST /api/restart. server.py is pure CRLF. */
'use strict';

const buildBlock = String.raw`from runtime_inputs import copy_fec_sources

# Files this console serves. Hoisted out of the request handler so the build
# identity below can hash exactly the set the browser can ask for.
STATIC_ASSETS = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript"),
                 '/contribution-studio': ('contribution-studio.html', 'text/html; charset=utf-8'),
                 '/contribution-studio.css': ('contribution-studio.css', 'text/css'),
                 '/contribution-studio.js': ('contribution-studio.js', 'text/javascript'),
                 '/contribution-plot.js': ('contribution-plot.js', 'text/javascript'),
                 '/contribution-charts.js': ('contribution-charts.js', 'text/javascript'),
                 '/contribution-map.js': ('contribution-map.js', 'text/javascript'),
                 '/mentat-icon.svg': ('mentat-icon.svg', 'image/svg+xml'),
                 "/style.css": ("style.css", "text/css"), "/template.csv": ("template.csv", "text/csv"),
                 '/workspace.css': ('workspace.css', 'text/css'),
                 '/evidence-csv.js': ('evidence-csv.js', 'text/javascript'),
                 '/charts.js': ('charts.js', 'text/javascript'), '/chart-math.js': ('chart-math.js', 'text/javascript'),
                 '/graph.js': ('graph.js', 'text/javascript'),
                 '/ui-state.js': ('ui-state.js', 'text/javascript'),
                 '/coverage-view.js': ('coverage-view.js', 'text/javascript'),
                 '/cross-reference.js': ('cross-reference.js', 'text/javascript'),
                 '/cross-reference.css': ('cross-reference.css', 'text/css'),
                 '/comparison.js': ('comparison.js', 'text/javascript'),
                 '/grouped-chart.js': ('grouped-chart.js', 'text/javascript'),
                 '/funding-comparison.js': ('funding-comparison.js', 'text/javascript'),
                 '/comparison.css': ('comparison.css', 'text/css'),
                 '/chart-export.js': ('chart-export.js', 'text/javascript'),
                 '/graph.css': ('graph.css', 'text/css'),
                 '/acu-theme.css': ('acu-theme.css', 'text/css'),
                 '/chart-studio-core.js': ('chart-studio-core.js', 'text/javascript'),
                 '/chart-studio-contributions.js': ('chart-studio-contributions.js', 'text/javascript'),
                 '/chart-studio.js': ('chart-studio.js', 'text/javascript'),
                 '/chart-comparison.js': ('chart-comparison.js', 'text/javascript'),
                 '/chart-studio.css': ('chart-studio.css', 'text/css'),
                 '/theme.js': ('theme.js', 'text/javascript')}

# Build identity. A console window outlives edits to this tree, so the page and
# the launcher both compare what this process loaded with what is on disk now.
# File names are folded into the tree hash, so a rename changes it too.


@lru_cache(maxsize=512)
def file_digest(identity):
    """SHA-256 of one file, cached by (path, size, mtime_ns)."""
    try:
        return hashlib.sha256(Path(identity[0]).read_bytes()).digest()
    except OSError:
        return b'file unavailable'


def tree_sha256(paths):
    digest = hashlib.sha256()
    for path in paths:
        try:
            info = path.stat()
            identity = (str(path), info.st_size, info.st_mtime_ns)
        except OSError:
            identity = (str(path), -1, -1)
        digest.update(path.name.encode('utf-8'))
        digest.update(b'\0')
        digest.update(file_digest(identity))
        digest.update(b'\0')
    return digest.hexdigest()


def code_files():
    """Every Python module this console loads from its own folder."""
    return sorted(Path(__file__).resolve().parent.glob('*.py'), key=lambda path: path.name)


def asset_files():
    directory = Path(__file__).resolve().parent
    return sorted({directory / name for name, _ in STATIC_ASSETS.values()}, key=lambda path: path.name)


def git_sha():
    """Short revision of the checkout, or 'unknown' when Git cannot answer."""
    try:
        finished = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=str(PROJECT),
                                  capture_output=True, text=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 'unknown'
    value = (finished.stdout or '').strip()
    return value if finished.returncode == 0 and re.fullmatch(r'[0-9a-f]{4,40}', value) else 'unknown'


CODE_TREE_SHA256 = tree_sha256(code_files())
ASSET_TREE_SHA256 = tree_sha256(asset_files())
GIT_SHA = git_sha()
STARTED_AT = time.time()


def console_busy(app):
    """Whether this console owns work a restart would interrupt.

    A console that cannot answer is reported busy: never stop work on a guess.
    """
    reader = getattr(app, 'busy', None)
    if not callable(reader):
        return False
    try:
        return bool(reader())
    except Exception:
        return True


def build_status(app, port):
    """What this process loaded, beside what is on disk right now."""
    return {'git_sha': GIT_SHA, 'code_sha256': CODE_TREE_SHA256, 'assets_sha256': ASSET_TREE_SHA256,
            'on_disk_code_sha256_now': tree_sha256(code_files()),
            'on_disk_assets_sha256_now': tree_sha256(asset_files()),
            'started_at': STARTED_AT, 'port': int(port), 'pid': os.getpid(),
            'busy': console_busy(app)}


@lru_cache(maxsize=64)
def static_asset(file_stamp):`;

const consoleMethods = String.raw`        if configured and not read_only:
            save_keys(configured)

    def busy(self):
        """True while this console owns work that stopping it would interrupt."""
        if self.preparing or self.jobs:
            return True
        return any(process.poll() is None for process in list(self.processes.values()))

    def restart(self, port):
        """Hand this console's port back to the launcher, which replaces it.

        The launcher stops this process only after it confirms the identity,
        the code hash and an idle busy flag, then binds the same port again.
        """
        script = Path(__file__).resolve().parent / 'Start-MentatApp.ps1'
        if not script.is_file():
            raise ValueError('The launcher script is unavailable. Close this window and open MENTAT again.')
        shell = shutil.which('powershell') or str(Path(os.environ.get('SystemRoot', 'C:/Windows'))
                                                  / 'System32/WindowsPowerShell/v1.0/powershell.exe')
        command = [shell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script),
                   '-NoBrowser', '-Port', str(int(port)), '-DataRoot', self.configured_root]
        # Identity is project path plus data root; a restart that dropped the
        # data root would open a second console on another port instead.
        if self.keys_file:
            command += ['-KeysFile', self.keys_file]
        if self.rscript:
            command += ['-RScriptPath', self.rscript]
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        try:
            subprocess.Popen(command, cwd=str(PROJECT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True, creationflags=flags)
        except OSError:
            raise ValueError('The launcher could not be started. Close this window and open MENTAT again.')
        return {'restarting': True, 'port': int(port), 'pid': os.getpid()}

    def inspect_report(self, path):`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'server.py',
    eol: 'crlf',
    edits: [
      // 1. Static asset map + build identity helpers at module level.
      {find: 'from runtime_inputs import copy_fec_sources\n\n\n@lru_cache(maxsize=64)\ndef static_asset(file_stamp):',
       replace: buildBlock},
      // 2. Console tracks its own background jobs so busy is answerable.
      {find: '        self.processes = {}\n        self.preparing = set()',
       replace: '        self.processes = {}\n        self.preparing = set()\n        self.jobs = set()'},
      // 3. Console.busy and Console.restart.
      {find: '        if configured and not read_only:\n            save_keys(configured)\n\n    def inspect_report(self, path):',
       replace: consoleMethods},
      // 4. Evidence collection counts as work; the finally keeps busy honest.
      {find: '        threading.Thread(target=collect, daemon=True).start()\n        return {\'id\':identifier, \'state\':\'collecting\'}',
       replace: '        def run_collect():\n            try:\n                collect()\n            finally:\n                self.jobs.discard(identifier)\n        self.jobs.add(identifier)\n        threading.Thread(target=run_collect, daemon=True).start()\n        return {\'id\':identifier, \'state\':\'collecting\'}'},
      // 5. /api/health carries the build block.
      {find: "                return self.send({'application': 'MENTAT', 'project': str(PROJECT),\n" +
             "                                  'data_root': app.configured_root,\n" +
             "                                  'resolved_data_root': str(app.root),\n" +
             "                                  'server_code_sha256': SERVER_CODE_SHA256,\n" +
             "                                  'contribution_studio_revision': CONTRIBUTION_STUDIO_REVISION,\n" +
             "                                  'read_only': bool(getattr(app, 'read_only', False)),\n" +
             "                                  'report_directory':str(app.report_directory), 'pid': os.getpid()})",
       replace: "                return self.send({'application': 'MENTAT', 'project': str(PROJECT),\n" +
             "                                  'data_root': app.configured_root,\n" +
             "                                  'resolved_data_root': str(app.root),\n" +
             "                                  'server_code_sha256': SERVER_CODE_SHA256,\n" +
             "                                  'contribution_studio_revision': CONTRIBUTION_STUDIO_REVISION,\n" +
             "                                  'read_only': bool(getattr(app, 'read_only', False)),\n" +
             "                                  'report_directory':str(app.report_directory),\n" +
             "                                  **build_status(app, self.server.server_port)})"},
      // 6. The light session carries the same block, so the page needs no extra request.
      {find: "                    return self.send({'token':app.token, 'read_only':bool(getattr(app, 'read_only', False)),\n" +
             "                                      'evidence_collection_available':True, 'api_version':2,\n" +
             "                                      'report_directory':str(app.report_directory)})",
       replace: "                    build = build_status(app, self.server.server_port)\n" +
             "                    return self.send({'token':app.token, 'read_only':bool(getattr(app, 'read_only', False)),\n" +
             "                                      'evidence_collection_available':True, 'api_version':2,\n" +
             "                                      'report_directory':str(app.report_directory), 'build': build, **build})"},
      // 7. The handler reads the hoisted map.
      {from: '            assets = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript"),',
       to: '            if parsed.path in assets:',
       replace: '            assets = STATIC_ASSETS\n'},
      // 8. POST /api/restart. Read-only consoles are refused by the guard above.
      {find: "            if self.path == '/api/contributions/geography':\n" +
             "                return self.send(contribution_geo.geography(data))\n" +
             '            if self.path == "/api/upload":',
       replace: "            if self.path == '/api/contributions/geography':\n" +
             "                return self.send(contribution_geo.geography(data))\n" +
             "            if self.path == '/api/restart':\n" +
             "                if console_busy(self.server.app):\n" +
             "                    return self.send({'error': 'This console is still running collection work. Restart it once that finishes.'}, 409)\n" +
             "                return self.send(self.server.app.restart(self.server.server_port))\n" +
             '            if self.path == "/api/upload":'}
    ]
  }]
};
