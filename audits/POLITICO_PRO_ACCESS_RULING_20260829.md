# Politico Pro staff-directory access ruling — 2026-08-29

**Decision:** `PROHIBITED` for automated extraction; `QUARANTINED` and disabled as a staffer-network source.

## Observed authenticated surface

- The user completed login personally in the Codex in-app browser.
- The authenticated staffer directory reported 18,618 results at the time of review.
- Directory/profile links use stable-looking UUID path segments, and the visible product surface contains employment/profile fields that could support later schema validation.
- The surface also displays contact PII. No contact values or profile records were copied, saved, normalized, or published during this review.

## Controlling access finding

The current [POLITICO Terms of Service](https://www.politico.com/terms-of-service), reviewed in the authenticated browser on 2026-08-29, prohibit using automated programs, electronic agents, bots, or automatic processes to access, monitor, or copy the services. The terms also restrict scraping and account transfer. An authenticated seat therefore does not by itself authorize an automated directory crawl.

The prior attended-access proposal is superseded wherever it contemplated agent-driven page traversal or extraction. The signed-in tab may be used by the account holder for ordinary manual viewing; it is not an ingestion channel for this implementation.

## A-0 disposition

| Field | Ruling |
|---|---|
| Source | Politico Pro staffer directory |
| Scope evaluated | Automated directory/profile extraction for the staffer-network corpus |
| Authorization | `PROHIBITED` under currently reviewed terms |
| Enabled | No |
| Approved access mode | Manual attended viewing only; no agent traversal or copying |
| Retention | No Politico profile data acquired; none retained |
| Redistribution | No Politico-derived records or fields authorized |
| Directory census | 18,618 displayed results; descriptive observation only, not an ingested denominator |

## Conditions that can unlock ingestion

Politico can move from `PROHIBITED` to a separately reviewed state only if one of these is obtained and recorded:

1. a Politico-provided export or API whose contract permits the intended internal research use; or
2. written Politico authorization specifically permitting automated directory/profile extraction, retention, and the intended derived outputs for this account.

Any future authorization must receive a new terms vintage, authority scope, retention/redistribution ruling, source manifest, conservation receipt, and PII controls. Login alone is insufficient.

## Execution receipt

- Authentication verified: yes, user-entered credentials only.
- Automated bulk extraction performed: no.
- Profile/contact records persisted: zero.
- Browser state: the authenticated Politico tab was left open for the user.
- Staffer-network effect: source disabled; no canonical facts or graph edges may cite Politico support.
