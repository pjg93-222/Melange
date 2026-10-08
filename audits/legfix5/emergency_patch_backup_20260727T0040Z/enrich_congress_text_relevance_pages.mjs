#!/usr/bin/env node
/**
 * Collect official Congress.gov text-context evidence for category relevance.
 *
 * Discovery remains exclusively the completed Advanced Search corpus. This
 * enrichment visits the official /text page for each recovered measure and
 * records exact/proximate identifier contexts without storing entire bill
 * texts. It never deletes candidates and never makes an exclusion decision.
 */

import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { writeTextAtomicWithRetry } from "./lib/atomic_checkpoint.mjs";
import { createGlobalRateLimiter } from "./lib/global_rate_limiter.mjs";
import { createCongressContextHttpFastPath } from "./lib/congress_context_http_fast_path.mjs";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const ROOT = path.resolve(import.meta.dirname, "..");
const DEFAULT_RUN = path.join(
  ROOT,
  "audits",
  "legfix5",
  "congress_advanced_final_20260725",
);
const DEFAULT_REGISTRY = path.join(
  ROOT,
  "source_data",
  "legislation",
  "acu_legislation_search_registry.json",
);
const DEFAULT_CHROME =
  process.platform === "win32"
    ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    : "/usr/bin/google-chrome";

function parseArgs(argv) {
  const args = {
    run: DEFAULT_RUN,
    registry: DEFAULT_REGISTRY,
    out: null,
    profile: path.join(os.tmpdir(), "codex-congress-text-relevance-profile"),
    chrome: DEFAULT_CHROME,
    headless: true,
    delayMs: 750,
    workers: 3,
    browserMaxAttempts: 3,
    httpFastPath: false,
    httpWorkers: 6,
    httpMaxAttempts: 3,
    httpRetryBaseMs: 3000,
    resume: false,
    keys: null,
    limit: null,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--run") args.run = argv[++index];
    else if (value === "--registry") args.registry = argv[++index];
    else if (value === "--out") args.out = argv[++index];
    else if (value === "--profile") args.profile = argv[++index];
    else if (value === "--chrome") args.chrome = argv[++index];
    else if (value === "--delay-ms") args.delayMs = Number(argv[++index]);
    else if (value === "--workers") args.workers = Number(argv[++index]);
    else if (value === "--browser-max-attempts") {
      args.browserMaxAttempts = Number(argv[++index]);
    }
    else if (value === "--http-fast-path") args.httpFastPath = true;
    else if (value === "--http-workers") {
      args.httpWorkers = Number(argv[++index]);
    } else if (value === "--http-max-attempts") {
      args.httpMaxAttempts = Number(argv[++index]);
    } else if (value === "--http-retry-base-ms") {
      args.httpRetryBaseMs = Number(argv[++index]);
    }
    else if (value === "--keys") {
      args.keys = new Set(
        argv[++index]
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      );
    } else if (value === "--limit") args.limit = Number(argv[++index]);
    else if (value === "--headless") args.headless = true;
    else if (value === "--headed") args.headless = false;
    else if (value === "--resume") args.resume = true;
    else if (value === "--help") {
      console.log(`Usage: node fec/enrich_congress_text_relevance_pages.mjs [options]
  --run PATH        Completed Advanced Search run directory
  --registry PATH   Search-outline registry
  --out PATH        Output directory (default RUN/text_relevance)
  --profile PATH    Isolated Chrome profile directory
  --chrome PATH     Chrome executable
  --delay-ms N      Delay between Congress.gov pages (default 750)
  --workers N       Concurrent tabs sharing the global delay (default 3)
  --browser-max-attempts N  Bounded browser attempts, 1-3 (default 3)
  --http-fast-path  Opt in to context-seeded HTTP with strict browser fallback
  --http-workers N  Logical HTTP workers sharing the global delay (default 6)
  --http-max-attempts N  Bounded HTTP attempts, 1-5 (default 3)
  --http-retry-base-ms N  HTTP exponential-backoff base (default 3000)
  --keys IDS        Comma-separated Congress-qualified keys
  --limit N         Process only the first N selected records
  --headless        Run Chrome headless (default)
  --headed          Run headed only when explicitly requested
  --resume          Reuse evidence artifacts that pass provenance checks`);
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${value}`);
    }
  }
  if (!Number.isFinite(args.delayMs) || args.delayMs < 0) {
    throw new Error("--delay-ms must be a non-negative number");
  }
  if (
    !Number.isInteger(args.workers) ||
    args.workers < 1 ||
    args.workers > 8
  ) {
    throw new Error("--workers must be an integer between 1 and 8");
  }
  if (
    !Number.isInteger(args.browserMaxAttempts) ||
    args.browserMaxAttempts < 1 ||
    args.browserMaxAttempts > 3
  ) {
    throw new Error("--browser-max-attempts must be an integer between 1 and 3");
  }
  if (
    !Number.isInteger(args.httpWorkers) ||
    args.httpWorkers < 1 ||
    args.httpWorkers > 8
  ) {
    throw new Error("--http-workers must be an integer between 1 and 8");
  }
  if (
    !Number.isInteger(args.httpMaxAttempts) ||
    args.httpMaxAttempts < 1 ||
    args.httpMaxAttempts > 5
  ) {
    throw new Error("--http-max-attempts must be an integer between 1 and 5");
  }
  if (
    !Number.isFinite(args.httpRetryBaseMs) ||
    args.httpRetryBaseMs < 0
  ) {
    throw new Error("--http-retry-base-ms must be a non-negative number");
  }
  if (
    args.limit !== null &&
    (!Number.isInteger(args.limit) || args.limit < 1)
  ) {
    throw new Error("--limit must be a positive integer");
  }
  return args;
}

function assertWithinRoot(target) {
  const resolved = path.resolve(ROOT, target);
  const relative = path.relative(ROOT, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Path must stay within repository root: ${resolved}`);
  }
  return resolved;
}

function stableHash(value) {
  return crypto
    .createHash("sha256")
    .update(typeof value === "string" ? value : JSON.stringify(value))
    .digest("hex");
}

function isoNow() {
  return new Date().toISOString();
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function readJson(file) {
  return JSON.parse(await fs.readFile(file, "utf8"));
}

async function readNdjson(file) {
  const text = await fs.readFile(file, "utf8");
  return text
    .split(/\r?\n/)
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
}

async function writeTextWithRetry(file, value, attempts = 30) {
  await writeTextAtomicWithRetry(file, value, { attempts });
}

async function writeJson(file, value) {
  await writeTextWithRetry(file, `${JSON.stringify(value, null, 2)}\n`);
}

async function writeNdjson(file, rows) {
  const body = rows.map((row) => JSON.stringify(row)).join("\n");
  await writeTextWithRetry(file, body ? `${body}\n` : "");
}

function safeEventSlug(value) {
  return String(value ?? "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120) || "unknown";
}

async function writeGlassboxEvent(eventsDir, sequence, canonicalKey, payload) {
  const file = path.join(
    eventsDir,
    `${String(sequence).padStart(8, "0")}-${safeEventSlug(canonicalKey)}-${crypto.randomUUID()}.json`,
  );
  await writeJson(file, {
    schema_version: 1,
    timestamp_utc: isoNow(),
    lane: "codex",
    source: "congress-full-text",
    run_id: "legislation-full-text-20260726",
    ...payload,
  });
  return file;
}

async function removeWithRetry(file, attempts = 30) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      await fs.rm(file, { force: true });
      return;
    } catch (error) {
      lastError = error;
      if (!["EBUSY", "EPERM", "EACCES"].includes(error.code)) throw error;
      if (attempt < attempts) await sleep(250 * attempt);
    }
  }
  throw new Error(`Could not remove checkpoint: ${file}`, {
    cause: lastError,
  });
}

