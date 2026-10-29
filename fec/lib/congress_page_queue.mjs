// Governed request/queue helpers: one request with pushback handling and a retry cap,
// and a worker pool whose width follows the governor's active-worker cap. Event based:
// parked work is released by task completion, never by polling.

export class PushbackError extends Error {
  constructor(kind, detail = {}) {
    super(`Congress.gov pushback (${kind})${detail.status ? ` HTTP ${detail.status}` : ""}`);
    this.name = "PushbackError";
    this.kind = kind; // "rate_limit" | "challenge"
    this.status = detail.status ?? null;
  }
}

export const MAX_RETRIES_PER_PAGE = 3;

const defaultSleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Browser "TypeError: Failed to fetch", Node "TypeError: fetch failed", and the same message
// surfaced through page.evaluate.
export function isTransportError(error) {
  return /failed to fetch|fetch failed|ECONNRESET|ETIMEDOUT|socket hang up|network error/i.test(
    `${error?.name ?? ""}: ${error?.message ?? ""} ${error?.cause?.message ?? ""}`,
  );
}

async function waitForSlot(governor, sleep) {
  const wait = governor.reserve();
  if (wait > 0) await sleep(wait);
  const pause = governor.pauseRemaining();
  if (pause > 0) await sleep(pause);
}

// Returns {ok:true, value, attempts} or, after maxRetries pushbacks, {ok:false, attempts, error}
// so the caller can record a gap instead of failing the run. Non-pushback errors propagate.
export async function governedAttempt({
  governor,
  request,
  onChallenge = async () => {},
  maxRetries = MAX_RETRIES_PER_PAGE,
  sleep = defaultSleep,
  transportBackoffMs = 4_000,
}) {
  let lastError = null;
  for (let attempt = 1; attempt <= maxRetries; attempt += 1) {
    await waitForSlot(governor, sleep);
    try {
      const value = await request();
      governor.onSuccess();
      return { ok: true, value, attempts: attempt };
    } catch (error) {
      if (isTransportError(error)) {
        // "Failed to fetch" / "fetch failed": transient, retried with backoff; exhaustion is a
        // gap row for the caller, never a thrown error that stops every worker.
        lastError = error;
        if (attempt < maxRetries) await sleep(transportBackoffMs * attempt);
        continue;
      }
      if (!(error instanceof PushbackError)) throw error;
      lastError = error;
      governor.onPushback();
      // onChallenge is a shared in-flight promise, so concurrent callers re-clear once.
      if (error.kind === "challenge") await onChallenge(error);
    }
  }
  return { ok: false, attempts: maxRetries, error: lastError };
}

// Run `run(item, slot)` over items with at most governor.activeWorkers in flight. `isDone`
// short-circuits resumed items. Any thrown error stops dispatch and rejects once in-flight work drains.
export function runPool({ items, governor, run, isDone = () => false }) {
  const results = new Array(items.length);
  let next = 0;
  let inFlight = 0;
  let failed = false;
  let firstError = null;
  const free = Array.from({ length: governor.maxWorkers }, (_, index) => index);
  return new Promise((resolve, reject) => {
    const pump = () => {
      if (failed) return;
      while (next < items.length && inFlight < governor.activeWorkers && free.length) {
        const index = next++;
        if (isDone(items[index])) {
          results[index] = { status: "resumed" };
          continue;
        }
        const slot = free.shift();
        inFlight += 1;
        Promise.resolve()
          .then(() => run(items[index], slot))
          .then(
            (value) => {
              results[index] = { status: "ok", value };
            },
            (error) => {
              if (!failed) {
                failed = true;
                firstError = error;
              }
            },
          )
          .finally(() => {
            inFlight -= 1;
            free.push(slot);
            if (failed && inFlight === 0) reject(firstError); // drain in-flight work first
            else pump();
          });
      }
      if (!failed && next >= items.length && inFlight === 0) resolve(results);
    };
    pump();
  });
}
