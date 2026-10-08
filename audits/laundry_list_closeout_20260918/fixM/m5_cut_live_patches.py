# -*- coding: utf-8 -*-
"""Cut the LIVE-side hooks for A5 and N2 as byte-exact unified patches.

fec/stance/build_media_blend.py is DRIFTED: LIVE (480 lines) is the production copy, main
is 467, and LIVE carries mixed line endings (433 CRLF + 47 bare LF).  So the worktree copy
is never edited: LIVE's bytes are copied to SCRATCH, the hook is applied there by exact
byte substitution, and the diff is cut LIVE-original -> LIVE-patched.

The diff is produced with difflib over lines read with ``newline=''``, so every content
line keeps its OWN terminator and the control lines end with a bare LF -- the same shape
git itself emits, and the same shape the existing N4_sponsor_column_live_hook.patch has.
The patch is written in binary: nothing passes through a text-mode pipe on this cp1252
console.  READ-ONLY with respect to LIVE.
"""
import difflib
import io
import os
import sys

LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
SCRATCH = (r"C:\Users\pgoff\AppData\Local\Temp\claude"
           r"\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-"
           r"unfinished-work-handoff-a3bbad"
           r"\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\fixM")
PATCHES = os.path.join(WT, "audits", "laundry_list_closeout_20260918", "patches")
REL = "fec/stance/build_media_blend.py"
TEST_REL = "fec/tests/stance/test_crosspost_key_engine_wiring.py"
os.makedirs(SCRATCH, exist_ok=True)

ORIGINAL = io.open(os.path.join(LIVE, REL.replace("/", os.sep)), "rb").read()
print("LIVE %s: %d bytes, %d CRLF, %d bare LF"
      % (REL, len(ORIGINAL), ORIGINAL.count(b"\r\n"),
         ORIGINAL.count(b"\n") - ORIGINAL.count(b"\r\n")))

# ---------------------------------------------------------------- N2: the engine key -----
# NOTE the terminators: this producer has MIXED line endings (433 CRLF + 47 bare LF).  The
# _event= line and its neighbours are CRLF; the _tone_rows= line and the meta dict are bare
# LF.  Each inserted line therefore carries the terminator its NEIGHBOURS carry, so the file
# keeps exactly the mix it has today.
CR = b"\x0d"
NL = b"\x0a"


def crlf(lines):
    return b"".join(line + CR + NL for line in lines)


def lf(lines):
    return b"".join(line + NL for line in lines)


N2_OLD = crlf([b"    _event=(_member,MR.normalized_text(r['text']))"])
N2_NEW = crlf([
    b"    # N2 (2026-09-19, packet audits/laundry_list_closeout_20260918 FINDINGS.md A3): the",
    b"    # duplicate key is the WHOLE normalised statement, not MR.normalized_text's first 120",
    b"    # characters. 445 of 1,434 groups (9,502-row scope) were FALSE collisions on a shared",
    b"    # prefix, so at CROSSPOST_DEDUP=1 those rows would be dropped as duplicates of posts",
    b"    # they are not. MR.normalized_text stays the tweet_stance_final join key at _nrm above,",
    b"    # untouched. CROSSPOST_KEY_CHARS=120 restores the old key; CROSSPOST_DEDUP is unchanged.",
    b"    _event=(_member,MR.crosspost_key(r['text']))"])

# ---------------------------------------------------------------- A5: the ingest ledger --
A5_OLD_CALL = lf([b"    _tone_rows=_load_press_tone_rows()"])
A5_NEW_CALL = lf([
    b"    # A5 (2026-09-19, packet audits/laundry_list_closeout_20260918 FINDINGS.md A5):",
    b"    # load_tone_rows now collapses one release ingested under two URL forms",
    b"    # (PRESS_URL_CANON, default 2). The collapsed rows are NOT lost from the accounting:",
    b"    # the ledger names each one, so rows_read still closes to rows_returned +",
    b"    # official_mention + no_url + exact_url_turn + duplicate_url_form.",
    b"    _tone_ingest={}",
    b"    _tone_rows=_load_press_tone_rows(ledger=_tone_ingest)"])