function processIsAlive(processId) {
  if (!Number.isInteger(processId) || processId < 1) return false;
  try {
    process.kill(processId, 0);
    return true;
  } catch (error) {
    return error.code === "EPERM";
  }
}

async function acquireRunLock(outDir) {
  const lockFile = path.join(outDir, "text-relevance.lock.json");
  await fs.mkdir(outDir, { recursive: true });
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const handle = await fs.open(lockFile, "wx");
      await handle.writeFile(
        `${JSON.stringify(
          {
            schema: "congress-text-relevance-lock-v1",
            pid: process.pid,
            started_at: isoNow(),
          },
          null,
          2,
        )}\n`,
        "utf8",
      );
      return { handle, lockFile };
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      let prior = null;
      try {
        prior = await readJson(lockFile);
      } catch {
        // An unreadable lock is not safe to overwrite.
      }
      if (!prior || processIsAlive(Number(prior.pid))) {
        throw new Error(
          `Text relevance output is locked by a live or unreadable run: ` +
            `${lockFile} (pid=${prior?.pid ?? "unknown"})`,
        );
      }
      await removeWithRetry(lockFile);
      if (attempt < 3) await sleep(500 * attempt);
    }
  }
  throw new Error(`Could not acquire text relevance lock: ${lockFile}`);
}

async function releaseRunLock(lock) {
  if (!lock) return;
  await lock.handle.close().catch(() => {});
  await removeWithRetry(lock.lockFile);
}

async function waitForCongressPage(
  page,
  selector,
  requireOfficialTextSurface = false,
) {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    const ready = requireOfficialTextSurface
      ? await page
          .evaluate((surfaceSelector) => {
            const marker =
              /(?:^|\n)\s*(?:Shown Here:|Amendment Text:)\s*(?:\n|$)/i;
            return [...document.querySelectorAll(surfaceSelector)].some(
              (surface) => marker.test(surface.innerText ?? ""),
            );
          }, selector)
          .catch(() => false)
      : Boolean(await page.locator(selector).count());
    if (ready) return;
    const title = await page.title().catch(() => "");
    const body = await page
      .locator("body")
      .innerText()
      .then((value) => value.slice(0, 1200))
      .catch(() => "");
    if (
      /captcha|verify you are human|human verification/i.test(`${title} ${body}`) &&
      !/verifying you are human|verification successful/i.test(`${title} ${body}`)
    ) {
      throw new Error(
        "Congress.gov presented an interactive human-verification challenge; " +
          "progress is checkpointed and no challenge was bypassed.",
      );
    }
    await sleep(2000);
  }
  throw new Error(
    `Congress.gov did not expose ${selector}; title=${JSON.stringify(
      await page.title().catch(() => "<unavailable>"),
    )} url=${page.url()}`,
  );
}

async function gotoWithRetry(
  page,
  url,
  selector = "#main",
  attempts = 3,
  scheduleRequest = async () => {},
  requireOfficialTextSurface = false,
) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      await scheduleRequest();
      const response = await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 90_000,
      });
      await waitForCongressPage(page, selector, requireOfficialTextSurface);
      return response?.status() ?? null;
    } catch (error) {
      lastError = error;
      if (/interactive human-verification/i.test(error.message)) throw error;
      if (attempt < attempts) await sleep(4000 * attempt);
    }
  }
  throw new Error(`Congress.gov navigation failed after ${attempts} attempts`, {
    cause: lastError,
  });
}

function canonicalKeySet(value) {
  return [...new Set(value)].sort();
}

const TEXT_MATCH_POLICY_VERSION =
  "ordered-token-bounded-act-action-required-v2";

