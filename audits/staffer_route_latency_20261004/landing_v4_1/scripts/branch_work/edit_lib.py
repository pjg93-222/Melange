"""Exact, anchored edits of worktree files that keep their line endings (v4.1 fix round).

edit(path, [(old, new), ...]) works on LF text and writes the file's own terminator back: a pure-CRLF file stays pure CRLF, a pure-LF file stays pure LF,
and a file that is neither is refused (the worktree's files are git-checkout CRLF). Every `old` must occur exactly once or nothing is written.
create(path, text) writes a new file with CRLF (the worktree's checkout convention; the git blob is LF either way).
"""
import os
import sys


def _profile(raw):
    crlf = raw.count(b'\r\n')
    lf = raw.count(b'\n') - crlf
    lone = raw.count(b'\r') - crlf
    return crlf, lf, lone


def edit(path, pairs):
    raw = open(path, 'rb').read()
    assert not raw.startswith(b'\xef\xbb\xbf'), path
    crlf, lf, lone = _profile(raw)
    assert lone == 0 and (crlf == 0 or lf == 0), '%s is not pure CRLF or pure LF (crlf=%d lf=%d lone_cr=%d)' % (path, crlf, lf, lone)
    use_crlf = crlf > 0
    text = raw.decode('utf-8')
    norm = text.replace('\r\n', '\n') if use_crlf else text
    for old, new in pairs:
        count = norm.count(old)
        assert count == 1, '%s: anchor found %d times: %r' % (os.path.basename(path), count, old[:100])
        assert old != new
        norm = norm.replace(old, new)
    out = (norm.replace('\n', '\r\n') if use_crlf else norm).encode('utf-8')
    c2, l2, lone2 = _profile(out)
    assert lone2 == 0 and (c2 == 0 or l2 == 0) and (c2 > 0) == use_crlf, 'line-ending class changed in %s' % path
    with open(path, 'wb') as handle:
        handle.write(out)
    print('%-70s %s  (crlf %d -> %d)' % (os.path.relpath(path), 'CRLF' if use_crlf else 'LF', crlf, c2 or l2))


def create(path, text):
    assert not os.path.exists(path), path
    assert '\r' not in text
    with open(path, 'wb') as handle:
        handle.write(text.replace('\n', '\r\n').encode('utf-8'))
    print('created %s' % path)


if __name__ == '__main__':
    sys.exit('library only')
