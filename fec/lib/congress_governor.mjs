// Pure adaptive governor for the Congress.gov collector: aggregate token bucket (GCRA),
// global pushback pause, worker halving and slow recovery. No timers, no I/O; the clock
// is injected so it is deterministic under test.

// ponytail: calibration knob; the original saw blocks above ~5 req/s aggregate
export const DEFAULT_MAX_RPS = 4;
// ponytail: Paul 2026-10-25: 10 s after pushback; calibrate
export const DEFAULT_PAUSE_MS = 10_000;
// ponytail: calibration knob; consecutive OK responses before one worker is added back
export const DEFAULT_RECOVER_AFTER = 40;
export const DEFAULT_WORKERS = 12;

export function createGovernor({
  maxWorkers = DEFAULT_WORKERS,
  maxRps = DEFAULT_MAX_RPS,
  pauseMs = DEFAULT_PAUSE_MS,
  recoverAfter = DEFAULT_RECOVER_AFTER,
  minIntervalMs = 0,
  now = Date.now,
} = {}) {
  if (!(maxRps > 0)) throw new Error("maxRps must be positive");
  if (!(maxWorkers >= 1)) throw new Error("maxWorkers must be at least 1");
  const intervalMs = 1000 / maxRps;
  const burstMs = (Math.max(1, Math.round(maxRps)) - 1) * intervalMs;
  let active = Math.floor(maxWorkers);
  let tat = 0; // theoretical arrival time of the next free token slot
  let lastStart = -Infinity;
  let pausedUntil = 0;
  let okStreak = 0;
  let pushbacks = 0;

  return {
    get activeWorkers() {
      return active;
    },
    get maxWorkers() {
      return Math.floor(maxWorkers);
    },
    get pausedUntil() {
      return pausedUntil;
    },
    get pushbackCount() {
      return pushbacks;
    },
    // Claim the next request slot; returns ms the caller must wait before sending.
    reserve() {
      const t = now();
      const earliest = Math.max(t, pausedUntil, tat - burstMs, lastStart + minIntervalMs);
      tat = Math.max(tat, earliest) + intervalMs;
      lastStart = earliest;
      return Math.max(0, earliest - t);
    },
    // Remaining global pause (a slot granted before a pushback may wake inside the pause).
    pauseRemaining() {
      return Math.max(0, pausedUntil - now());
    },
    onSuccess() {
      okStreak += 1;
      if (okStreak >= recoverAfter && active < Math.floor(maxWorkers)) {
        active += 1;
        okStreak = 0;
      }
    },
    // Returns true when this call opened a new pause (concurrent failures inside the same
    // pause window are one event, so 12 simultaneous 429s halve once, not four times).
    onPushback() {
      okStreak = 0;
      const t = now();
      if (t < pausedUntil) return false;
      pausedUntil = t + pauseMs;
      active = Math.max(1, Math.floor(active / 2));
      pushbacks += 1;
      return true;
    },
  };
}
