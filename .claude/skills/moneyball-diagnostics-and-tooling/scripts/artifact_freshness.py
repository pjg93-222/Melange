# -*- coding: utf-8 -*-
"""artifact_freshness.py — mtime-ordering freshness check for derived artifacts
(read-only, stdlib-only; never imports fec modules).

Each derived artifact in the table below is produced by a pipeline/one-shot script
that READS the listed inputs. If an input's mtime is NEWER than the artifact's mtime,
the artifact may be stale (its producer has not been re-run since the input changed).

The table lists only PURE FILE-READ dependencies verified against producer source
(2026-07-09; paths re-verified and corrected 2026-08-25 against the 2026-08 data
reorg, which moved several artifacts out of the repo root into data/<domain>/
subfolders — producer scripts under fec/ were NOT relocated by that reorg).
Deliberately excluded:
  - ranks_python.json vs the workbook: the chain writes the workbook (sync_stance_g)
    AFTER compute_pillars, so the workbook is legitimately newer. Rank freshness is
    checked by `python fec/engine/compute_pillars.py` (PARITY: CLEAN) instead.
  - bipartisan.json / col-G two-run-convergence artifacts: they legitimately post-date
    their consumers by one chain run.

A STALE flag is a lead, not a verdict — confirm with the producer's docstring before
re-running anything (several producers are user-gated; electoral_plays.json in
particular is user-gated, and its 2026-07-09 STALE flag proved mtime-only on
2026-07-10 — the authorized rebuild was byte-identical).

Usage:
  python artifact_freshness.py "<live root>" [--tol SECONDS]

  <live root> = the data tree, e.g. "C:\\Users\\pgoff\\OneDrive\\Desktop\\Melange Systems"
  --tol       = mtime slack in seconds before flagging (default 2; OneDrive can skew stamps)
"""
import os, sys, time

# derived artifact -> (producer script, [input files it reads])
# every read verified at the cited producer, 2026-07-09
# paths below re-verified on disk 2026-08-25 (see module docstring); artifacts that
# moved under the 2026-08 reorg are keyed/listed by their current data/<domain>/ path
DEPS = {
    'member_receptivity.json': ('fec/members/receptivity_layer.py',
        ['data/engine/congestion.json', 'behavioral_dispositions.json', 'data/money/electoral.json',
         'data/money/electoral_plays.json']),
    'data/money/electoral_plays.json': ('fec/engine/build_electoral_plays.py  [USER-GATED re-run]',
        ['category_stance.json', 'data/money/electoral.json', 'data/engine/congestion.json']),
    'data/network/lt_priming.json': ('fec/engine/lt_priming.py',
        ['data/engine/congestion.json', 'category_stance.json']),
    'data/money/budget_frontier.json': ('fec/engine/budget_frontier.py',
        ['data/engine/congestion.json', 'category_stance.json', 'data/money/electoral.json',
         'data/money/electoral_plays.json', 'member_receptivity.json']),
    'data/money/budget_frontier_electoral.json': ('fec/engine/budget_frontier.py --electoral',
        ['data/engine/congestion.json', 'category_stance.json', 'data/money/electoral.json',
         'data/money/electoral_plays.json', 'member_receptivity.json']),
    'optimize_result.json': ('fec/engine/optimize.py',
        ['data/engine/congestion.json', 'category_stance.json', 'member_receptivity.json']),
    'im_allocation.json': ('fec/engine/build_im_allocation.py',
        ['per_topic_alloc.json', 'data/lobbying/per_topic_coalition.json']),
    'dashboard_data.json': ('fec/surfaces/build_dashboard_bundle.py',
        ['data/engine/congestion.json', 'category_stance.json', 'per_topic_alloc.json',
         'data/lobbying/per_topic_coalition.json', 'data/money/electoral_plays.json',
         'data/money/budget_frontier.json', 'optimize_result.json', 'salience_advisory.json']),
    'Moneyball Dashboard.html': ('fec/surfaces/make_dashboard_html.py',
        ['dashboard_data.json']),
    'data/network/kb_benchmark.json': ('fec/engine/kb_benchmark.py  [diagnostic, non-chain]',
        ['optimize_result.json']),
    'data/lobbying/signed_coalitions.json': ('fec/network/signed_coalitions.py  [diagnostic, non-chain]',
        ['member_references.json']),
}

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__); sys.exit(2)
    root = args[0]
    tol = 2.0
    if '--tol' in sys.argv:
        tol = float(sys.argv[sys.argv.index('--tol') + 1])
    if not os.path.isdir(root):
        print('not a directory: %s' % root); sys.exit(2)
    stale = fresh = missing = 0
    for art, (producer, inputs) in DEPS.items():
        apath = os.path.join(root, art)
        if not os.path.exists(apath):
            print('MISSING %-32s (producer: %s)' % (art, producer)); missing += 1
            continue
        amt = os.path.getmtime(apath)
        newer = []
        for inp in inputs:
            ipath = os.path.join(root, inp)
            if not os.path.exists(ipath):
                newer.append((inp, None)); continue
            imt = os.path.getmtime(ipath)
            if imt > amt + tol:
                newer.append((inp, imt - amt))
        if newer:
            stale += 1
            print('STALE   %-32s artifact %s' % (art, time.strftime('%Y-%m-%d %H:%M', time.localtime(amt))))
            for inp, d in newer:
                print('        input newer: %-28s %s' % (inp,
                      ('MISSING' if d is None else '+%.0f min' % (d / 60))))
            print('        producer: %s' % producer)
        else:
            fresh += 1
            print('fresh   %-32s' % art)
    print('\n%d fresh / %d stale / %d missing (tol %.0fs). STALE = re-check the producer '
          'before acting; some re-runs are user-gated.' % (fresh, stale, missing, tol))
    sys.exit(0)   # informational tool: staleness can be legitimate, so never a failing exit

if __name__ == '__main__':
    main()
