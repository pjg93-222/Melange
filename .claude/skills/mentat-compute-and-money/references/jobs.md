# Mentat jobs and controlled task transition

Prepared 2026-10-16 from the 2026-10-14 procedure. Verify job contracts and limits in
the selected `mentat/COMPUTE.md` and `mentat/tools/run_job.ps1`. The table records
that procedure's bounds; it does not establish current schedules or start jobs.

| Job | Network / key need | Historical wrapper cap |
|---|---|---:|
| anchors | none / no FEC key | 45 min |
| refit-detect | none / no FEC key | 20 min |
| refit-parity | none / no FEC key | 240 min |
| refit | none / no FEC key; publish never | 480 min |
| pocket-build | none / no FEC key | 10 min |
| collect-fanout | live collection / FEC key | 1440 min |
| pac-evidence | live collection / FEC key | 120 min |

The wrapper form is `mentat/tools/run_job.ps1 -Job <job> [-JobArgs ...] [-PlanOnly]`.
Confirm that `-PlanOnly` has no execution side effects in selected source. Retain
its locking, digest validation, clock check, receipt validation and key staging/
`finally` cleanup. Never log staged secrets or publish job logs without review.

Anchors requires existing Melange-derived `sector_spend.csv` and
`fullscope_receipts.json` through read-only mounts that refuse missing host paths.
Use the current configured private store, not a hardcoded personal directory.
Industry report production, Excel finalization, artifact-tool, console prewarm,
figure export and analytics indexing were outside the compute-job migration;
do not broaden it implicitly.

## Official-image streak

The retained criterion is three consecutive passing runs on three distinct frozen
input snapshots for each of anchors, refit-detect, pocket-build and refit-parity,
with one source identity and official image digest. Record both, not just a tag.

The historical harness runs Windows A1 and A2 to establish named variance, then B
sequentially from the same inputs. Its command shapes from the `mentat` directory:

```text
python tools/compute_parity.py variance <A1> <A2> --out <mask.json>
python tools/compute_parity.py compare <A1> <B> --mask <mask.json> --map <host-mentat-root>=/mentat --report <report.json>
```

The mask must originate from those actual reference runs. Do not drop A2 to fit an
older lighter-run note. Historical passes on a local image and incomplete old
snapshots do not count for a new official-image identity. A recorded old R test
failure is not evidence that a new failure is baseline; retain comparison receipts.

## Task transition, only within current scope

After all applicable gates pass, review the actual definitions of
`MentatNightlyAnchors` and `MentatRefitWatcher` and their proposed container
counterparts. Preserve exported definitions in private recovery storage before an
authorized change. Verify one writer per input tree, no in-flight task, exact
arguments/identity and rollback before disabling/registering/enabling anything.

Use the selected current runbook for exact registration parameters. This document
deliberately does not replay historical schedules or enable tasks automatically.
An authorized smoke invocation is a separate operation with actual logs and
receipts. Do not delete original task definitions merely because a container task
exists; preserve the accepted rollback and existing holds.
