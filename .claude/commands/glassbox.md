---
description: Open the live GLASS BOX orchestration dashboard and four lane data streams
---

# /glassbox - open observable orchestration

Run:

`& C:\Users\pgoff\.claude\glassbox\launch.ps1`

This launches one orchestration dashboard plus the Claude, Codex, Grok, and
Gemini data-stream windows. It is idempotent: healthy existing windows are
reused.

After launch, run:

`& C:\Users\pgoff\.claude\glassbox\health.ps1 -RequireAll`

Report the five health rows exactly. If any view is down, report the failed
role and stop. Do not claim visibility from a queued hello or silently replace
a missing lane.

