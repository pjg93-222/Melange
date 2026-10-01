# Institutional evidence experiment

Separate research generation in `outputs/cosponsor_institutions_20260905`. Extends the sealed continuing-member study with dated caucus, committee and raw voting evidence. It does not change production, prior forecasts, prior experiment files or the external Project Brain.

Read `PROTOCOL.md` and the output `REPORT.md` first. The exact 377-member cohort, full-panel row indices, 30-day horizons and weighted training sample are inherited. Both 2023 and 2024 are previously examined development data. Congress 119 outcomes are not used.

Execution order, in a fresh separate output generation if reproducing:

1. Retain the source bytes declared in the three feature receipts. The builders intentionally preserve full original metadata row order; caucus extraction precedes its build. Do not substitute current rosters or undated public pages.
2. Run source reviews and `institutions_review_caucus.py`. Independent committee and voting reviews describe semantic limitations. `institutions_model_review.json` checks harness/sample/alignment and source closure.
3. Run `institutions_models.py`. It freezes protocol, code, inputs, feature groups and 70 contrasts before fitting. It fits 13 new models and copies four exact frozen references. Every forecast and the 2023-selected winner are frozen before the new 2024 metrics.
4. Run `institutions_statistics.py` and then `institutions_verify.py`. Statistics use 100,000 whole-family resamples, with multiplicity adjustment separately for precision and Brier. Verify saved forecasts and recount metrics independently.
5. Run `institutions_report.py` with the separately recorded Matplotlib environment. Review its complete numeric tables and interpretation; render the PNG for visual inspection.
6. Run `institutions_finalize.py --draft-only`, independently check final claims, then run `institutions_finalize.py` to seal. Existing final output files must not be overwritten. `code_snapshot.zip` preserves exact bytes independently of Git line-ending conversion.

The default Python handles models/statistics/verification. The existing isolated renderer is `C:/Users/pgoff/AppData/Local/Melange/research_runtime/cosponsor_universe_20260905/Scripts/python.exe`; its versions are recorded separately. No package installation is required.

The historical caucus membership subset is Problem Solvers only. Committee source update dates are not first publication dates; the four event-dated hearing features are sensitivity-only and cannot win selection. Recorded assignments/opportunities are not attendance or lobbying effects. These models estimate observed legislative actions, not persuasion susceptibility.
