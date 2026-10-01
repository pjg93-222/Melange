# Four repeated interview turns block the intake gate

The previous collection receipt was rejected for four exact repeated-turn groups.
Read-only verification confirms the same four groups remain. Each contains two
identical rows, including member, date, source, package, word count and text.

| Member | Program date | Keep rowid | Proposed removal | Source |
|---|---|---:|---:|---|
| Charles Schumer | 2019-03-26 | 193060 | 193063 | [CNN](https://transcripts.cnn.com/show/nwsm/date/2019-03-26/segment/01) |
| Chuck Grassley | 2018-09-04 | 190575 | 190576 | [Fox](https://www.foxnews.com/transcript/ingraham-the-party-of-stunts-strikes-again) |
| Kirsten Gillibrand | 2019-01-15 | 189055 | 189056 | [CNN](https://transcripts.cnn.com/show/ebo/date/2019-01-15/segment/01) |
| Tim Scott | 2023-04-16 | 103937 | 103939 | [NBC](https://www.nbcnews.com/meet-the-press/meet-press-april-16-2023-n1304351) |

Source verification confirms the Schumer and Grassley passages appear twice in
their broadcasts. Thus exact repeated text is not, by itself, proof of faulty
collection. The other two source pages were unavailable in this web pass.
The existing collector nevertheless deliberately retains one identical text per
member/package in `fetch_interviews.store`; the intake audit enforces that rule.

The concrete proposed action is to align these eight stored rows with that
existing policy: preserve one row from each pair and remove the four listed
surplus copies. No unique speech text would be lost. The alternative is a separate
owner decision on preserving source repetition and changing ingestion semantics.
The removal changes the stored corpus by four turn occurrences and 65 word
occurrences (11 + 29 + 12 + 13). Preserving unique text does not imply that repeated
broadcast exposure has no analytical value; that is why the policy choice is explicit.

`cleanup_interview_duplicates.py` defaults to read-only verification. Its prepared
`--apply` path creates a complete SQLite backup, verifies all eight exact records
again inside a transaction, removes exactly four rowids, asserts the row-count
delta and writes a receipt. No deletion has been performed.
An isolated full-database rehearsal clears the interview gate while preserving
the live database byte-for-byte. Optimized-runtime tests also verify exact
four-row deletion and refusal of changed evidence; safety checks do not depend
on Python assertions being enabled.

This action remains owner-gated under moneyball-change-control law 15:
"Data deletions from the D2/legacy duplicate ledgers are user-gated" and
"no dedup DELETE without Paul." The blanket regeneration request does not clearly
settle this previously explicit data-deletion decision.
