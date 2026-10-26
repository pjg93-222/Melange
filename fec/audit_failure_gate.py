# -*- coding: utf-8 -*-
"""KNOWN Paul-gated audit_full dissent — the ONE parser both unattended gates share.

audit_full.py exits 1 whenever ANY check fails (fec\\audit\\audit_full.py:2214-2217), and the
list below plus its companion pattern list are STANDING open items blocked on Paul's decisions,
not on code. Two independent unattended callers have to decide "is this the known dissent, or
novel breakage?":

  * fec\\weekly_refresh.py  — GATE-1's chain step (run_pipeline's tail is audit_full).
  * fec\\collect\\collector_supervisor.py — GATE-2 runs audit_full directly as its last step.

This module exists so that decision has exactly ONE implementation and ONE list. Duplicating
KNOWN_GATED_FAILURES into the supervisor would make the two gates able to disagree about which
failures are ratified, and a name added in one place would silently not apply in the other.

Everything here fails CLOSED: a report that cannot be read as complete and self-consistent is
treated as novel breakage, because a report we cannot read proves nothing. Import cost is stdlib
only — the supervisor imports this on every 10-minute tick; the two D-330 condition checks read
files only when one of their names is actually failing.

CALLER OBLIGATION (not enforceable here): tolerating audit_full's verdict is only safe when every
PRODUCER has already run, so the audit's dissent cannot be masking unrun work. weekly_refresh
proves that with its chain-tail guard (_chain_tail_is_audit_full); collector_supervisor's GATE-2
satisfies it by construction — audit_full is its last gate_step and every earlier step's result is
already in the required-dict.
"""
import ast
import hashlib
import json
import os
import re
import time

# audit_full.py is the LAST step of run_pipeline's CHAIN (fec\run_pipeline.py:135) and the LAST
# step of collector_supervisor's GATE-2, so when it is the step that fails, every PRODUCER has
# already succeeded: ranks, workbook and dashboards are freshly written and the only dissent is the
# audit's own verdict. Paul's manual chain runs treat "202 passed, 1 FAILED with the legfix5
# culling item" as the documented healthy baseline, because that promotion is blocked on HIS
# 19-category membership review, not on code. Aborting the whole unattended refresh on it froze the
# UI for five weeks (2026-07-26..08-23).
# Each entry is the EXACT ck() name audit_full prints, copied from source — never inferred:
KNOWN_GATED_FAILURES = (
    # User 2026-09-08, replying to the exact missing rescue-folder question:
    # "Oh backups are done, don't bother". These four old local paths are outside
    # the refresh gate. The audit still reports their absence; this is not backup
    # verification and does not waive loss of any current source or scoring file.
    'A1 repo.rescue_dir still exists',
    'A1 repo.rescue_manifest_a still exists',
    'A1 repo.rescue_manifest_b still exists',
    'A1 repo.rescue_manifest_c still exists',
    'culling surface reports the hash-bound production promotion state',   # fec\audit\audit_full.py:1642
    # ratified by Paul 2026-09-05; schema-only mismatch (the desk adds a display_dedupe block; the
    # 480 texture payloads are byte-identical, dashboard-fixes lane 2026-09-05); UN-GATE when the
    # check is narrowed to the texture payload or the desk stops adding the block; the audit check
    # stays live and visible.
    'personal-texture layer propagates exactly to member profiles (display-only)',
    # ratified by Paul 2026-09-05; today's failure is sources=False intake=False (the press engine
    # feed's source-run and intake bindings), which the sentinel-collectors lane's unmerged repair
    # branch claude/sentinel-collectors-progress-f7de7d addresses; UN-GATE when that branch is
    # merged and build_press_engine_feed.py rebuilt; the audit check stays live and visible.
    'press refresh feed is hash-bound and keeps official mentions out of stance/speech',
)
# The two D-330 tolerances are NOT in KNOWN_GATED_FAILURES: each audit_full check below is a
# conjunction of several sub-conditions, and D-330 adjudicated exactly ONE sub-condition of each.
# Tolerating the whole name would also waive the others (hash binding, candidate-only status,
# partition completeness, no active writes; a malformed receipt; any other tolerated step going
# stale). So each name is tolerated only when a read-only re-derivation of the check from the same
# live files finds that the adjudicated sub-condition is the ONLY one failing. Any other failing
# sub-condition, an unreadable file, or a failure the re-derivation cannot explain = NOVEL.
INTAKE_CHECK = 'accepted audio manifest is fully partitioned into a candidate-only review intake'
CTF_CHECK = 'chain_tolerated_failures'
# D-330 ruling 8: tolerate the age of THIS last-good longform artifact (mtime 2026-09-05T20:58:27Z,
# 47 d at attempt 9) until the re-bind after attempt 10. The tolerance is pinned to the artifact's
# bytes, so it EXPIRES BY ITSELF: the re-bind writes a new artifact, its hash no longer matches, and
# from then on the 21-day age limit binds the longform step like every other tolerated step.
LONGFORM_STEP = 'build_member_longform_turn_features.py'
LONGFORM_LAST_GOOD_SHA256 = '02da7ca4884066f3a6e046e5e92e8a5b90f5681ab095862e25352fb9101dbc39'
CTF_MAX_AGE_DAYS = 21   # mirrors fec\audit\audit_full.py _CTF_MAX_AGE_DAYS


