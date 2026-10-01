---
description: Route a build task through the Codex executor lane (Claude specs + reviews, Codex gpt-5.6-sol executes)
argument-hint: <task to dispatch to Codex>
---
Invoke the codex-executor skill and route the following task through its full
protocol: Claude writes the spec (objective, constraints, numbered acceptance
criteria, impact envelope, confirmation conditions), dispatches implementation
to Codex via the codex MCP tools (throwaway codex/* worktree, sandbox
workspace-write, capability handshake + plan echo before edits), reviews the
returned diff and acceptance evidence for architecture + security, iterates
via codex-reply until clean, runs verification, dispatches the second
independent read-only Codex review round for any non-trivial diff (double
sign-off), and presents the result at Paul's gate.

If the codex MCP tools are unavailable in this session, say so and offer either
a fresh session (where .mcp.json loads) or the stdio fallback described in the
codex-executor skill — do not silently do the implementation yourself.

Task: $ARGUMENTS
