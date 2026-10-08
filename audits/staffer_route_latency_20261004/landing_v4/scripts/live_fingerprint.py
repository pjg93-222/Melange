"""Read-only fingerprint of the parts of LIVE this work reads: HEAD, the full `git status --porcelain` text, and (relative path, size, mtime_ns) of every
file under the directories the two patch sets touch. Printed as one digest per part so a before/after pair can be compared. Writes nothing in LIVE."""
import hashlib, os, subprocess, sys
LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
head = subprocess.run(['git', '-C', LIVE, 'rev-parse', 'HEAD'], capture_output=True, env=env).stdout.decode().strip()
status = subprocess.run(['git', '-C', LIVE, 'status', '--porcelain=v1', '-uall'], capture_output=True, env=env).stdout
rows = []
for sub in ('fec/surfaces', 'fec/tests/surfaces', 'fec/tools'):
    for folder, dirs, names in os.walk(os.path.join(LIVE, *sub.split('/'))):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'approved')] if False else [d for d in dirs if d != '__pycache__']
        for name in names:
            path = os.path.join(folder, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            rows.append('%s|%d|%d' % (os.path.relpath(path, LIVE).replace(os.sep, '/'), st.st_size, st.st_mtime_ns))
rows.sort()
print('HEAD', head)
print('status lines', len(status.splitlines()), 'sha256', hashlib.sha256(status).hexdigest()[:16])
print('files fingerprinted', len(rows), 'sha256', hashlib.sha256('\n'.join(rows).encode()).hexdigest()[:16])
if '--list' in sys.argv:
    print('\n'.join(rows))
