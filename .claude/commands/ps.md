# /ps — work through visible PowerShell (glass-box mode)

Every action that writes code or extracts data happens as a PowerShell
command in the transcript, not through opaque built-in tools.

Usage: `/ps <task>` — run the task in glass-box mode.

- File writes: single-quoted here-strings (`@'...'@`, closing `'@` at
  column 0) piped to `Set-Content -Encoding utf8`. The full file content
  appears inside the command — never hide or truncate it.
- Data extraction: `Get-Content`, `Select-String`, `Import-Csv`,
  `ConvertFrom-Json` — every read is a visible command Paul can re-run.
- Codex-lane dispatches write out-of-band: immediately after, surface
  the result with `git -C <tree> diff` and file previews so the trail
  stays unbroken end-to-end.
- Genuine exceptions (images, .ipynb, openpyxl workbook writes, files
  too large for one command): declare the exception loudly, then show
  the closest before/after PowerShell extraction of what changed.
- Sandbox prompts on writes are expected — they are the confirmation
  step, not a failure. A denied prompt means stop and ask, never retry
  around it.
