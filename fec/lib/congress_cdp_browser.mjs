// Attach to a real, user-launched Chrome over CDP (no automation flags, no stealth, no
// fingerprint changes) and wait for a positive "cleared" signal. Interactive challenges are
// only ever completed by a human in the visible window. Cookie values are never persisted.

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawn as nodeSpawn } from "node:child_process";
import {
  CongressAutomaticVerificationTimeoutError,
  classifyAutomaticVerification,
} from "./congress_automatic_verification.mjs";
import { defaultCongressProfileDir } from "./congress_profile_dir.mjs";

export const DEFAULT_CDP_PORT = 9222;
export const CF_COOKIE = "cf_clearance";
export const CONGRESS_COOKIE_URL = "https://www.congress.gov";
// ponytail: knobs, calibrate from the measured cf_clearance lifetime in the run receipt
export const DEFAULT_CLEARANCE_AUTO_MS = 30_000;
export const DEFAULT_CLEARANCE_HUMAN_MS = 10 * 60_000;
export const DEFAULT_REFRESH_MARGIN_MS = 10 * 60_000;
export const DEFAULT_KEEP_WARM_MS = 20 * 60_000;

const CHALLENGE_DOM =
  "#challenge-running,#cf-challenge-running,.cf-browser-verification,#challenge-form";

// ---- chrome attach -------------------------------------------------------------------

export function chromeSpawnArgs(port, profile) {
  // Exactly what a person would pass; nothing that alters fingerprint or automation flags.
  return [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "--no-first-run",
    "--no-default-browser-check",
  ];
}

