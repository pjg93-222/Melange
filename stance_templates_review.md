# Stance-template cross-validation — 2026-07-01

## A. T1 — DEBATE label template (cu_stance_label_set.csv, 552 rows, 552 dual-labeled)
pre_label vs human_label: agreement 70.1%, Cohen kappa 0.529  (Zhou-Elejalde reported kappa 0.81-0.94 for a clean template)
confusion (pre -> human): support->support:163, neutral->neutral:148, neutral->support:78, oppose->oppose:76, support->neutral:43, neutral->oppose:30, support->oppose:7, oppose->neutral:4
per-class recall of the template: neutral 76% (n=195), oppose 67% (n=113), support 67% (n=244)

## B. T1 x T4 — overlap articles (n=95): human vs API vs DEBATE
human==API 55% | human==DEBATE 100%
CAVEATS (read before concluding anything): (1) DEBATE is CIRCULAR here — overlap stance_src = {'human_label': 95},
    i.e. where src=human_label, model_stance IS the human label, so 100% is tautological, not skill.
(2) the API pass labeled from TITLE+metadata only; humans labeled full text — the 45% human/API gap
    mixes template disagreement with the title-only handicap.  The CLEAN comparison is T4 itself:
    adjudicate gold_* on the 312 balanced items, then stance_eval.py scores api_cu_alignment and
    model_stance against YOUR gold on equal footing.
disagreement rows to eyeball: 43

## C. T2 x T3 — valence priors vs bill_directions.csv vs DEFENSIVE set
bill_directions.csv coverage: 60 rows, categories: ['CFPB']
CFPB registry: 49 pro-CU (restraint) / 5 anti-CU (expansion) directions — CONSISTENT with the T2 prior (restrain=+1) OK
Interchange: T2 prior = anti-CU target (-1) and DEFENSIVE set contains it: True -> consistent (CU defends the status quo)
Credit Card Mandates: T2 prior = anti-CU target (-1) and DEFENSIVE set contains it: True -> consistent (CU defends the status quo)
NOTE for review: T2 priors are hard-coded in fec/stance/api_prelabel.py SYSTEM (lines ~27-34). The user-owned
registry (T3 + a future press-side valence csv, phase S2) should be the single source; the API prompt
should eventually READ the registry rather than embed it.

## D. S3 NLI hypothesis variants -> stance_template_variants.csv (45 templates, 3 paraphrases/class x 5 targets)

## Where each template lives (for your review pass)
- T1  C:\Users\pgoff\OneDrive\Desktop\Draft Systems\cu_stance_label_set.csv  (pre_label/human_label + text snippets)
- T2  C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\stance\api_prelabel.py  (SYSTEM prompt: factorization + valence priors)
- T3  C:\Users\pgoff\OneDrive\Desktop\Melange Systems\bill_directions.csv  (user-owned legislative valence registry)
- T4  C:\Users\pgoff\OneDrive\Desktop\Melange Systems\gold_label_queue.csv  (312 balanced items; adjudicate gold_*, then: python fec/stance/stance_eval.py api_cu_alignment)
- NEW C:\Users\pgoff\OneDrive\Desktop\Melange Systems\stance_template_variants.csv  (S3 NLI paraphrase set — edit before S3 benchmarking)