function textEvidenceEvaluator({ categories, html = null, loadedUrl = null }) {
    const compactBrowser = (value) =>
      String(value ?? "").replace(/\s+/g, " ").trim();
    const normalize = (value) =>
      String(value ?? "")
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/[’']/g, "")
        .replace(/[^\p{L}\p{N}]+/gu, " ")
        .replace(/\s+/g, " ")
        .trim();
    const stem = (value) => {
      let token = normalize(value);
      if (token.length > 5 && token.endsWith("ies")) {
        token = `${token.slice(0, -3)}y`;
      } else if (
        token.length > 5 &&
        token.endsWith("es") &&
        !token.endsWith("ses")
      ) {
        token = token.slice(0, -2);
      } else if (token.length > 4 && token.endsWith("s")) {
        token = token.slice(0, -1);
      }
      return token;
    };
    const sourceDocument =
      html === null
        ? document
        : new DOMParser().parseFromString(html, "text/html");
    const surfaces = [...sourceDocument.querySelectorAll("#main, main")];
    const verifiedSurfaces = surfaces
      .map((surface) => {
        const rawText = surface.innerText ?? "";
        const markers = [
          ...rawText.matchAll(
            /(?:^|\n)\s*(Shown Here:|Amendment Text:)\s*(?:\n|$)/gi,
          ),
        ].map((match) => ({
          index: match.index ?? -1,
          marker: /^Shown Here:$/i.test(match[1])
            ? "Shown Here:"
            : "Amendment Text:",
        }));
        return { surface, rawText, markers };
      })
      .filter((candidate) => candidate.markers.length > 0)
      .sort(
        (left, right) =>
          left.markers[0].index - right.markers[0].index,
      );
    const verifiedSurface = verifiedSurfaces[0] ?? null;
    const main = verifiedSurface?.surface ?? null;
    const rawMain = verifiedSurface?.rawText ?? "";
    const selectedMarker = verifiedSurface?.markers[0] ?? null;
    const officialTextSurfaceMarker = selectedMarker?.marker ?? null;
    const shownHereMarkerFound =
      verifiedSurface?.markers.some(
        (marker) => marker.marker === "Shown Here:",
      ) ?? false;
    const amendmentTextMarkerFound =
      verifiedSurface?.markers.some(
        (marker) => marker.marker === "Amendment Text:",
      ) ?? false;
    // Fail closed when Congress.gov does not expose the verified bill-text
    // or amendment-text container. Page chrome, Cloudflare challenge text,
    // related-measure titles, and navigation are not official-text evidence.
    const content =
      selectedMarker?.index >= 0 ? rawMain.slice(selectedMarker.index) : "";
    const normalizedContent = normalize(content);
    const tokens = [];
    const tokenPattern = /[\p{L}\p{N}]+/gu;
    let tokenMatch;
    let segmentId = 0;
    let priorTokenEnd = 0;
    while ((tokenMatch = tokenPattern.exec(content)) !== null) {
      if (/[.!?;\n]/.test(content.slice(priorTokenEnd, tokenMatch.index))) {
        segmentId += 1;
      }
      tokens.push({
        stem: stem(tokenMatch[0]),
        start: tokenMatch.index,
        end: tokenPattern.lastIndex,
        segment_id: segmentId,
      });
      priorTokenEnd = tokenPattern.lastIndex;
    }
    const contextForRange = (start, end) =>
      compactBrowser(
        content.slice(
          Math.max(0, start - 320),
          Math.min(content.length, end + 320),
        ),
      );
    const orderedTokenSpans = (required, maximumGap = 0) => {
      if (!required.length) return [];
      const spans = [];
      for (let startIndex = 0; startIndex < tokens.length; startIndex += 1) {
        if (tokens[startIndex].stem !== required[0]) continue;
        let priorIndex = startIndex;
        let matched = true;
        for (let requiredIndex = 1; requiredIndex < required.length; requiredIndex += 1) {
          let foundIndex = -1;
          const lastIndex = Math.min(
            tokens.length - 1,
            priorIndex + maximumGap + 1,
          );
          for (let index = priorIndex + 1; index <= lastIndex; index += 1) {
            if (tokens[index].segment_id !== tokens[startIndex].segment_id) break;
            if (tokens[index].stem === required[requiredIndex]) {
              foundIndex = index;
              break;
            }
          }
          if (foundIndex < 0) {
            matched = false;
            break;
          }
          priorIndex = foundIndex;
        }
        if (matched) {
          spans.push({
            startToken: startIndex,
            endToken: priorIndex,
            spanTokens: priorIndex - startIndex + 1,
            segmentId: tokens[startIndex].segment_id,
          });
        }
      }
      return spans;
    };
    const actionPattern =
      /\b(?:amend(?:s|ed|ing|ment)?|repeal(?:s|ed|ing)?|exempt(?:s|ed|ing|ion)?|prohibit(?:s|ed|ing|ion)?|require(?:s|d|ing|ment)?|authoriz(?:e|es|ed|ing|ation)|reauthoriz(?:e|es|ed|ing|ation)|direct(?:s|ed|ing|ion)?|modif(?:y|ies|ied|ication)|revis(?:e|es|ed|ing|ion)|strike|strikes|struck|insert(?:s|ed|ing)?|extend(?:s|ed|ing)?|apply|applies|applied)\b/i;
    const segmentContext = (span) => {
      let start = tokens[span.startToken].start;
      let end = tokens[span.endToken].end;
      while (start > 0 && !/[.!?;\n]/.test(content[start - 1])) start -= 1;
      while (end < content.length && !/[.!?;\n]/.test(content[end])) end += 1;
      return compactBrowser(content.slice(start, end));
    };
    const evidenceForIdentifier = (identifier) => {
      const rawIdentifier = String(identifier ?? "").trim();
      const proximityExpression = rawIdentifier.match(
        /^\s*"([^"]+)"\s*~\s*(\d+)\s*$/,
      );
      const evidenceIdentifier = (
        proximityExpression ? proximityExpression[1] : rawIdentifier
      )
        .replace(/"([^"]+)"\s*~\s*\d+/g, "$1")
        .replace(/[()"]/g, " ")
        .replace(/\b(?:AND|OR|NOT)\b/gi, " ");
      const normalizedIdentifier = normalize(evidenceIdentifier);
      const identifierTokens = normalizedIdentifier
        .split(" ")
        .map(stem)
        .filter(Boolean);
      const genericEvidenceTokens = new Set([
        "a",
        "an",
        "the",
        "this",
        "that",
        "of",
        "and",
        "or",
        "for",
        "to",
        "in",
        "on",
        "act",
        "bill",
        "law",
        "resolution",
        "legislation",
      ]);
      const containsAct = identifierTokens.includes("act");
      const actIndex = identifierTokens.indexOf("act");
      const distinctiveTokens = [
        ...new Set(
          identifierTokens.filter(
            (token) => !genericEvidenceTokens.has(token),
          ),
        ),
      ];
      const specificityValid =
        identifierTokens.length > 0 &&
        !(containsAct && distinctiveTokens.length < 2) &&
        !identifierTokens.every((token) =>
          genericEvidenceTokens.has(token),
        );
      const specificityReason = specificityValid
        ? containsAct
          ? "complete_ordered_act_name_and_local_legislative_action_required"
          : "non_generic_identifier"
        : containsAct
          ? "rejected_non_specific_act_identifier"
          : "rejected_all_generic_identifier";
      const actTitleTokens = containsAct
        ? identifierTokens.slice(0, actIndex + 1)
        : [];
      const trailingContextTokens = containsAct
        ? identifierTokens.slice(actIndex + 1)
        : [];
      const maximumGap = proximityExpression
        ? Math.max(0, Number.parseInt(proximityExpression[2], 10))
        : 0;
      const fullOrderedSpans = specificityValid
        ? orderedTokenSpans(identifierTokens, maximumGap)
        : [];
      const exactPhraseSpans = specificityValid
        ? orderedTokenSpans(identifierTokens, 0)
        : [];
      const actTitleSpans =
        specificityValid && containsAct
          ? orderedTokenSpans(actTitleTokens, 0)
          : [];
      const actSpansWithContext = actTitleSpans.filter((titleSpan) => {
        if (!trailingContextTokens.length) return true;
        const tailTokens = tokens.slice(
          titleSpan.endToken + 1,
          Math.min(
            tokens.length,
            titleSpan.endToken + trailingContextTokens.length + 9,
          ),
        );
        if (
          tailTokens.some(
            (token) => token.segment_id !== titleSpan.segmentId,
          )
        ) {
          const firstDifferent = tailTokens.findIndex(
            (token) => token.segment_id !== titleSpan.segmentId,
          );
          tailTokens.splice(Math.max(0, firstDifferent));
        }
        let prior = -1;
        return trailingContextTokens.every((requiredToken) => {
          const found = tailTokens.findIndex(
            (token, index) =>
              index > prior && token.stem === requiredToken,
          );
          if (found < 0) return false;
          prior = found;
          return true;
        });
      });
      const actActionSpans = actSpansWithContext.filter((span) =>
        actionPattern.test(segmentContext(span)),
      );
      const exactPhrase = exactPhraseSpans.length > 0;
      const orderedProximityMatch = Boolean(
        proximityExpression && fullOrderedSpans.length,
      );
      const best = containsAct
        ? actActionSpans[0] ?? actSpansWithContext[0] ?? actTitleSpans[0] ?? null
        : exactPhraseSpans[0] ?? fullOrderedSpans[0] ?? null;
      const proximityMatch = containsAct
        ? actActionSpans.length > 0
        : orderedProximityMatch;
      const localizedMatch = containsAct
        ? specificityValid && actActionSpans.length > 0
        : specificityValid && (exactPhrase || orderedProximityMatch);
      const context = best
        ? contextForRange(
            tokens[best.startToken].start,
            tokens[best.endToken].end,
          )
        : null;
      return {
        identifier,
        evidence_identifier: normalizedIdentifier,
        match_mode: containsAct
          ? "ordered_complete_act_name_plus_same_segment_legislative_action"
          : proximityExpression
            ? "ordered_same_segment_proximity"
            : "ordered_exact_token_phrase",
        maximum_adjacent_gap: maximumGap,
        normalized_identifier: normalizedIdentifier,
        identifier_tokens: identifierTokens,
        distinctive_identifier_tokens: distinctiveTokens,
        act_title_tokens: actTitleTokens,
        trailing_context_tokens: trailingContextTokens,
        specificity_valid: specificityValid,
        specificity_reason: specificityReason,
        exact_phrase: exactPhrase,
        minimum_token_span: best?.spanTokens ?? null,
        proximity_threshold: proximityExpression ? maximumGap : 0,
        proximity_match: proximityMatch,
        complete_act_name_found: actTitleSpans.length > 0,
        act_context_found: actSpansWithContext.length > 0,
        localized_legislative_action_found:
          containsAct && actActionSpans.length > 0,
        act_reference_only:
          containsAct &&
          actSpansWithContext.length > 0 &&
          actActionSpans.length === 0,
        localized_match: localizedMatch,
        context,
      };
    };
    const categoryEvidence = categories.map((category) => {
      const identifiers = category.identifiers.map(evidenceForIdentifier);
      const localized = identifiers.filter((item) => item.localized_match);
      const separated = identifiers.filter(
        (item) =>
          !item.localized_match && item.minimum_token_span !== null,
      );
      return {
        query_id: category.query_id,
        label: category.label,
        evidence_role: category.evidence_role,
        source_coverage_probe_ids:
          category.source_coverage_probe_ids ?? [],
        identifiers,
        localized_identifier_count: localized.length,
        localized_identifiers: localized.map((item) => item.identifier),
        separated_identifier_count: separated.length,
        separated_identifiers: separated.map((item) => ({
          identifier: item.identifier,
          minimum_token_span: item.minimum_token_span,
        })),
        evidence_state: localized.length
          ? "localized_official_text_evidence"
          : "no_localized_identifier_evidence",
      };
    });
    const title = sourceDocument.title;
    const notFound =
      /page not found|requested page could not be found|error 404/i.test(
        `${title} ${compactBrowser(rawMain).slice(0, 1500)}`,
      );
    const textAvailable = !notFound && selectedMarker?.index >= 0;
    const versionLabel =
      compactBrowser(
        [...(main?.querySelectorAll("h2, h3") ?? [])].find((node) =>
          /^Shown Here:/i.test(compactBrowser(node.textContent)),
        )?.nextElementSibling?.textContent,
      ) || null;
    let hash = 2166136261;
    for (let index = 0; index < content.length; index += 1) {
      hash ^= content.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return {
      loaded_url: loadedUrl ?? location.href,
      page_title: title,
      not_found: notFound,
      text_available: textAvailable,
      official_text_surface_marker: officialTextSurfaceMarker,
      shown_here_marker_found: shownHereMarkerFound,
      amendment_text_marker_found: amendmentTextMarkerFound,
      version_label: versionLabel,
      official_text_character_count: content.length,
      official_text_token_count: tokens.length,
      official_text_fnv1a32: (hash >>> 0).toString(16).padStart(8, "0"),
      categories: categoryEvidence,
    };
}

async function extractTextEvidence(page, categorySpecs) {
  return page.evaluate(textEvidenceEvaluator, { categories: categorySpecs });
}

async function extractTextEvidenceFromHtml(
  page,
  categorySpecs,
  html,
  loadedUrl,
) {
  // Render the already-fetched body in the worker tab so `innerText` has the
  // same layout/whitespace semantics as the frozen browser-navigation
  // baseline. Strip scripts first: the HTTP body is evidence to parse, not
  // authority to execute a second navigation or analytics workload.
  const inertHtml = String(html ?? "").replace(
    /<script\b[^>]*>[\s\S]*?<\/script\s*>/gi,
    "",
  );
  await page.setContent(inertHtml, {
    waitUntil: "domcontentloaded",
    timeout: 30_000,
  });
  return page.evaluate(textEvidenceEvaluator, {
    categories: categorySpecs,
    loadedUrl,
  });
}

function officialTextContentProjection(value) {
  return {
    text_available: value?.text_available === true,
    official_text_surface_marker:
      value?.official_text_surface_marker ?? null,
    shown_here_marker_found: value?.shown_here_marker_found === true,
    amendment_text_marker_found:
      value?.amendment_text_marker_found === true,
    official_text_character_count:
      value?.official_text_character_count ?? null,
    official_text_token_count: value?.official_text_token_count ?? null,
    official_text_fnv1a32: value?.official_text_fnv1a32 ?? null,
  };
}

function officialTextContentFingerprint(value) {
  return stableHash(officialTextContentProjection(value));
}

function artifactIntegrityProjection(artifact) {
  const copy = { ...artifact };
  delete copy.artifact_integrity_sha256;
  return copy;
}

function artifactIntegritySha256(artifact) {
  return stableHash(artifactIntegrityProjection(artifact));
}

function frozenBrowserBaseline(prior, sourceFileSha256) {
  if (!prior || prior.text_available !== true) return null;
  const selected =
    prior.transport_provenance?.selected_transport ?? "browser_navigation";
  if (selected !== "browser_navigation") return null;
  const projection = officialTextContentProjection(prior);
  const verifiedSurface =
    (projection.official_text_surface_marker === "Shown Here:" &&
      projection.shown_here_marker_found === true) ||
    (projection.official_text_surface_marker === "Amendment Text:" &&
      projection.amendment_text_marker_found === true);
  if (
    !verifiedSurface ||
    !Number.isInteger(projection.official_text_character_count) ||
    projection.official_text_character_count < 1 ||
    !Number.isInteger(projection.official_text_token_count) ||
    projection.official_text_token_count < 1 ||
    !/^[0-9a-f]{8}$/i.test(projection.official_text_fnv1a32 ?? "")
  ) {
    return null;
  }
  return {
    schema: "congress-text-browser-equivalence-baseline-v1",
    source_artifact_file_sha256: sourceFileSha256,
    source_artifact_integrity_sha256:
      prior.artifact_integrity_sha256 ?? null,
    source_transport: selected,
    content_projection: projection,
    content_fingerprint_sha256: stableHash(projection),
  };
}

async function readJsonWithFileHash(file) {
  const text = await fs.readFile(file, "utf8");
  return {
    artifact: JSON.parse(text),
    file_sha256: stableHash(text),
  };
}

async function writeImmutableTransportReceipt(outDir, record, payload) {
  const receiptBase = {
    schema: "congress-text-transport-receipt-v1",
    created_at: isoNow(),
    discovery_canonical_key: record.canonical_key,
    ...payload,
  };
  const receipt = {
    ...receiptBase,
    receipt_payload_sha256: stableHash(receiptBase),
  };
  const text = `${JSON.stringify(receipt, null, 2)}\n`;
  const fileSha256 = stableHash(text);
  const directory = path.join(
    outDir,
    "transport_receipts",
    String(record.congress),
    record.type,
    String(record.number),
  );
  const file = path.join(directory, `${receipt.receipt_payload_sha256}.json`);
  await fs.mkdir(directory, { recursive: true });
  try {
    const existing = await fs.readFile(file, "utf8");
    if (existing !== text) {
      throw new Error(`Immutable transport receipt collision: ${file}`);
    }
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
    const temporary = path.join(
      directory,
      `.${receipt.receipt_payload_sha256}.${process.pid}.${crypto.randomUUID()}.tmp`,
    );
    let handle;
    try {
      handle = await fs.open(temporary, "wx");
      await handle.writeFile(text, "utf8");
      await handle.sync();
      await handle.close();
      handle = null;
      try {
        await fs.link(temporary, file);
      } catch (linkError) {
        if (linkError.code !== "EEXIST") throw linkError;
        const existing = await fs.readFile(file, "utf8");
        if (existing !== text) {
          throw new Error(`Immutable transport receipt collision: ${file}`);
        }
      }
    } finally {
      await handle?.close().catch(() => {});
      await fs.rm(temporary, { force: true }).catch(() => {});
    }
  }
  return {
    file: path.relative(outDir, file).split(path.sep).join("/"),
    receipt_payload_sha256: receipt.receipt_payload_sha256,
    file_sha256: fileSha256,
  };
}

async function collectMeasure(
  page,
  record,
  categorySpecs,
  scheduleRequest,
  {
    httpFastPath = null,
    frozenBaseline = null,
    browserMaxAttempts = 3,
  } = {},
) {
  const textUrl = `${record.canonical_url}/text`;
  let httpStatus = null;
  let extracted = null;
  let selectedTransport = "browser_navigation";
  let browserFallbackReason = null;
  let httpResult = null;
  let equivalence = {
    required: Boolean(httpFastPath),
    baseline_available: Boolean(frozenBaseline),
    passed: false,
    baseline: frozenBaseline,
    observed_content_fingerprint_sha256: null,
  };

  if (httpFastPath) {
    httpResult = await httpFastPath.fetch(textUrl);
    if (httpResult.kind === "accepted") {
      const httpExtracted = await extractTextEvidenceFromHtml(
        page,
        categorySpecs,
        httpResult.body,
        httpResult.loaded_url,
      );
      equivalence.observed_content_fingerprint_sha256 =
        officialTextContentFingerprint(httpExtracted);
      equivalence.passed = Boolean(
        frozenBaseline &&
          httpExtracted.text_available === true &&
          equivalence.observed_content_fingerprint_sha256 ===
            frozenBaseline.content_fingerprint_sha256,
      );
      if (equivalence.passed) {
        extracted = httpExtracted;
        httpStatus = httpResult.status;
        selectedTransport = "browser_context_http";
      } else {
        browserFallbackReason = frozenBaseline
          ? "http_content_missed_frozen_browser_hash"
          : "missing_frozen_browser_hash";
      }
    } else {
      browserFallbackReason = httpResult.reason;
    }
  }

  if (!extracted) {
    httpStatus = await gotoWithRetry(
      page,
      textUrl,
      "#main, main",
      browserMaxAttempts,
      scheduleRequest,
      true,
    );
    extracted = await extractTextEvidence(page, categorySpecs);
  }
  const textUnavailable =
    extracted.not_found ||
    (httpStatus !== null && httpStatus >= 400) ||
    !extracted.text_available;
  const categories = extracted.categories.map((category) => ({
    ...category,
    evidence_state: textUnavailable
      ? "official_text_unavailable"
      : category.evidence_state,
  }));
  return {
    schema: "congress-text-relevance-measure-v2",
    text_match_policy_version: TEXT_MATCH_POLICY_VERSION,
    collected_at: isoNow(),
    primary_source: "Congress.gov official measure text page",
    discovery_canonical_key: record.canonical_key,
    discovery_record_sha256: stableHash(record),
    requested_url: textUrl,
    http_status: httpStatus,
    loaded_url: extracted.loaded_url,
    page_title: extracted.page_title,
    text_available: !textUnavailable,
    not_found: extracted.not_found,
    official_text_surface_marker: extracted.official_text_surface_marker,
    shown_here_marker_found: extracted.shown_here_marker_found,
    amendment_text_marker_found: extracted.amendment_text_marker_found,
    version_label: extracted.version_label,
    official_text_character_count: extracted.official_text_character_count,
    official_text_token_count: extracted.official_text_token_count,
    official_text_fnv1a32: extracted.official_text_fnv1a32,
    transport_provenance: {
      schema: "congress-text-transport-provenance-v1",
      selected_transport: selectedTransport,
      http_fast_path_opt_in: Boolean(httpFastPath),
      browser_context_seeded_http: Boolean(httpFastPath),
      cookie_export_performed: false,
      manual_challenge_interaction_performed: false,
      stealth_escalation_performed: false,
      shared_global_request_start_limiter: true,
      browser_fallback_performed:
        Boolean(httpFastPath) && selectedTransport === "browser_navigation",
      browser_fallback_reason: browserFallbackReason,
      frozen_browser_hash_equivalence: equivalence,
      http_response:
        httpResult?.kind === "accepted"
          ? {
              status: httpResult.status,
              loaded_url: httpResult.loaded_url,
              body_sha256: httpResult.body_sha256,
              body_byte_length: httpResult.body_byte_length,
              content_type: httpResult.content_type,
              validation: httpResult.validation,
            }
          : null,
      http_attempts: httpResult?.attempts ?? [],
    },
    categories,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const runDir = assertWithinRoot(args.run);
  const registryPath = path.resolve(ROOT, args.registry);
  const outDir = assertWithinRoot(
    args.out ?? path.join(runDir, "text_relevance"),
  );
  const discoveryManifest = await readJson(path.join(runDir, "manifest.json"));
  if (discoveryManifest.status !== "complete") {
    throw new Error("Advanced Search discovery manifest is not complete");
  }
  const registryText = await fs.readFile(registryPath, "utf8");
  const registry = JSON.parse(registryText);
  const registryHash = stableHash(registryText);
  let records = await readNdjson(
    path.join(runDir, discoveryManifest.union.records_file),
  );
  const memberships = await readNdjson(
    path.join(runDir, discoveryManifest.union.memberships_file),
  );
  const categoryById = new Map(
    registry.categories.map((category) => [category.id, category]),
  );
  const queryMetaById = new Map(
    discoveryManifest.queries.map((query) => [query.query_id, query]),
  );
  const membershipIdsByRecord = new Map();
  const coverageIdsByRecord = new Map();
  for (const membership of memberships) {
    if (categoryById.has(membership.query_id)) {
      if (!membershipIdsByRecord.has(membership.canonical_key)) {
        membershipIdsByRecord.set(membership.canonical_key, []);
      }
      membershipIdsByRecord.get(membership.canonical_key).push(
        membership.query_id,
      );
    } else if (
      queryMetaById.get(membership.query_id)?.record_kind === "coverage_probe"
    ) {
      if (!coverageIdsByRecord.has(membership.canonical_key)) {
        coverageIdsByRecord.set(membership.canonical_key, []);
      }
      coverageIdsByRecord.get(membership.canonical_key).push(
        membership.query_id,
      );
    }
  }
  records = records.filter((record) =>
    membershipIdsByRecord.has(record.canonical_key) ||
    coverageIdsByRecord.has(record.canonical_key),
  );
  if (args.keys) {
    records = records.filter((record) => args.keys.has(record.canonical_key));
    const missing = [...args.keys].filter(
      (key) => !records.some((record) => record.canonical_key === key),
    );
    if (missing.length) {
      throw new Error(`Unknown selected canonical keys: ${missing.join(", ")}`);
    }
  }
  if (args.limit !== null) records = records.slice(0, args.limit);
  if (!records.length) throw new Error("No category candidates selected");
  const logicalWorkerCount = Math.min(
    args.httpFastPath ? args.httpWorkers : args.workers,
    records.length,
  );

  await fs.mkdir(outDir, { recursive: true });
  const progressFile = path.join(outDir, "progress.json");
  const eventsDir = path.join(outDir, "events");
  await fs.mkdir(eventsDir, { recursive: true });
  const runLock = await acquireRunLock(outDir);
  const partialFile = path.join(outDir, "manifest.partial.json");
  const manifestFile = path.join(outDir, "manifest.json");
  const commandLine = [
    process.execPath,
    path.relative(ROOT, fileURLToPath(import.meta.url)),
    ...process.argv.slice(2),
  ].join(" ");
  const startedMilliseconds = Date.now();
  const writeProgress = async ({
    status,
    completed,
    collected,
    resumed,
    preserved,
    failureCount = 0,
    detail = "",
  }) => {
    const elapsedSeconds = Math.max(
      0.001,
      (Date.now() - startedMilliseconds) / 1000,
    );
    const recordsPerMinute =
      completed > 0 ? completed / (elapsedSeconds / 60) : 0;
    const etaSeconds =
      recordsPerMinute > 0
        ? Math.max(0, ((records.length - completed) / recordsPerMinute) * 60)
        : null;
    await writeJson(progressFile, {
      schema_version: 1,
      updated_at: isoNow(),
      lane: "codex",
      source: "congress-full-text",
      run_id: "legislation-full-text-20260726",
      kind: "collector.progress",
      status,
      stage: "official-full-text",
      current: completed,
      total: records.length,
      summary: `${completed}/${records.length} full-text records`,
      detail:
        detail ||
        "Complete official text is checked against every assigned category identifier; absence remains neutral.",
      workers: logicalWorkerCount,
      active_workers:
        status === "running"
          ? Math.min(logicalWorkerCount, records.length - completed)
          : 0,
      collected_records: collected,
      resumed_records: resumed,
      preserved_prior_records: preserved,
      failure_count: failureCount,
      records_per_minute: Number(recordsPerMinute.toFixed(3)),
      rate: Number(recordsPerMinute.toFixed(3)),
      eta_seconds:
        etaSeconds === null ? null : Number(etaSeconds.toFixed(1)),
      command: commandLine,
      output_directory: outDir,
      candidate_deletion_allowed: false,
      absence_is_neutral: true,
    });
  };
  const manifest = {
    schema: "congress-text-relevance-enrichment-manifest-v2",
    text_match_policy_version: TEXT_MATCH_POLICY_VERSION,
    status: "running",
    started_at: isoNow(),
    completed_at: null,
    primary_source: "Congress.gov official measure text pages",
    discovery_manifest: path
      .relative(ROOT, path.join(runDir, "manifest.json"))
      .split(path.sep)
      .join("/"),
    discovery_records_sha256: discoveryManifest.union.records_sha256,
    registry_file: path.relative(ROOT, registryPath).split(path.sep).join("/"),
    registry_sha256: registryHash,
    selected_record_count: records.length,
    completed_records: [],
    worker_count: logicalWorkerCount,
    global_request_start_delay_ms: args.delayMs,
    minimum_request_start_interval_preserved: true,
    transport_policy: {
      default_transport: "browser_navigation",
      http_fast_path_opt_in: args.httpFastPath,
      browser_context_seeded_http: args.httpFastPath,
      logical_http_worker_count: args.httpFastPath
        ? logicalWorkerCount
        : 0,
      http_max_attempts: args.httpFastPath ? args.httpMaxAttempts : 0,
      http_retry_base_ms: args.httpFastPath ? args.httpRetryBaseMs : null,
      browser_max_attempts: args.browserMaxAttempts,
      frozen_browser_hash_equivalence_required: args.httpFastPath,
      unsafe_http_response_browser_fallback_required: args.httpFastPath,
      cookie_export_performed: false,
      manual_challenge_interaction_performed: false,
      stealth_escalation_performed: false,
    },
    destructive_filtering: false,
    exclusion_decisions_made: 0,
  };
  await writeJson(partialFile, manifest);

  const context = await chromium.launchPersistentContext(args.profile, {
    executablePath: args.chrome,
    headless: args.headless,
    ignoreDefaultArgs: ["--enable-automation"],
    args: ["--disable-blink-features=AutomationControlled"],
    viewport: { width: 1400, height: 900 },
  });
  const artifacts = new Array(records.length);
  const completedEntries = new Array(records.length);
  try {
    const pages = [context.pages()[0] || (await context.newPage())];
    while (
      pages.length < logicalWorkerCount
    ) {
      pages.push(await context.newPage());
    }
    const scheduleRequest = createGlobalRateLimiter(args.delayMs);
    const httpFastPath = args.httpFastPath
      ? createCongressContextHttpFastPath({
          requestContext: context.request,
          scheduleRequest,
          maxAttempts: args.httpMaxAttempts,
          retryBaseMs: args.httpRetryBaseMs,
        })
      : null;
    let resumedCount = 0;
    let collectedCount = 0;
    let noRegressionPreservedCount = 0;
    let completedCount = 0;
    let nextIndex = 0;
    let fatalError = null;
    let checkpointQueue = Promise.resolve();
    await writeProgress({
      status: "running",
      completed: 0,
      collected: 0,
      resumed: 0,
      preserved: 0,
    });
    await writeGlassboxEvent(eventsDir, 0, "run", {
      kind: "collector.started",
      status: "running",
      stage: "official-full-text",
      summary: `0/${records.length} full-text records | ${logicalWorkerCount} workers`,
      detail:
        "All harvested candidates are retained while complete official text is checked against the 210 category identifiers.",
      command: commandLine,
      input: {
        records: records.length,
        discovery_memberships: memberships.length,
        category_identifiers: registry.categories.reduce(
          (count, category) => count + category.identifiers.length,
          0,
        ),
      },
      output: outDir,
      current: 0,
      total: records.length,
    });

    const processRecord = async (page, index, workerId) => {
      const record = records[index];
      const queryIds = canonicalKeySet(
        membershipIdsByRecord.get(record.canonical_key) ?? [],
      );
      const coverageIds = canonicalKeySet(
        coverageIdsByRecord.get(record.canonical_key) ?? [],
      );
      const selectedCategoryIds = queryIds.length
        ? queryIds
        : [...categoryById.keys()];
      const evidenceRole = queryIds.length
        ? "category_membership"
        : "coverage_probe_classification";
      const categorySpecs = selectedCategoryIds.map((queryId) => {
        const category = categoryById.get(queryId);
        return {
          query_id: queryId,
          label: category.label,
          evidence_role: evidenceRole,
          source_coverage_probe_ids: queryIds.length ? [] : coverageIds,
          identifiers: category.identifiers.map((item) => item.text),
        };
      });
      const membershipHash = stableHash(categorySpecs);
      const measureFile = path.join(
        outDir,
        "raw",
        String(record.congress),
        record.type,
        `${record.number}.json`,
      );
      let artifact = null;
      let priorRead = null;
      try {
        priorRead = await readJsonWithFileHash(measureFile);
        if (
          priorRead.artifact.artifact_integrity_sha256 &&
          priorRead.artifact.artifact_integrity_sha256 !==
            artifactIntegritySha256(priorRead.artifact)
        ) {
          throw new Error(
            `Existing text artifact failed integrity validation: ${measureFile}`,
          );
        }
      } catch (error) {
        if (error.code !== "ENOENT") throw error;
      }
      const recordHash = stableHash(record);
      const priorInputsCurrent = Boolean(
        priorRead &&
          priorRead.artifact.discovery_canonical_key === record.canonical_key &&
          priorRead.artifact.discovery_record_sha256 === recordHash &&
          priorRead.artifact.registry_sha256 === registryHash &&
          priorRead.artifact.membership_sha256 === membershipHash &&
          priorRead.artifact.text_match_policy_version ===
            TEXT_MATCH_POLICY_VERSION,
      );
      if (args.resume) {
        if (priorInputsCurrent) {
          artifact = priorRead.artifact;
          resumedCount += 1;
        }
      }
      if (!artifact) {
        const candidate = await collectMeasure(
          page,
          record,
          categorySpecs,
          scheduleRequest,
          {
            httpFastPath,
            browserMaxAttempts: args.browserMaxAttempts,
            frozenBaseline: frozenBrowserBaseline(
              priorRead?.artifact,
              priorRead?.file_sha256,
            ),
          },
        );
        candidate.registry_sha256 = registryHash;
        candidate.membership_sha256 = membershipHash;
        candidate.artifact_integrity_sha256 =
          artifactIntegritySha256(candidate);

        if (
          priorInputsCurrent &&
          priorRead.artifact.text_available === true &&
          candidate.text_available !== true
        ) {
          await writeImmutableTransportReceipt(outDir, record, {
            decision: "preserve_prior_no_regression",
            reason: "candidate_lost_previously_verified_official_text",
            preserved_artifact_file: path
              .relative(outDir, measureFile)
              .split(path.sep)
              .join("/"),
            preserved_artifact_file_sha256: priorRead.file_sha256,
            preserved_artifact_integrity_sha256:
              priorRead.artifact.artifact_integrity_sha256 ?? null,
            candidate_artifact_integrity_sha256:
              candidate.artifact_integrity_sha256,
            candidate_transport_provenance:
              candidate.transport_provenance,
            candidate_content_projection:
              officialTextContentProjection(candidate),
          });
          artifact = priorRead.artifact;
          noRegressionPreservedCount += 1;
        } else {
          const receipt = await writeImmutableTransportReceipt(
            outDir,
            record,
            {
              decision: "accept_collected_artifact",
              candidate_artifact_integrity_sha256:
                candidate.artifact_integrity_sha256,
              selected_transport:
                candidate.transport_provenance.selected_transport,
              transport_provenance: candidate.transport_provenance,
              content_projection:
                officialTextContentProjection(candidate),
            },
          );
          candidate.transport_receipt = receipt;
          candidate.artifact_integrity_sha256 =
            artifactIntegritySha256(candidate);
          await writeJson(measureFile, candidate);
          artifact = candidate;
        }
        collectedCount += 1;
      }
      artifacts[index] = artifact;
      completedEntries[index] = {
        canonical_key: record.canonical_key,
        file: path.relative(outDir, measureFile).split(path.sep).join("/"),
        text_available: artifact.text_available,
        membership_count: artifact.categories.length,
        localized_membership_count: artifact.categories.filter(
          (item) => item.localized_identifier_count,
        ).length,
      };
      completedCount += 1;
      const localizedCategories = artifact.categories
        .filter((item) => item.localized_identifier_count)
        .map((item) => ({
          query_id: item.query_id,
          identifiers: item.localized_identifiers,
        }));
      await writeGlassboxEvent(
        eventsDir,
        completedCount,
        record.canonical_key,
        {
          kind: "collector.record.completed",
          status: artifact.text_available ? "completed" : "needs-review",
          stage: `worker-${workerId}`,
          summary:
            `${completedCount}/${records.length} ${record.canonical_key} | ` +
            `${artifact.text_available ? "text verified" : "text unavailable"} | ` +
            `${localizedCategories.length} category signal(s)`,
          detail:
            "Identifier absence is neutral; this record remains preserved unless a separate provenance-complete review decision is made.",
          command: `GET ${artifact.requested_url}`,
          input: {
            canonical_key: record.canonical_key,
            assigned_categories: categorySpecs.map((category) => ({
              query_id: category.query_id,
              identifiers: category.identifiers,
            })),
          },
          output: {
            loaded_url: artifact.loaded_url,
            text_available: artifact.text_available,
            version_label: artifact.version_label,
            official_text_character_count:
              artifact.official_text_character_count,
            official_text_token_count: artifact.official_text_token_count,
            localized_categories: localizedCategories,
            selected_transport:
              artifact.transport_provenance?.selected_transport ?? null,
            artifact_integrity_sha256:
              artifact.artifact_integrity_sha256 ?? null,
          },
          artifact: path.relative(ROOT, measureFile).split(path.sep).join("/"),
          current: completedCount,
          total: records.length,
        },
      );
      if (
        completedCount === records.length ||
        completedCount % 10 === 0
      ) {
        await writeProgress({
          status: "running",
          completed: completedCount,
          collected: collectedCount,
          resumed: resumedCount,
          preserved: noRegressionPreservedCount,
        });
      }
      if (completedCount % 100 === 0 || completedCount === records.length) {
        const snapshot = {
          ...manifest,
          completed_records: completedEntries.filter(Boolean),
        };
        checkpointQueue = checkpointQueue.then(() =>
          writeJson(partialFile, snapshot),
        );
        console.log(
          `TEXT PROGRESS ${completedCount}/${records.length}: ` +
            `${collectedCount} collected, ${resumedCount} resumed, ` +
            `${noRegressionPreservedCount} prior artifact(s) preserved`,
        );
      }
    };

    const worker = async (page, workerId) => {
      while (!fatalError) {
        const index = nextIndex;
        nextIndex += 1;
        if (index >= records.length) return;
        try {
          await processRecord(page, index, workerId);
        } catch (error) {
          fatalError ??= error;
          return;
        }
      }
    };

    await Promise.all(pages.map((page, index) => worker(page, index + 1)));
    await checkpointQueue;
    if (fatalError) throw fatalError;
    if (artifacts.filter(Boolean).length !== records.length) {
      throw new Error("Concurrent text collection left an incomplete artifact set");
    }
    manifest.completed_records = completedEntries;

    const ledger = [];
    for (const artifact of artifacts) {
      for (const category of artifact.categories) {
        ledger.push({
          canonical_key: artifact.discovery_canonical_key,
          query_id: category.query_id,
          category_label: category.label,
          evidence_role: category.evidence_role,
          source_coverage_probe_ids:
            category.source_coverage_probe_ids ?? [],
          evidence_state: category.evidence_state,
          text_available: artifact.text_available,
          version_label: artifact.version_label,
          official_text_character_count:
            artifact.official_text_character_count,
          official_text_token_count: artifact.official_text_token_count,
          localized_identifier_count: category.localized_identifier_count,
          localized_identifiers: category.localized_identifiers,
          separated_identifier_count: category.separated_identifier_count,
          separated_identifiers: category.separated_identifiers,
          identifier_evidence: category.identifiers,
          source_url: artifact.loaded_url,
          candidate_retained_in_discovery_corpus: true,
          exclusion_decision: null,
        });
      }
    }
    ledger.sort((left, right) =>
      `${left.query_id}:${left.canonical_key}`.localeCompare(
        `${right.query_id}:${right.canonical_key}`,
        undefined,
        { numeric: true },
      ),
    );
    const unresolved = ledger.filter(
      (row) => row.evidence_state !== "localized_official_text_evidence",
    );
    const ledgerFile = path.join(outDir, "text_relevance_evidence.ndjson");
    const unresolvedFile = path.join(
      outDir,
      "text_relevance_unresolved.ndjson",
    );
    await writeNdjson(ledgerFile, ledger);
    await writeNdjson(unresolvedFile, unresolved);
    manifest.status = "complete";
    manifest.completed_at = isoNow();
    manifest.membership_count = ledger.length;
    manifest.actual_category_membership_evidence_count = ledger.filter(
      (row) => row.evidence_role === "category_membership",
    ).length;
    manifest.coverage_probe_classification_evidence_count = ledger.filter(
      (row) => row.evidence_role === "coverage_probe_classification",
    ).length;
    manifest.localized_official_text_membership_count = ledger.filter(
      (row) => row.evidence_state === "localized_official_text_evidence",
    ).length;
    manifest.unresolved_membership_count = unresolved.length;
    manifest.text_unavailable_record_count = artifacts.filter(
      (artifact) => !artifact.text_available,
    ).length;
    manifest.transport_summary = {
      collected_record_count: collectedCount,
      resumed_record_count: resumedCount,
      no_regression_preserved_record_count:
        noRegressionPreservedCount,
      browser_navigation_record_count: artifacts.filter(
        (artifact) =>
          (artifact.transport_provenance?.selected_transport ??
            "browser_navigation") === "browser_navigation",
      ).length,
      browser_context_http_record_count: artifacts.filter(
        (artifact) =>
          artifact.transport_provenance?.selected_transport ===
          "browser_context_http",
      ).length,
      http_fast_path: httpFastPath?.snapshot() ?? null,
    };
    manifest.ledger_file = path
      .relative(outDir, ledgerFile)
      .split(path.sep)
      .join("/");
    manifest.ledger_sha256 = stableHash(ledger);
    manifest.unresolved_file = path
      .relative(outDir, unresolvedFile)
      .split(path.sep)
      .join("/");
    manifest.unresolved_sha256 = stableHash(unresolved);
    await writeJson(manifestFile, manifest);
    await removeWithRetry(partialFile);
    await writeProgress({
      status: "complete",
      completed: records.length,
      collected: collectedCount,
      resumed: resumedCount,
      preserved: noRegressionPreservedCount,
      detail:
        "Official-text evidence collection completed; no exclusion or production write was performed.",
    });
    await writeGlassboxEvent(eventsDir, records.length + 1, "run-complete", {
      kind: "collector.completed",
      status: "completed",
      stage: "official-full-text",
      summary: `${records.length}/${records.length} full-text records complete`,
      detail:
        `${ledger.length} category evidence rows emitted; ${unresolved.length} remain unresolved without a localized official-text signal.`,
      command: commandLine,
      output: {
        manifest: path.relative(ROOT, manifestFile).split(path.sep).join("/"),
        ledger: path.relative(ROOT, ledgerFile).split(path.sep).join("/"),
        unresolved: path.relative(ROOT, unresolvedFile).split(path.sep).join("/"),
      },
      current: records.length,
      total: records.length,
    });
    console.log(
      `COMPLETE: ${ledger.length} category membership(s), ` +
        `${unresolved.length} without localized official-text evidence`,
    );
  } catch (error) {
    manifest.status = "failed";
    manifest.failed_at = isoNow();
    manifest.completed_records = completedEntries.filter(Boolean);
    manifest.error = {
      name: error.name,
      message: error.message,
      stack: error.stack,
    };
    await writeJson(partialFile, manifest);
    await writeProgress({
      status: "failed",
      completed: manifest.completed_records.length,
      collected: 0,
      resumed: 0,
      preserved: 0,
      failureCount: 1,
      detail: error.message,
    }).catch(() => {});
    await writeGlassboxEvent(
      eventsDir,
      manifest.completed_records.length + 1,
      "run-failed",
      {
        kind: "collector.failed",
        status: "failed",
        stage: "official-full-text",
        summary:
          `${manifest.completed_records.length}/${records.length} before failure`,
        detail:
          "Failure is quarantined; preserved discovery and completed evidence artifacts are not deleted.",
        command: commandLine,
        failure: {
          name: error.name,
          message: error.message,
        },
        current: manifest.completed_records.length,
        total: records.length,
      },
    ).catch(() => {});
    throw error;
  } finally {
    await context.close();
    await releaseRunLock(runLock);
  }
}

const isDirectExecution =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isDirectExecution) {
  await main();
}

export {
  artifactIntegritySha256,
  extractTextEvidence,
  extractTextEvidenceFromHtml,
  frozenBrowserBaseline,
  officialTextContentFingerprint,
  officialTextContentProjection,
  TEXT_MATCH_POLICY_VERSION,
};
