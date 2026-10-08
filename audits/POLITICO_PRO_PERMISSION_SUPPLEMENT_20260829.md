# Politico Pro extraction-permission supplement — 2026-08-29

## Evidence supplied by the user

Paul attests that he possesses a physical letter from the Politico team granting full permission for data extraction from the website, subject to respecting the site's rate limits. The letter cannot be attached electronically in this workspace. This supplement records the user's first-party attestation; it does not claim independent verification of letterhead, signature, delivery date, or sender authority.

The permission is interpreted narrowly for this project:

- authenticated, rate-limited collection of Politico Pro Congressional Directory records for the Melange staffer-network evidence corpus;
- no password, session token, or account credential extraction;
- no forwarding, resale, or republication of Politico content;
- no retention of email addresses, phone numbers, street addresses, or other direct-contact fields;
- names and source UUIDs remain restricted/local until a separate public-output ruling;
- only public-safe aggregates, opaque identifiers, support digests, and contractually permitted derived fields may leave restricted storage.

## Operational conduct ruling

The signed-in Resource Center and FAQ did not publish a numeric request ceiling, and `directory.politicopro.com/robots.txt` returned the product's 404 page. Until Politico supplies a numeric ceiling, the crawler contract is:

- adaptive concurrency: begin at 2 and permit at most 4 in-flight directory requests;
- maximum aggregate request rate: 60 directory page requests per minute;
- ramp rule: increase only while authentication, latency, and response outcomes remain stable; reduce concurrency immediately on latency or transient-error growth;
- retry: exponential backoff with jitter for transient failures;
- immediate circuit break on HTTP 429, authentication loss, access warning, CAPTCHA, or changed pagination/schema;
- resume only after an attended review of the stop reason;
- every request in the sealed production crawl counted in its local receipt; exploratory pagination attempts are dispositioned separately below.

This bounded fast envelope reflects the user's attestation that Politico preferred prompt extraction. It is an implementation choice, not a claim that Politico published a numeric limit.

## Exploratory-attempt disposition

The unfiltered directory exposes 18,618 results but returned the normal product "no results" state at offset 10,000. The first exploratory browser batch reached offsets through 4,700 before a browser-control timeout and was not published. A second checkpointed unpartitioned attempt conserved 10,000 contact-free rows and 100 request-log entries before the offset-10,000 circuit break. That stopped checkpoint is isolated at `%LOCALAPPDATA%\Melange\staffer_network\quarantine\politico\unpartitioned-stop-20260829T220324-0400`; it is not referenced by the successful snapshot or any canonical metric.

The completed crawl used the directory's visible `Party` filter to form four mutually exclusive partitions whose counts sum exactly to 18,618. I-13 and the sealed crawl receipt are scoped to all 188 requests in that completed production run. They do not claim an exact all-session request census for the earlier exploratory discovery work. The production request log independently reconstructs maximum concurrency of four and a maximum rolling-minute count of 28.

## A-0/A-1 disposition

- Written extraction authority: **AUTHORIZED BY USER-ATTESTED PHYSICAL LETTER**.
- Restricted acquisition disposition: **ACCEPTED AND SEALED**; the rate/concurrency receipt, PII exclusion, exact UUID/outcome conservation, and immutable restricted source manifest pass for this snapshot.
- Canonical source enablement: **NOT YET ENABLED**; normalization, identity-resolution pilots, P-1, and redistribution-safe publication contracts remain incomplete.
- Redistribution: **RESTRICTED LOCAL / PUBLIC-SAFE DERIVED ONLY**.
- Previous Terms-only ruling: retained unchanged as historical evidence and superseded for extraction authority only by this supplement.

## Post-crawl adjudication

1. **PASS:** the attended production run stayed within the provisional envelope: 188/188 successful requests, maximum four in flight, and maximum 28 in any rolling minute.
2. **PASS:** 18,618/18,618 directory rows and UUIDs reconcile exactly across the four party partitions; duplicate UUID occurrences are zero.
3. **PASS:** retained row fields are exactly `issue_areas`, `name`, `partition`, `partition_ordinal`, `profile_uuid`, and `roles`; prohibited contact keys and email/phone-pattern rows are zero.
4. **PASS:** the immutable local request log, partition inventory, row file, source manifest, and public-safe crawl receipt are hash-sealed. A canonical auditor reproduces the committed receipt exactly from those restricted bytes.
5. **OPEN:** keep `enabled=false` until P-1, the source-native normalizer, resolution pilots, and redistribution-safe output contracts pass. Acquisition acceptance is not canonical-publication approval.
