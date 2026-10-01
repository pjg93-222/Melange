---
name: grok-companion
description: >-
  Grok (xAI, Grok Build CLI, SuperGrok subscription) as Fable's adversarial
  counsel — the brutally honest critic that attacks plans, claims, and
  syntheses before they ship. Minor secondary orchestrator: counsel to
  Claude, zero execution authority, zero veto. Use for high-stakes critique
  passes, when Paul asks for the fear factor, or via /grok. Also owns the
  LIVE no-API-key X search lane and the Monday catalog collector.
---

# Grok companion protocol

Hierarchy (Paul, 2026-07-24): **Fable (Claude) commands; Grok is Fable's
adversarial counsel — the fear factor beside the greater reasoning; Codex
executes; Gemini perceives.** Grok critiques whatever Fable puts in front
of it with maximum severity and zero diplomacy. It holds no execution
authority, no veto, and no gate: every Grok verdict is an input Fable
adjudicates, exactly like an executor review round. Grok never writes
code, never touches git, never dispatches the other lanes.

Universal lane laws: `.claude/commands/metaloop.md` § UNIVERSAL LANE LAWS
binds this lane in and out of Meta LOOP runs — role monopolies,
escalate-don't-reason, never-downgrade, glasseye, one-writer, copy-sync.

## Critique contract

Every companion dispatch carries:

1. `TARGET`: the plan, claim set, synthesis, or design under attack,
   verbatim or by exact file reference.
2. `ATTACK SURFACE`: numbered aspects to assault (logic, evidence,
   feasibility, cost, blind spots, wishful thinking).
3. `OUTPUT SHAPE`: end with four labeled lists (citation form permanent,
   Paul 2026-08-10) —
   KILLED: <claims/steps that do not survive — each with the kill shot AND the exact target location (file:line, or the quoted span for inline targets)>
   WOUNDED: <survives only with the named repair — each with the exact target location>
   SURVIVES: <held up under attack, why the attack failed — each with the exact target location>
   BLOCKED: <lane-level trouble — CLI, auth, or balance failure, missing target file, contract defect; or none>
   A quoted span must include local negation or qualification — a quote
   clipped to invert its meaning is a false cite.
4. `PROHIBITIONS`: no softening, no praise padding, no invented facts —
   every attack cites the target's own text or a checkable external fact;
   uncertainty is stated as uncertainty, not dressed as a kill.

Fable adjudicates each KILLED/WOUNDED item: accept (fix or withdraw),
reject with reasons (recorded), or escalate to Paul. Adjudication checks
cite-correctness, not cite-presence: each cite is resolved and checked
that it supports the point; an uncited, false-cited, or unresolvable
point is not adjudicated on persuasiveness — it is returned once for
correct citation and dropped if it returns uncorrected. A Grok kill that
Fable rejects twice on the same target is itself escalated — the
disagreement is the signal. A BLOCKED report is a capability failure,
not a critique: Fable emits the lane skip and reroutes per the
universal laws.

## When to invoke

Only as needed — mirroring the Gemini rule: high-stakes syntheses,
plans preceding irreversible or expensive steps, claims headed for Paul's
gates, or whenever Paul asks. Routine mechanical work does not get a
critique pass; never invent one to use the lane. Tiered verification
(Paul 2026-08-11): a diff reaches this lane only when it is material
AND the free tier — execution, tests, schema validation — has already
passed; never pay critique rates to find what the interpreter finds
free.

## Runtime

- CLI: Grok Build (`grok`) 0.2.112 stable at
  `C:\Users\pgoff\.grok\bin\grok.exe`. Sign-in: browser OAuth on Paul's
  SuperGrok account (cached; credentials never handled by Claude).
- Model: grok-4.5 (self-reported on first dispatch). Never downgrade
  without Paul's instruction.

Verified invocation (2026-07-24) - write the critique contract BOM-free
to critique_contract.txt in the working directory, then:

```powershell
$env:Path = "C:\Users\pgoff\.grok\bin;$env:Path"
grok -p "Read critique_contract.txt in the current directory and execute the critique dispatch it contains exactly as specified, ending with the three labeled lists."
```

Load-bearing facts, verified live:

- Headless -p WORKS on cached subscription OAuth locally; the API-key
  requirement applies only to environments without a cached browser
  sign-in.
- Contract delivery is FILE-BASED: embedded double quotes in a -p
  argument shatter PowerShell 5.1 native-command quoting, and stdin
  piping is not consumed in -p mode.
- First-dispatch calibration: killed two planted bad claims with correct
  kill shots (universal-quantifier overreach; model-vs-tool-layer
  conflation) and wounded a true-but-unevidenced claim by demanding
  evidence objects and temporal scoping - severity on-charter, zero
  fabrication, exact three-list compliance.

## X search lane (VERIFIED LIVE 2026-07-24 — no API key)

The SuperGrok subscription CLI natively carries the X toolset server-side:
x_keyword_search (from:/since:/until: operators — handle AND date filters
LIVE-VERIFIED), x_semantic_search (subject-matter semantic search with
usernames + from_date/to_date), x_user_search, x_thread_fetch. The xAI
developer API is NOT needed for any of this. Ad-hoc searches dispatch via
the standard file-based contract; subject via query, handles and dates as
hard filters. LOCATION REMAINS A SOFT FILTER ONLY - no native
zipcode/coordinate parameter exists anywhere in the toolset; geo-targeting
rides on prompt-level reasoning and is never claimed as a hard guarantee.

## Monday catalog collector (OPERATIONAL)

`scripts/monday_x_collector.py` (Codex-authored under the full loop, 26
offline tests + live smoke). Harvests new posts from the 506 stored
legislator handles (legislators_social_media.json social.twitter) via
sequential headless grok x_keyword_search batches and appends
`x_catalog.jsonl` at the live-tree root — additive data-plane artifact,
dedup on url else sha256(handle+utc_date+text); NEVER touches
quorum_member_tweets.csv or any stance input, which stay behind Paul's
gates. State/log/FAILED.marker in %LOCALAPPDATA%\melange_x_collector\
(non-OneDrive) with a single-instance PID lock. Gate: runs when today is
Monday OR last success is >7 days old (or --force); window = last success
minus 1 day (first run: 8 days back); failed batches carry to the next
run; last_success advances only on a zero-failure run. Armed via a Startup-folder shim (MelangeXCollector.cmd in shell:startup, pythonw, at every logon; the script self-gates) - Task Scheduler registration was denied unelevated. Manual run:

```powershell
python "<live>\.claude\skills\grok-companion\scripts\monday_x_collector.py" --force
```

Verified runtime reality (2026-07-24 forensics): x_keyword_search returns ~10 results per call - the prompt mandates pagination (up to 10 calls per batch, 5 handles per batch); harvest completeness is model-mediated best-effort. NEVER smoke-test against the production state dir without --state-dir override. Accepted residuals (documented, not defects to re-flag): the dedupe key
set loads fully into memory (years of weekly volume before it matters);
harvest completeness is model-mediated best-effort, not a raw API
guarantee. Windows lesson baked into the code: subprocess reader threads
SWALLOW UnicodeDecodeError — capture binary, decode strict in the caller.

Staffer/constituent handles: not in the current stores (staff_directory
has no X handles); extend via an additive handles file when Paul supplies
them.
## Copy sync

The repository copy is canonical. After a ratified change, sync this
`SKILL.md`, `scripts/` (collector + tests), `.claude/commands/grok.md`,
and `.claude/commands/metaloop.md` to
`C:\Users\pgoff\.claude\skills\grok-companion\` and
`C:\Users\pgoff\.claude\commands\`.