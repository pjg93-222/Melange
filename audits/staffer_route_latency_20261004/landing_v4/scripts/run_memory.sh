#!/bin/bash
# Peak memory of a router publish plus its prewarm (publish_memory.py), before (the 5d4a9bd0a export) and after (the new tip's export), on synthetic worlds of 20,000 and 40,000 people, two runs each.
# Each run is one process under memrun.py with a 1000 MB cap (it is killed above that). Sequential. Output: <work dir>/memory_runs.jsonl, one JSON line per run, and logs/memory_*.log.
#   usage: run_memory.sh <work dir>
set -u
W="$1"
SP="$(cd "$W/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
: > "$W/memory_runs.jsonl"
for n in 20000 40000; do
  offices=400; [ "$n" = 40000 ] && offices=600
  for run in 1 2; do
    for variant in before after; do
      tree="$W/tip_v4"; [ "$variant" = before ] && tree="$W/base_5d4a9bd0a"
      log="$W/logs/memory_${variant}_${n}_${run}.log"
      (cd "$tree" && python "$SP/memrun.py" "$log" 1000 -- python -B "$SP/fix5/publish_memory.py" $n 3 $offices --label "$variant") > "$W/logs/memory_${variant}_${n}_${run}.memrun" 2>&1
      echo "$(cat "$W/logs/memory_${variant}_${n}_${run}.memrun")" | head -1
      grep -h '^{' "$log" >> "$W/memory_runs.jsonl"
    done
  done
done
echo "MEMORY DONE"
