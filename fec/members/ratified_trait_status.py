"""Owner-ratified evidence status of each broad Big Five trait in data/stance/big5_gold_anchored.json.

The validator (b5_gold_multitrait_validate.py) computes a status from the frozen external panels on every run.  A computed
status may fall below the ratified one (that is published as computed), but it may never rise above it: a two-panel pass
that appears only because the current-roster sample changed is not independent validation.  The computed value is kept in
the artifact as `computed_status`.

Promotion is a deliberate edit of RATIFIED_STATUS by the owner (Paul), with the decision id cited in the commit.  The map is
the expectation audit_full.py pinned at :1396-1400 since before 0fd69cb4f (2026-08-04); the owner's 2026-10-22 rule (relayed
in reliability Task 2, audits/reliability_2026-10/decisions_applied.md) keeps Openness at one panel.  Status is a label: every
numeric consumer gates on the ACTIVE_ prefix only, which both active levels share.
"""

RATIFIED_STATUS = {
    'O': 'ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED',
    'C': 'ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED',
    'E': 'ACTIVE_EXTERNAL_GOLD_ANCHORED',
    'A': 'ACTIVE_EXTERNAL_GOLD_ANCHORED',
    'N': 'ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED',
}
_LEVEL = {'WITHHELD_FAILED_GATES': 0, 'ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED': 1, 'ACTIVE_EXTERNAL_GOLD_ANCHORED': 2}


def published_status(trait, computed):
    """The computed status, capped at the trait's ratified level."""
    ratified = RATIFIED_STATUS[trait]
    return ratified if _LEVEL[computed] > _LEVEL[ratified] else computed
