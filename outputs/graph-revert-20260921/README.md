# Graph rollback

Restored `graph.js`, `graph.css`, and `templates/view_graph.html` byte-for-byte from the saved pre-redesign files in `outputs/visual-analysis-implementation-20260921/pre-edit/`. Restored the original shared Graph rules and scoped its original shell appearance to Graph. Regenerated the console and restarted port 8806.

The live screenshot confirms the original summary totals above side-by-side recipient-type and candidate charts. Direct browser verification passed for that composition, recipient navigation, returning from Insights, and absence of page errors or stale-build warnings. PAC evidence and Insights assets retain their prior SHA-256 values; see `receipt.json`.

The original large-fixture regression test rendered the expected 42 marks but timed out on its historical exact request-count assertion at line 111. It is not recorded as passed. Its redesign-specific test changes were reverted along with Graph. No further UI redesign was performed.

Current screenshot: `restored-graph-1440.png`.
