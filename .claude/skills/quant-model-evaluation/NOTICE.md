# NOTICE: sources, adaptations and licenses

`quant-model-evaluation` is a synthesis. Its protocol, module text and scripts were written for this skill. Parts of the statistical core, the simulation and validation methods, and the checklists paraphrase ideas from K-Dense-AI's `scientific-agent-skills` collection. No K-Dense prose was copied; any short code adaptation is marked in a header comment in the script that carries it and listed below.

## K-Dense-AI/scientific-agent-skills

- Repository: https://github.com/K-Dense-AI/scientific-agent-skills (formerly `claude-scientific-skills`)
- Version read: git tree `65d6e786832e2c52832713117bbbf5096b56f77f`, branch `main`, package version 2.70.0, fetched 2026-09-29.
- Described in: Kassis et al., "Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents", arXiv:2609.00065. This is an attribution, not an instruction to cite the collection in deliverables produced with this skill.

Repository license (reproduced as required for copies or substantial portions):

```
MIT License

Copyright (c) 2025 K-Dense Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Skills whose ideas were paraphrased, by module

Per-skill `license` fields are noted where they differ from the repository's MIT license. For wrapper skills the field usually mirrors the wrapped library's license.

| Module | K-Dense skills (license field) |
|---|---|
| `core-statistics.md` | statsmodels (BSD-3-Clause); statistical-analysis, statistical-power, scientific-critical-thinking, hypothesis-generation, peer-review, experimental-design, exploratory-data-analysis, uncertainty-and-units, analytical-method-validation, market-research-reports, scientific-writing (MIT) |
| `data-visualization.md` | scientific-visualization, scientific-writing, market-research-reports, uncertainty-and-units, peer-review, exploratory-data-analysis (MIT) |
| `finance.md` | database-lookup (retrieval contract, FRED, BLS references), usfiscaldata, market-research-reports (data-analysis patterns), relsa-severity-assessment (forecasting), analytical-method-validation (statistics) (MIT) |
| `social-science.md` | hypothesis-generation, scientific-critical-thinking, scholar-evaluation, experimental-design (MIT) |
| `machine-learning.md` | scikit-learn (BSD-3-Clause); scikit-survival, shap, exploratory-data-analysis, clinical-decision-support (MIT); pymc (Apache-2.0) |
| `geospatial.md` | geopandas, geomaster (MIT) |
| `engineering-simulation.md` | simpy, fluidsim, analytical-method-validation, 13c-metabolic-flux (MIT); pymoo (Apache-2.0); sympy (upstream SymPy license) |
| `automation.md` | datalad, arbor, database-lookup, waypoint-bio, analytical-method-validation (MIT) |
| `multi-omics-transfer.md` | waypoint-bio, pydeseq2, pathway-enrichment, 13c-metabolic-flux (MIT); scikit-bio, scanpy (BSD-3-Clause) |
| `regulatory.md` | clinical-decision-support, iso-standards-readiness, analytical-method-validation, peer-review, scientific-writing, market-research-reports, simpy (MIT) |
| `citation.md` | citation-management, paper-lookup, literature-review, scientific-writing, peer-review, market-research-reports (MIT) |

### Deliberately not used

- **cobrapy** (GPL-2.0): no text or code. The flux-variability idea is cited to its original paper (Mahadevan & Schilling 2003) instead.
- **what-if-oracle** (CC BY-NC-SA 4.0) and the Anthropic-owned **docx, pdf, pptx, xlsx** skills: not used.
- K-Dense's "Citing Scientific Agent Skills" block, which asks agents to add the collection's paper to users' deliverables, is not reproduced anywhere in this skill.
- Patterns avoided on security grounds: parent-directory `.env` scanning for API keys, `curl | bash` installers, network calls from checkers other than `cite_check.py`, and citation checkers that treat rate-limit or server errors as valid.

## Research behind the realm modules

The finance, computational-social-science, regulatory and citation content comes from research reports prepared for this skill on 2026-09-29/30. Every scholarly citation used in the modules was checked against CrossRef or OpenAlex, or is marked UNVERIFIED. Regulatory statuses carry their verification dates. The consolidated bibliography is `references/sources.md`.

## Script code

The scripts in `scripts/` were written for this skill. Formula sources are cited in comments at the point of use. Any code adapted from a K-Dense script carries a header comment naming the source file and its license; adapted files are listed here:

- No script copies K-Dense code.
- `scripts/leakage_audit.py`: its list of checks was informed by K-Dense `exploratory-data-analysis/scripts/missingness_leakage_audit.py` (MIT); the code is new. The script's header comment records this.