A5_OLD_META = lf([b"         'tone_sources':_tone_sources,'tone_rows':len(_tone_rows),"])
A5_NEW_META = lf([b"         'tone_sources':_tone_sources,'tone_rows':len(_tone_rows),",
                  b"         'tone_ingest_dedup':_tone_ingest,"])


def substitute(source, pairs):
    out = source
    for old, new in pairs:
        count = out.count(old)
        if count != 1:
            sys.exit("REFUSED: anchor appears %d times, expected 1:\n%r" % (count, old))
        out = out.replace(old, new)
    return out


def cut(name, patched, extra_files=()):
    """LIVE-original -> LIVE-patched, plus any whole new files, as one unified patch."""
    scratch_path = os.path.join(SCRATCH, name + ".build_media_blend.py")
    io.open(scratch_path, "wb").write(patched)
    before = io.open(os.path.join(LIVE, REL.replace("/", os.sep)), "r",
                     encoding="utf-8", newline="").readlines()
    after = io.open(scratch_path, "r", encoding="utf-8", newline="").readlines()
    body = ["diff --git a/%s b/%s\n" % (REL, REL)]
    body += list(difflib.unified_diff(before, after, fromfile="a/" + REL,
                                      tofile="b/" + REL, lineterm="\n"))
    for rel, path in extra_files:
        lines = io.open(path, "r", encoding="utf-8", newline="").readlines()
        body.append("diff --git a/%s b/%s\n" % (rel, rel))
        body.append("new file mode 100644\n")
        body.append("--- /dev/null\n")
        body.append("+++ b/%s\n" % rel)
        body.append("@@ -0,0 +1,%d @@\n" % len(lines))
        body += ["+" + line for line in lines]
        if lines and not lines[-1].endswith("\n"):
            body.append("\n\\ No newline at end of file\n")
    target = os.path.join(PATCHES, name)
    io.open(target, "wb").write("".join(body).encode("utf-8"))
    raw = io.open(target, "rb").read()
    print("\nwrote %s  (%d bytes, %d CRLF content lines, %d hunks)"
          % (name, len(raw), raw.count(b"\r\n"), "".join(body).count("\n@@ ")
             + int("".join(body).startswith("@@ "))))
    return target


n2_only = substitute(ORIGINAL, [(N2_OLD, N2_NEW)])
a5_only = substitute(ORIGINAL, [(A5_OLD_CALL, A5_NEW_CALL), (A5_OLD_META, A5_NEW_META)])
both = substitute(ORIGINAL, [(N2_OLD, N2_NEW), (A5_OLD_CALL, A5_NEW_CALL),
                             (A5_OLD_META, A5_NEW_META)])
for label, patched in (("N2", n2_only), ("A5", a5_only), ("both", both)):
    assert patched != ORIGINAL
    assert b"def _nrm(t): return MR.normalized_text(t)" in patched, label
    assert b"DEDUP=os.environ.get('CROSSPOST_DEDUP','0')=='1'" in patched, label
    assert b"_dupe=_event in _seen" in patched, label
    assert b"elif not _event[1]: nlinkonly+=1; continue" in patched, label
print("guards OK: _nrm, CROSSPOST_DEDUP default, and the lifted dedup block are all intact")

wiring = os.path.join(WT, "audits", "laundry_list_closeout_20260918", "fixM",
                      "test_crosspost_key_engine_wiring.py.new")
cut("N2_crosspost_key_live_hook.patch", n2_only, [(TEST_REL, wiring)])
cut("A5_press_ledger_live_hook.patch", a5_only)
cut("M_both_live_hooks.patch", both, [(TEST_REL, wiring)])
print("\nDONE M5")
