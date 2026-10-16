# Chain and collector replay procedures

Prepared 2026-10-16 from the 2026-10-14 procedure. Command shapes below retain its
gates, but CLI options must match the selected committed tool. This page does not
authorize execution or establish that unfinished parity has passed. Private older
designs/decisions may be consulted locally; they are not required public inputs.

## Chain parity

1. Establish current execution scope, trusted image identity, exclusive input/writer
   ownership and projected disk reserve. Use approved private scratch storage
   outside automatic temp cleanup; never run A and B against one live tree.
2. Freeze the full read set and record its hash:
   `python ops/compute/chain_parity.py freeze --src <source-root> --dest <frozen-root> --list <read-set.txt>`.
   Inspect `ops/compute/parity_readset_local_extra.args` for required local stores.
   Do not copy secrets/data into a public repository or container build context.
3. Verify each frozen side before execution:
   `python ops/compute/chain_parity.py verify --root <side-root> --manifest <frozen-manifest.json>`.
4. Run Windows with an isolated local state directory and the same pinned date:
   `python ops/compute/chain_parity.py command --side windows --root <A-root> --today <date> --local-dir <A-local-state> --glassbox-dir <A-events> --execute`.
   Do not omit `--local-dir`; a relocated run otherwise risks live local state.
   Retain the harness's rebasing, UTF-8 and workbook-writer settings.
5. Run the container sequentially from its separate frozen inputs:
   `python ops/compute/chain_parity.py command --side container --root <B-root> --today <same-date> --audio-pilot-dir <authorized-audio-input> --execute`.
   The image must resolve through the existing trusted digest/manifest contract.
6. Compare with the actual independent reference runs the selected harness needs:
   `python ops/compute/chain_parity.py compare --frozen <frozen-manifest.json> --a1 <A1> --a2 <A2> --b <B> --map <host-data-root>=<container-data-root> --expect-members 533 --report <evidence-dir>/chain_parity.json --store <comparison-store>`.
   Exit 0 is PASS, 1 failed, and 3 requires disposition of named equivalence
   exceptions. Record counts, failed gates and hashes; do not relabel exit 3.

The older lighter ruling specified one Windows run while this compare form requires
A2. Resolve that mismatch before running; do not pass A twice or silently remove
the independent-reference requirement. Retain exact ranks/dashboard/money gates;
compare workbook content under the accepted numeric contract in shared accuracy.

The 2026-10-14 notes reported failed/incomplete reference runs and no container run.
Those notes are not current status. Missing inputs, lease fixes and receipt-path
repairs require current evidence in the selected source; do not reopen old held
commits solely because their identifiers appeared in a handoff.

## Collector replay

The historical `collectors_replay.py` proof records a keyless GovInfo request for
`fetch_congressional_record.py crec` for one past session day, then replays it with
container networking disabled. It does not prove other collectors or FEC money.

```text
python ops/compute/collectors_replay.py run --date <past-session-day> --glassbox-dir <events-dir>
python ops/compute/collectors_replay.py run --date <past-session-day> --glassbox-dir <events-dir> --work-parent <approved-private-scratch> --execute
```

The first form is the historical plan-only form; verify that in the selected source
before invoking it. The second performs recording and execution and needs current
scope. Inspect scratch retention behavior first: the historical tool removes its
scratch/cassette/staged DB unless `--keep`. Do not let it remove required recovery
evidence. Retain existing secret-leak refusal and network isolation.

Read `result`: PASS, FAIL or INCONCLUSIVE. An empty-speech date/exit 3 proves nothing.
Keep report output at the gate's actual `collectors_replay.json` path. Select images
from the verified release or explicitly trusted digest, never an unreviewed tag or
a hypothetical `--local-image` bypass. Inspect deny-by-default build-context filters
before any separately authorized image build; private keys must not reach a daemon.
