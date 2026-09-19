# Primacy → Efficiency → Volume

**Superseded candidate:** the user's corrected four-priority specification and final replay are in [Primacy → Efficiency → Substance → Volume](../pesv_implementation_20260913/README.md). This older package is retained as the record of the earlier conversion-rate proposal.

This package implements the revised candidate and produces an auditable comparison against the current CU board. It preserves production files and the frozen September 12 reports.

**Completed:** 58/58 tests; 533-member baseline reproduced; two byte-identical replays; zero tier membership changes. See the [implementation result](IMPLEMENTATION_RESULT.md) and [interactive comparison](generation_01/review.html).

- [Scoring and activation contract](ACTIVATION_CONTRACT_PEV_2026-09-13_v3.md)
- [Evidence corrections](EVIDENCE_CORRECTIONS_2026-09-13.md)
- [Publication collector contract](COLLECTOR_CONTRACT_CU_PUBLICATIONS_2026-09-13_v2.md)
- [Pure scoring engine](src/pev.py)
- [Replay runner](src/replay_pev.py)
- [Behavioral tests](tests/test_pev.py)

The order is strict. E compares observed conversion within chambers, after a conservative sample-size adjustment; V counts beneficial distinct measures. E and V affect only P ties. All three raw ingredients and coverage remain visible. No publication-volume term is substituted for substance.

The 180-day horizon and Wilson z=1.96 are explicit candidate choices. They have not been optimized against future outcomes. The implementation measures any further milestone advancement; stage-specific outcomes are shown separately. It does not measure member causality, economic benefit or lobbying ROI.

Run the tests in PowerShell:

```powershell
$pevPython = 'C:\Users\pgoff\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $pevPython -I -B -m unittest discover -s 'C:\Users\pgoff\Mentat\outputs\pev_implementation_20260913\tests' -v
```

Run a new frozen comparison (use a new output directory for each run):

```powershell
& $pevPython -I -B 'C:\Users\pgoff\Mentat\outputs\pev_implementation_20260913\src\replay_pev.py' --source-root 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems' --shadow-root 'C:\Users\pgoff\AppData\Local\Melange\legislative_effectiveness\shadow_20260912' --output-root 'C:\Users\pgoff\Mentat\outputs\pev_implementation_20260913\generation_new' --congress 118 119 --as-of 2026-09-06
```

Read the generated receipt before using candidate tiers. A failed baseline, identity, coverage or constraint check is not silently bypassed. Production integration and full-chain verification are separate from this isolated replay.