async function debuggerUp(port, fetchImpl) {
  try {
    const response = await fetchImpl(`http://127.0.0.1:${port}/json/version`, {
      signal: AbortSignal.timeout(1500),
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function ensureChrome({
  port = DEFAULT_CDP_PORT,
  profile = defaultCongressProfileDir(),
  chromePath,
  fetchImpl = globalThis.fetch,
  spawnImpl = nodeSpawn,
  probeIntervalMs = 250,
  timeoutMs = 30_000,
  now = Date.now,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
} = {}) {
  const endpoint = `http://127.0.0.1:${port}`;
  if (await debuggerUp(port, fetchImpl)) return { endpoint, spawned: false };
  const child = spawnImpl(chromePath, chromeSpawnArgs(port, profile), {
    detached: true,
    stdio: "ignore",
  });
  child.unref?.();
  const deadline = now() + timeoutMs;
  while (now() < deadline) {
    if (await debuggerUp(port, fetchImpl)) return { endpoint, spawned: true };
    await sleep(probeIntervalMs);
  }
  throw new Error(
    `Launched Chrome but port ${port} never came up after ${Math.round(timeoutMs / 1000)}s. ` +
      "Most likely a Chrome already running on this profile intercepted the launch; " +
      "close all Chrome windows and chrome.exe tasks, then retry.",
  );
}

// ---- cleared signal ------------------------------------------------------------------

// Self-contained on purpose: its source is injected into the page (single source of truth).
export function isClearedSignal(s) {
  const challengeTitle = /just a moment|attention required|security check|verify you are human/i;
  if (challengeTitle.test(s.title || "")) return false;
  if (s.hasChallengeDom) return false;
  return Boolean(s.hasSelector) || /\/(bill|amendment)\//.test(s.pathname || "");
}

export function clearedProbeExpression(selector) {
  return (
    "(() => { const s = { title: document.title, " +
    `hasChallengeDom: !!document.querySelector(${JSON.stringify(CHALLENGE_DOM)}), ` +
    `hasSelector: !!document.querySelector(${JSON.stringify(selector)}), ` +
    "pathname: location.pathname }; " +
    `return (${isClearedSignal.toString()})(s); })()`
  );
}

// "interactive" -> a human must act; "automatic" -> Cloudflare self-check; "none" -> neither.
export function classifyChallenge({ loadedUrl, title, bodyText }) {
  const text = `${title ?? ""} ${bodyText ?? ""}`;
  if (
    /captcha|verify you are human|human verification/i.test(text) &&
    !/verifying you are human|verification successful/i.test(text)
  ) {
    return "interactive";
  }
  if (classifyAutomaticVerification({ loadedUrl, title, bodyText })) return "automatic";
  if (/just a moment|attention required|security check/i.test(title ?? "")) return "automatic";
  return "none";
}

export function classifyFetchPushback({ status, text }) {
  if ([429, 503].includes(status)) return { kind: "rate_limit", status };
  if (status === 403) {
    return /just a moment|challenge-form|cf-challenge|attention required/i.test(text ?? "")
      ? { kind: "challenge", status }
      : { kind: "rate_limit", status };
  }
  const title = String(text ?? "").match(/<title[^>]*>([^<]*)<\/title>/i)?.[1] ?? "";
  if (/just a moment|attention required|security check|verify you are human/i.test(title)) {
    return { kind: "challenge", status };
  }
  if (/id=["']challenge-form["']|cf-browser-verification/i.test(text ?? "")) {
    return { kind: "challenge", status };
  }
  return null;
}

async function snapshot(page) {
  const title = await page.title().catch(() => "");
  const bodyText = await page
    .locator("body")
    .innerText({ timeout: 2000 })
    .then((value) => value.slice(0, 1200))
    .catch(() => "");
  return { loadedUrl: page.url(), title, bodyText };
}

// Resolves {kind:"cleared", via} or throws CongressAutomaticVerificationTimeoutError (so the
// caller exits non-zero and refresh_legislation_discovery.py runs the GovInfo fallback).
export async function waitForClearance(
  page,
  {
    selector = "#main",
    autoMs = DEFAULT_CLEARANCE_AUTO_MS,
    humanMs = DEFAULT_CLEARANCE_HUMAN_MS,
    reloadAtMs = Math.floor(autoMs / 2),
    log = console.log,
  } = {},
) {
  const probe = clearedProbeExpression(selector);
  const waitFor = (timeout) =>
    page.waitForFunction(probe, undefined, { timeout }).then(
      () => true,
      (error) => {
        if (error?.name === "TimeoutError") return false;
        throw error;
      },
    );
  if (await waitFor(reloadAtMs)) return { kind: "cleared", via: "automatic" };
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60_000 }).catch(() => {});
  if (await waitFor(Math.max(1, autoMs - reloadAtMs))) {
    return { kind: "cleared", via: "automatic_after_reload" };
  }
  const observed = await snapshot(page);
  const kind = classifyChallenge(observed);
  if (kind === "interactive" && humanMs > 0) {
    log(
      "Congress.gov needs a one-time human check: complete it in the open Chrome window " +
        `(waiting up to ${Math.round(humanMs / 60_000)} min).`,
    );
    if (await waitFor(humanMs)) return { kind: "cleared", via: "human" };
  }
  const classification = classifyAutomaticVerification(observed) ?? {
    kind: "automatic_security_verification",
    provider: "cloudflare",
    interactive: false,
    collection_outcome: "not_a_result_page",
    loaded_url: observed.loadedUrl,
    page_title: observed.title,
    ray_id: null,
    captcha_bypass_attempted: false,
    verification_interaction_performed: false,
    challenge_observed: kind,
  };
  throw new CongressAutomaticVerificationTimeoutError(
    { ...classification, loaded_url: observed.loadedUrl, page_title: observed.title },
    kind === "interactive" ? humanMs : autoMs,
  );
}

// ---- clearance longevity (metadata only, never the cookie value) ---------------------

export function defaultSessionMetaPath(env = process.env, platform = process.platform) {
  const base =
    platform === "win32"
      ? env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local")
      : os.tmpdir();
  return path.join(base, "Melange", "congress_cf_session.json");
}

export function buildSessionMeta({ cookies, userAgent, profile, now = Date.now() }) {
  const cookie = (cookies ?? []).find((item) => item.name === CF_COOKIE);
  // Playwright reports expires as epoch seconds, -1 for a session cookie.
  const expiresMs = cookie && cookie.expires > 0 ? Math.round(cookie.expires * 1000) : null;
  return {
    schema: "congress-cf-session-meta-v1",
    harvested_at: new Date(now).toISOString(),
    cf_clearance_present: Boolean(cookie),
    cf_clearance_expires: expiresMs === null ? null : new Date(expiresMs).toISOString(),
    measured_lifetime_ms: expiresMs === null ? null : expiresMs - now,
    user_agent: userAgent ?? null,
    profile,
  };
}

export function clearanceNeedsRefresh(
  meta,
  nowMs,
  marginMs,
  { keepWarmMs = Infinity, lastRefreshAtMs = null } = {},
) {
  if (!meta) return true;
  if (meta.cf_clearance_present === false) return true;
  if (meta.cf_clearance_expires) {
    if (Date.parse(meta.cf_clearance_expires) - nowMs < marginMs) return true;
  }
  const last = lastRefreshAtMs ?? Date.parse(meta.harvested_at);
  return Number.isFinite(last) && nowMs - last >= keepWarmMs;
}

export async function recordClearance({
  context,
  userAgent,
  profile,
  metaPath = defaultSessionMetaPath(),
  now = Date.now(),
}) {
  const cookies = await context.cookies(CONGRESS_COOKIE_URL);
  const meta = buildSessionMeta({ cookies, userAgent, profile, now });
  await fs.mkdir(path.dirname(metaPath), { recursive: true });
  await fs.writeFile(metaPath, `${JSON.stringify(meta, null, 2)}\n`, "utf8");
  return meta;
}
