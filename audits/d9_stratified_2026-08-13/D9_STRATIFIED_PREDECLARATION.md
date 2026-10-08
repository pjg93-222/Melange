# D9 STRATIFIED REFIT — PRE-DECLARATION

Written **before** the refit is dispatched. Fixed here so the headline cannot be chosen
after seeing the numbers.

**Status: EXPLORATORY.** D9 consumed no look, has no prereg, fired no bars, and closed
nothing. This is not a "successor" in the bridge sense — there is no closure to succeed.
The prereg discipline binds only at promotion (change-control class 4), which this is not.

---

## 1. What is fit

The same 12 cross-industry models, unchanged in every other respect:

```
align_B ~ exp_B + align_A + exp_B*align_A + senate + log_total_exp     (n=533)
```

using the archived `n2_models.py` `ols()` for comparability with the committed fit.

Three specifications:

- **S0 POOLED** — the archived spec, reproduced as the reference point.
- **S1 STRATIFIED** — S0 fit separately within Democrats and within Republicans.
- **S2 FULLY INTERACTED** — S0 plus `party` and every party × term product, including the
  three-way `party × exp_B × align_A`.

## 2. THE HEADLINE, fixed in advance

**The headline is S1, the party-stratified subsample estimates.**

Reason: the question this refit exists to answer is *where does the association live*, and
a stratified estimate answers it directly and legibly. A three-way interaction coefficient
answers a different question — *is moderation present* — and is harder to read as a
quantity.

**S2's three-way terms are the test of whether stratification is warranted**, reported as
supporting evidence for S1, never as the headline number.

## 3. Multiplicity, fixed in advance

- Holm across the **12 interaction terms within each stratum**, applied separately inside
  the Democrat fit and inside the Republican fit.
- Holm across the **12 three-way terms** as its own family.
- The two families are corrected separately, not pooled: they are different hypotheses
  (where is the effect vs is it moderated), and pooling all 24 would be wrong for the same
  reason the earlier round corrected the two worlds separately.

## 4. DECISION RULE, fixed in advance

**If a pair's three-way term survives Holm, that pair's POOLED coefficient is DEPRECATED
and only its stratified estimates may be quoted.** No exceptions decided after the fact.

If a pair's three-way term does not survive, the pooled coefficient stands and the
stratified estimates are reported as context.

## 5. Handling of Independents

There are 3 Independents in the roster. **They are excluded from stratification** — three
observations cannot support a subsample fit. They are **reported as excluded with their
count**, never silently dropped, and they remain in S0 and S2 where party enters as a
dummy.

Note the roster's Independent cell is itself partly an artifact: it now contains two
Senate independents plus a genuine mid-Congress party switcher, following today's Voteview
fix. That is a further reason not to fit anything on it.

## 6. What this CANNOT establish, stated before the result

- **It cannot make the finding causal.** Exposure and alignment share bill sponsorship as
  a common cause; selection is unmodeled; industries plausibly lobby hardest where they
  are already losing, which produces the same signs.
- **It does not license the screening rule.** That wording was corrected out of the
  document today precisely because an exploratory fit cannot support an operational
  decision procedure.
- **It is one cross-sectional epoch** (2021–2026 pooled), so it says nothing about whether
  exposure precedes alignment.

## 7. Expectation, recorded so it can be wrong

From the replication round: the three "crypto as outcome" pairs (credit_union→crypto,
bank→crypto, fintech→crypto) should show significant three-way moderation and
**opposite-signed** stratified estimates (D positive, R negative). The three crypto
fault-line pairs (crypto→credit_union, crypto→bank, crypto→fintech) should be
**Democrat-driven**, with two of the three not significant within Republicans.

If the stratified fits contradict this, the replication's diagnosis was wrong and that is
the finding.