def _root(root=None):
    # Same resolution as fec\paths.py ROOT (audit_full's B), without importing it.
    return os.path.abspath(root or os.environ.get('MONEYBALL_ROOT')
                           or os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _intake_only_rejected(root):
    """D-330 attempt-9 residual: collection_intake REJECTED, tolerated until the media gate passes.
    Mirrors fec\\audit\\audit_full.py (the 'accepted audio manifest ...' ck). Tolerated only when the
    intake receipt's status is exactly REJECTED and EVERY other conjunct of that check holds."""
    intake = _load_json(os.path.join(root, 'data', 'engine', 'collection_intake_receipt.json'))
    cand = _load_json(os.path.join(root, 'data', 'members', 'b5_audio_reviews_v2.json.candidate'))
    if not isinstance(intake, dict) or not isinstance(cand, dict):
        return False, 'intake receipt or audio candidate is not an object'
    if intake.get('status') != 'REJECTED':
        return False, 'intake status is %r, not the adjudicated REJECTED' % (intake.get('status'),)
    part = cand.get('partition') or {}
    src = cand.get('source_manifest') or {}
    manifest = src.get('path') or ''
    expected = int(((intake.get('house') or {}).get('all_clip_rows')) or -1)
    queued, excluded, total = part.get('queued'), part.get('excluded'), part.get('total')
    others = (
        ('candidate schema', cand.get('schema') == 'b5-audio-review-v2-candidate'),
        ('candidate-only status',
         cand.get('status') == 'CANDIDATE_ONLY_CONSUMED_BY_NOTHING_AWAITING_DOUBLE_REVIEW'),
        ('intake schema', intake.get('schema') == 'collection-intake-receipt-v1'),
        ('manifest present', bool(manifest) and os.path.isfile(manifest)),
        ('candidate hash binds the manifest',
         bool(manifest) and os.path.isfile(manifest) and src.get('sha256') == _sha256(manifest)),
        ('intake hash binds the candidate',
         bool(src.get('sha256')) and (intake.get('inputs') or {}).get('clip_manifest_sha256') == src.get('sha256')),
        ('partition total', total == expected),
        ('partition complete', all(isinstance(v, int) and not isinstance(v, bool) for v in (queued, excluded, total))
         and queued + excluded == total),
        ('no active artifact writes', (cand.get('contract') or {}).get('active_artifacts_written') is False),
    )
    bad = [n for n, ok in others if not ok]
    if bad:
        return False, 'intake REJECTED but also failing: %s' % ', '.join(bad)
    return True, 'only the adjudicated intake status REJECTED'


def _ctf_only_adjudicated_longform_age(root):
    """D-330 ruling 8. Mirrors fec\\audit\\audit_full.py's chain_tolerated_failures ck. Tolerated only
    when the receipt is well-formed, every tolerated step's last-good artifact exists, and the ONLY
    entry over the age limit is the longform step serving the adjudicated (pinned) artifact."""
    receipt = os.path.join(root, 'data', 'engine', 'chain_tolerated_failures.json')
    if not os.path.exists(receipt):
        return False, 'receipt absent, so the check cannot be failing on the longform age'
    entries = _load_json(receipt)
    if not isinstance(entries, list):
        return False, 'receipt malformed'
    now = time.time(); adjudicated = 0
    for e in entries:
        if not isinstance(e, dict):
            return False, 'receipt entry malformed'
        step = str(e.get('step') or '?'); art = e.get('last_good_path')
        if not isinstance(art, str) or not os.path.isfile(art):
            return False, '%s: last-good artifact missing' % step
        if (now - os.path.getmtime(art)) / 86400.0 <= CTF_MAX_AGE_DAYS:
            continue
        if step != LONGFORM_STEP:
            return False, '%s: last-good artifact over %d days (not adjudicated)' % (step, CTF_MAX_AGE_DAYS)
        if _sha256(art) != LONGFORM_LAST_GOOD_SHA256:
            return False, '%s: stale artifact is not the adjudicated one (re-bound: tolerance expired)' % step
        adjudicated += 1
    if not adjudicated:
        return False, 'no adjudicated longform-age failure found'
    return True, 'only the adjudicated longform last-good age'


CONDITIONALLY_GATED_FAILURES = {
    # D-330 (Paul, 2026-10-26): attempt 9's collection_intake_receipt is REJECTED (media gate unmet);
    # tolerated until the media gate passes. UN-GATE then.
    INTAKE_CHECK: _intake_only_rejected,
    # D-330 ruling 8 (Paul, 2026-10-26): re-bind longform after attempt 10, tolerate the age until then.
    # Self-expiring (LONGFORM_LAST_GOOD_SHA256); remove this entry once the re-bind lands.
    CTF_CHECK: _ctf_only_adjudicated_longform_age,
}


def conditional_tolerance(name, root=None):
    """(tolerated, reason) for a CONDITIONALLY_GATED_FAILURES name. Fails CLOSED on any error."""
    predicate = CONDITIONALLY_GATED_FAILURES.get(name)
    if predicate is None:
        return False, 'not conditionally gated'
    try:
        return predicate(_root(root))
    except Exception as e:
        return False, 'condition unreadable (%s: %s)' % (type(e).__name__, str(e)[:160])
# DELIBERATELY NOT LISTED (these must keep aborting the refresh AND failing GATE-2):
#   'own-source channel inputs within 28 days of the corpus (channels are default-ON)'
#       — fec\audit\audit_full.py:627. A REAL staleness tripwire: it means a channel sidecar has
#         fallen 28+ days behind the corpus, i.e. the refresh would publish a stale-basis rank.
#   'qualified conversation roles v2 propagate exactly to the desk and remain engine-isolated'
#       — fec\audit\audit_full.py:1489. Never adjudicated as Paul-gated; treat as novel.
# Adding a name here is a change-control decision, not a maintenance edit.

# ratified by Paul 2026-09-05, NARROWED 2026-09-06. The A2 scale pattern is unchanged: a chain run
# still moves a store's size class and file count minutes before its own terminal audit.
#
# The A2b pattern is now an EXPLICIT TWO-STORE LIST, not a store-class alternation, because the
# 2026-09-05 un-gate condition ("exclude chain outputs from sentinel duty") is SATISFIED for every
# store the chain writes into: build_system_manifest's per-store sentinel_excludes/sentinel_newest
# take those paths out of sentinel candidacy, so repo.data_{stance,legislation,lobbying,network,
# members,money,engine} and repo.outputs and local.lda_derived must now go GREEN and any red there
# is NOVEL — most likely a new chain output that needs a sentinel_excludes entry.
#
# The two that remain are NOT chain-driven and were never covered by that condition:
#   local.billstatus — BILLSTATUS-119.receipt.json is written by weekly_refresh's GovInfo bulk
#     collector step; refresh_cosponsor_forecast.py (the only chain step touching that tree) merely
#     READS it (:146-151, :208-221) and puts its receipt under data\engine (path at :85).
#   glassbox.events  — the GLASS BOX runtime's own rolling event stream; no chain step writes it.
# UN-GATE local.billstatus when the collector lane stops pinning its receipt; un-gate
# glassbox.events when the events store's rotation is reflected in its sentinel selection.
# Adding a store to this pattern is a change-control decision, exactly like KNOWN_GATED_FAILURES.
KNOWN_GATED_PATTERNS = (
    re.compile(r'^A2 (?:repo|mdata|local|mirror|draft|glassbox)\.[A-Za-z0-9_.\-]+ (?:size_class agrees|file_count within tolerance)$'),
    re.compile(r'^A2b (?:local\.billstatus|glassbox\.events) sentinels unchanged$'),
)

_FAILURES_RE = re.compile(r'^\s*FAILURES:\s*(\[.*\])\s*$', re.M)
_TALLY_RE = re.compile(r'FULL-BODY AUDIT.{0,8}?(\d+) passed, (\d+) FAILED')


def pipeline_failure_output(script, stdout):
    """Preserve the complete terminal verdict for the scheduled failure gate."""
    stdout=stdout or ''
    if script=='audit_full.py':
        verdict=[line for line in stdout.splitlines()
                 if _TALLY_RE.search(line) or _FAILURES_RE.match(line)]
        if verdict:
            return '\n'.join(verdict)
    return stdout[-800:]


def audit_failures(stdout, stderr):
    """Parse audit_full's FAILURES list out of a caller's captured output.

    Returns (names, reason); names is None whenever the output cannot be read as a COMPLETE and
    SELF-CONSISTENT audit report. run_pipeline echoes only the last 800 chars of the audit's stdout
    (fec\\run_pipeline.py:317), so via GATE-1 a long failure list arrives front-truncated — the
    name-count-vs-tally cross-check below is what catches that. (GATE-2 runs audit_full directly
    and captures all of it, so the same parser is strictly better informed there.) Fail CLOSED."""
    blob = (stdout or '') + '\n' + (stderr or '')
    found = _FAILURES_RE.findall(blob)
    if not found:
        return None, 'no complete "FAILURES: [...]" line in the captured output'
    try:
        names = ast.literal_eval(found[-1])
    except Exception as e:
        return None, 'unparseable FAILURES list (%s)' % type(e).__name__
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        return None, 'FAILURES is not a non-empty list of strings'
    tally = _TALLY_RE.findall(blob)
    if not tally:
        return None, 'no "FULL-BODY AUDIT - N passed, M FAILED" tally in the captured output'
    if int(tally[-1][1]) != len(names):
        return None, ('tally says %s FAILED but %d name(s) parsed (output truncated?)'
                      % (tally[-1][1], len(names)))
    return names, ''


def tolerate_known_gated(stdout, stderr, log=print, prefix='   ', root=None):
    """Decide whether a non-zero audit_full result is ONLY the known Paul-gated dissent.

    Returns (tolerate, names). Every uncertain path returns tolerate=False. `log` is the caller's
    own logger so the decision lands in whichever unattended log the operator will actually read.
    `root` is the Moneyball root whose files the audit read (default: fec\\paths.py's ROOT); only the
    CONDITIONALLY_GATED_FAILURES names consult it."""
    names, reason = audit_failures(stdout, stderr)
    if names is None:
        log('%snot a readable audit failure report (%s) — abort stands' % (prefix, reason))
        return False, []
    novel = []; tags = {}
    for n in names:
        if n in KNOWN_GATED_FAILURES:
            tags[n] = ''
        elif any(p.match(n) for p in KNOWN_GATED_PATTERNS):
            tags[n] = ' (pattern)'
        elif n in CONDITIONALLY_GATED_FAILURES:
            ok, why = conditional_tolerance(n, root)
            if ok:
                tags[n] = ' (condition: %s)' % why
            else:
                novel.append('%s [%s]' % (n, why))
        else:
            novel.append(n)
    if novel:
        log('%sNOVEL audit failure(s) — abort stands:' % prefix)
        for n in novel:
            log('%s  NOVEL: %s' % (prefix, n))
        return False, names
    log('%sknown Paul-gated dissent only — tolerating:' % prefix)
    for n in names:
        log('%s  %s%s' % (prefix, n, tags[n]))
    return True, names
