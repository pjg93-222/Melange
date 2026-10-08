#!/bin/bash
# The gc and rebuild evidence of the v4.1 round, on clean exports of the v4 tip (the "before": base_v4) and the v4.1 tip (the "after": tip_v41), one process at a time, each under memrun.py with a
# 1000 MB cap (a run that goes above it is killed and reported):
#   1. publish_memory.py: a router and its prewarm, then an equal router swapped in the way the service does it and its prewarm (the start-up prewarm's gc_ms, the replacement prewarm's gc_ms, peak memory)
#      at 20,000 and 40,000 people;
#   2. gc_measure.py 20000: what one collection costs with nothing to free (the start-up case v4 paid) and with a replaced router to free (the publish case);
#   3. stress_release.py (the re-check's own script): 6 workers on one router while a releaser empties it every 0-15 ms; the deterministic release between the passes of a distinct, independent and
#      ranked request; the service case with an in-flight build on the old router;
#   4. directory_mode.py (the re-check's scenario D, extended for uncovered_basis and the page's line).
#   usage: evidence.sh <suites work dir holding base_v4 and tip_v41> <out dir>
set -u
W="$1"
OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
mkdir -p "$OUT"
DATA="staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json"
for name in base_v4 tip_v41; do
  tree="$W/$name"
  for f in $DATA; do cp "$LIVE/fec/surfaces/$f" "$tree/fec/surfaces/$f"; done
  for n in 20000 40000; do
    offices=400; [ "$n" = 40000 ] && offices=600
    (cd "$tree" && python "$HERE/memrun.py" "$OUT/publish_memory_${name}_${n}.log" 1000 -- python -B "$HERE/publish_memory.py" $n 3 $offices --label "$name") > "$OUT/publish_memory_${name}_${n}.memrun" 2>&1
    echo "publish_memory $name $n: $(head -1 "$OUT/publish_memory_${name}_${n}.memrun")"
  done
  (cd "$tree" && python "$HERE/memrun.py" "$OUT/gc_measure_${name}.log" 1000 -- python -B "$HERE/gc_measure.py" 20000) > "$OUT/gc_measure_${name}.memrun" 2>&1
  echo "gc_measure $name: $(head -1 "$OUT/gc_measure_${name}.memrun")"
  seconds=40; [ "$name" = base_v4 ] && seconds=15
  (cd "$tree" && STRESS_SECONDS=$seconds python "$HERE/memrun.py" "$OUT/stress_release_${name}.log" 1000 -- python -B "$HERE/stress_release.py") > "$OUT/stress_release_${name}.memrun" 2>&1
  echo "stress_release $name (${seconds} s): $(head -1 "$OUT/stress_release_${name}.memrun")"
  (cd "$tree" && python -B "$HERE/directory_mode.py") > "$OUT/directory_mode_${name}.log" 2>&1
  echo "directory_mode $name rc=$?"
  for f in $DATA; do rm -f "$tree/fec/surfaces/$f"; done
done
echo "EVIDENCE DONE"
