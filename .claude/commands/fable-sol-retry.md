# Bounded Fable revision

Run the repository controller:

```powershell
python .claude/skills/codex-executor/scripts/fable_sol_cli.py `
  --prompt-file <path> `
  --fable-command-json '["<fable-review-executable>","<arg>"]'
```

The Fable process receives one JSON object on stdin:

```json
{"action":"review","prompt":"...","attempt":1}
```

It returns one JSON object on stdout:

```json
{
  "output": "...",
  "reasoning_backend": "claude-fable-5",
  "review_completed": true,
  "flags": []
}
```

If Fable reports any flag or an actual backend containing `opus`, the
controller asks Sol to revise the prompt and submits that revision to Fable.
The cycle is bounded (five attempts by default), rejects repeated prompts,
fails closed on incomplete reviews, and records every event in SQLite.

By default Sol runs through the installed Codex CLI as `gpt-5.6-sol` with
xhigh effort, priority service, a read-only sandbox, an ephemeral session, and
a schema-constrained response. A custom Sol process can instead be supplied
with `--sol-command-json`.

The Anthropic Fable adapter is available only through the explicit
`--allow-paid-api --fable-api-key-file <path>` combination. Never include a
key in a prompt, command value, ledger payload, or log.
