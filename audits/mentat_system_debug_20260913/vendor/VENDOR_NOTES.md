# PptxGenJS browser bundle — vendoring notes

Fetched: 2026-09-14
Destination: scratchpad only — `vendor\` under this session's scratchpad. No repository files were touched; the Mentat tree was not accessed.

## Source resolution

- Registry queried: https://registry.npmjs.org/pptxgenjs (reachable; fetched via PowerShell `System.Net.WebClient` with TLS 1.2 forced — Git Bash `curl` was not attempted first per the task's known-failure note, PowerShell was used directly).
- `dist-tags.latest` = **4.0.1** (this matches the pinned fallback version given in the task, so no fallback was actually needed).
- `versions["4.0.1"].license` = **MIT**
- `versions["4.0.1"].dist.tarball` = `https://registry.npmjs.org/pptxgenjs/-/pptxgenjs-4.0.1.tgz`
- `versions["4.0.1"].dist.shasum` (npm SHA-1) = `cd0f202f62f74d950bcd217e90b766da8f73742e`

## Download and extraction

- Tarball downloaded with PowerShell `WebClient` (TLS 1.2, retry loop, succeeded on attempt 1) to a scratch build folder (`..\_pptxgenjs_build\`, sibling of `vendor\`, not part of the deliverable).
- Downloaded tarball: 813,698 bytes; SHA-1 verified with `Get-FileHash -Algorithm SHA1` = `cd0f202f62f74d950bcd217e90b766da8f73742e` — **matches registry `dist.shasum` exactly**, confirming an uncorrupted download.
- Extracted with `tar -xzf` (Git Bash / GNU tar 1.35).
- `package/dist/` contents: `pptxgen.bundle.js`, `pptxgen.bundle.js.map`, `pptxgen.cjs.js`, `pptxgen.es.js`, `pptxgen.min.js`, `pptxgen.min.js.map`.
- Exact file used: **`package/dist/pptxgen.bundle.js`** — the UMD bundle that includes JSZip, per the task's instruction. It was **copied verbatim, byte-for-byte**, not edited.

## Files placed in `vendor\`

| File | Purpose |
|---|---|
| `pptxgen.bundle.js` | UMD browser bundle (PptxGenJS 4.0.1 + bundled JSZip), copied unmodified from `package/dist/pptxgen.bundle.js` |
| `LICENSE-pptxgenjs.md` | Upstream `package/LICENSE` (MIT), prefixed with one attribution line |
| `VENDOR_NOTES.md` | This file |

## `pptxgen.bundle.js` — integrity

- Byte size: **460,889 bytes** (identical to the size of `package/dist/pptxgen.bundle.js` inside the extracted tarball — confirms a clean, unmodified copy).
- SHA-256: **`4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8`**
  - Computed twice, independently, with identical results: PowerShell `Get-FileHash -Algorithm SHA256` and Git Bash `sha256sum`.

## Sanity check 1 — content flags

Command:
```
node -e "const s=require('fs').readFileSync('<bundle>','utf8'); console.log(s.length, /PptxGenJS/.test(s), /JSZip/.test(s), /eval\(/.test(s))"
```
Result: `460736 true true false`

- String length (460,736 UTF-16 units) differs from the on-disk byte size (460,889 bytes) only because a handful of multi-byte UTF-8 sequences (e.g. the em dash in the header comment `/* PptxGenJS 4.0.1 @ ... */`-adjacent text and minified Unicode escapes) decode to fewer UTF-16 code units than their UTF-8 byte count — not corruption, not an edit.
- `/PptxGenJS/` → true (present, as expected).
- `/JSZip/` → true (bundled dependency present, as expected — 7 occurrences, including JSZip's own UMD banner and internal error strings).
- `/eval\(/` → **false — no `eval(` call anywhere in the bundle.**

## Sanity check 2 — global export behavior

This needed more than the literal one-liner in the task to get a trustworthy answer, so both the literal check and a corrected simulation are recorded.

**Literal check as specified** (`global.window=global; require('<bundle>')`) — **throws**:
```
ReferenceError: JSZip is not defined
```
Thrown at the trailing `(function(B){ ... })(JSZip)` call inside the file.

**Root cause (bundle structure, not corruption):** `pptxgen.bundle.js` is a straight concatenation of two independently-built pieces, with no wrapper tying them together:
1. **JSZip**, bundled via Browserify with its own textbook 3-way UMD ternary: `typeof exports==='object' && typeof module!=='undefined' ? module.exports=e() : typeof define==='function'&&define.amd ? define([],e) : (window|global|self|this).JSZip=e()`.
2. **PptxGenJS itself**, appended right after, as a bare top-level statement with *no* UMD wrapper of its own: `var PptxGenJS=(B=>{ ... })(JSZip);` — this simply reads whatever `JSZip` currently resolves to in scope.

Under Node's `require()`, Node *always* injects real `module`/`exports` objects into the file's wrapper scope — that's what makes it a CommonJS module. So piece 1's ternary takes the **first** branch (`module.exports = e()`, i.e. `module.exports` becomes **JSZip**, not PptxGenJS) instead of the "assign to global" branch — meaning `global.JSZip`/`window.JSZip` is never set. Piece 2 then dereferences the bare identifier `JSZip`, finds nothing, and throws. This reproduced consistently and is inherent to the file, not an artifact of a bad copy (confirmed against the untouched, hash-verified file).

**Corrected simulation of the actual target environment** (a real `<script src="pptxgen.bundle.js">` tag has no `exports`/`module`/`define` in scope at all): ran the file through Node's `vm.createContext`/`vm.runInContext` with a bare sandbox object (`sandbox.window = sandbox`, no `module`/`exports`/`define` defined anywhere), i.e. the same "no CJS/AMD host" condition a browser provides:

```
typeof window.JSZip     = function
typeof window.PptxGenJS = function
```

**Conclusion:** the bundle *does* correctly define a global — **`window.PptxGenJS`** (plus `window.JSZip` as a side effect) — but only in an environment with no `exports`/`module`/`define` visible, i.e. a plain `<script>` tag in a browser (or an equivalent sandboxed/global-only evaluation). It is **not require()-able from Node as-is**: Node's CJS wrapper makes JSZip's own UMD branch hijack `module.exports` and leaves PptxGenJS's trailing statement unable to find `JSZip`. This is expected for a browser-targeted UMD artifact and is not something to fix — **the bundle was not modified.** Practical takeaway for whoever consumes this vendor file: load it with a plain `<script>` tag, then read `window.PptxGenJS` (and note `window.JSZip` will also be a global as a side effect) — do not `require()`/`import` it in Node.

## What was not done

- Nothing was installed globally.
- The Mentat tree was not touched.
- No repository files were written; everything above lives under this session's scratchpad `vendor\` (plus the sibling scratch build folder `_pptxgenjs_build\` holding the raw registry JSON, the downloaded `.tgz`, and the full extracted tarball, kept for traceability but not part of the deliverable).
- `pptxgen.bundle.js` itself was not edited in any way.
