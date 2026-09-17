"""Obvious outliers and clear refunds from one saved cross-reference run.

The published report workbook is the accounting of record. This module never
restates it: it reads a completed run's decisions and lists only the rows a
reader would want to look at by eye - refunds the engine linked to an original
gift, negative adjustments it could not link, money an accepted baseline had
counted as giving that the engine reclassified as non-giving, and unusually
large counted receipts. Every amount here describes the listed rows, never a
total of giving.

``build_digest`` is pure. It consumes ``links`` first, then ``decisions``, then
``changes``, so a caller may hand it cursors instead of lists; it retains only
the rows it can list. ``entities``, ``source_urls`` and ``descriptions`` are
looked up with ``.get`` for a bounded set of record ids, so a caller may back
them with a lazy reader rather than a dictionary of every source row.

The two size thresholds are a proposed default and await the owner's
ratification; they are stated in the digest so no reader has to guess them.

CLI: ``python cross_reference_digest.py <run_dir> [--large-cents N]
[--large-individual-cents N]`` opens ``<run_dir>/ledger.sqlite`` read-only and
writes ``<run_dir>/digest.json``. It modifies nothing else.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import closing
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time

from report_source_guard import atomic

SCHEMA_VERSION = 1
LARGE_CENTS = 100_000_000
LARGE_INDIVIDUAL_CENTS = 10_000_000
ROW_LIMIT = 200
NON_GIVING_PREFIX = "non_giving_receipt_role:"
# The engine files ``signed_adjustment_not_linked_refund`` in its review queue
# and writes ``negative_amount_is_not_refund_proof`` on the decision itself
# (cross_reference_engine.py:522-523). Accept either name so this digest keeps
# following the engine whichever one reaches the decision row.
UNLINKED_REFUND_REASONS = ("signed_adjustment_not_linked_refund",
                           "negative_amount_is_not_refund_proof")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _threshold(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive whole number of cents")
    return value


def _cents(value) -> int:
    return int(value or 0)


def _dollars(cents: int) -> float:
    return round(cents / 100, 2)


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _text(value, limit: int = 300) -> str:
    return str(value or "")[:limit]


def _identifier(value) -> str:
    return str(value or "")[:120]


def _reasons(decision: Mapping) -> tuple:
    reasons = decision.get("reasons") or ()
    return tuple(reasons) if isinstance(reasons, (list, tuple)) else ()


def basis_text(large_cents: int, large_individual_cents: int) -> str:
    """One sentence a reader can check the listed rows against."""
    return (f"A receipt is listed as large at {_money(large_cents)} or more, or at "
            f"{_money(large_individual_cents)} or more when an individual sent it; both thresholds are a "
            "proposed default and await the owner's ratification.")


def build_digest(decisions: Iterable[Mapping], links: Iterable[Mapping], changes: Iterable[Mapping], *,
                 run_id: str = "", generated_at: str = "", entities: Mapping | None = None,
                 source_urls: Mapping | None = None, descriptions: Mapping | None = None,
                 large_cents: int = LARGE_CENTS,
                 large_individual_cents: int = LARGE_INDIVIDUAL_CENTS) -> dict:
    """Return the dwarfed view of one run: clear refunds and obvious outliers.

    ``decisions`` are the engine's per-row decisions, ``links`` its supported
    links and ``changes`` the runner's presentation change rows. ``entities``
    maps a record id to its FEC ``entity_type``, ``source_urls`` to its public
    filing URL and ``descriptions`` to its receipt text; all three are optional
    fallbacks, and an absent entity type leaves a row subject to the general
    threshold only.
    """
    large_cents = _threshold(large_cents, "large_cents")
    large_individual_cents = _threshold(large_individual_cents, "large_individual_cents")
    entities = {} if entities is None else entities
    source_urls = {} if source_urls is None else source_urls
    descriptions = {} if descriptions is None else descriptions

    refund_links = []
    paired = set()
    for link in links:
        if link.get("kind") != "refund":
            continue
        refund, original = _identifier(link.get("source_id")), _identifier(link.get("counterpart_id"))
        if not refund or not original:
            continue
        refund_links.append((refund, original, _cents(link.get("amount_cents"))))
        paired.update((refund, original))

    kept: dict[str, dict] = {}
    unlinked, non_giving, large = [], [], []
    source_records = 0
    for decision in decisions:
        source_records += 1
        record = _identifier(decision.get("source_id"))
        if not record:
            continue
        reasons = _reasons(decision)
        amount, baseline = _cents(decision.get("amount_cents")), _cents(decision.get("baseline_cents"))
        counted = _cents(decision.get("counted_cents"))
        listed, entity = record in paired, ""
        if any(reason in UNLINKED_REFUND_REASONS for reason in reasons):
            unlinked.append(record)
            listed = True
        if baseline > 0 and any(str(reason).startswith(NON_GIVING_PREFIX) for reason in reasons):
            non_giving.append(record)
            listed = True
        # An entity type is only consulted where it can change the answer, so a
        # lazy reader is asked about large receipts and nothing else.
        if counted > 0 and abs(amount) >= min(large_cents, large_individual_cents):
            entity = _text(entities.get(record), 40).strip().upper()
            if abs(amount) >= large_cents or (entity == "IND" and abs(amount) >= large_individual_cents):
                large.append(record)
                listed = True
        if listed:
            kept[record] = {"company": _text(decision.get("company"), 200), "cycle": decision.get("cycle"),
                            "amount_cents": amount, "baseline_cents": baseline, "counted_cents": counted,
                            "receipt_role": _text(decision.get("receipt_role"), 80), "entity_type": entity}

    wanted = set(unlinked) | set(non_giving)
    context: dict[str, dict] = {}
    for change in changes:
        record = _identifier(change.get("record_id") or change.get("source_id"))
        if record in wanted and record not in context:
            context[record] = {"description": _text(change.get("source_description")),
                               "source_url": _text(change.get("source_url"), 2000)}

    def url(record: str) -> str:
        found = context.get(record, {}).get("source_url") or source_urls.get(record) or ""
        return _text(found, 2000)

    def description(record: str) -> str:
        found = context.get(record, {}).get("description") or descriptions.get(record) or ""
        return _text(found)

    def row(record: str) -> dict:
        return kept.get(record, {})

    def ranked(records, amount_of):
        return sorted(records, key=lambda record: (-abs(amount_of(record)), record))

    refund_rows = ranked(refund_links, lambda link: link[2] or _cents(row(link[0]).get("amount_cents")))
    linked = [{"refund_record_id": refund, "original_record_id": original,
               "company": row(refund).get("company", "") or row(original).get("company", ""),
               "cycle": row(refund).get("cycle") if row(refund) else row(original).get("cycle"),
               "refund_amount": _dollars(amount or _cents(row(refund).get("amount_cents"))),
               "original_amount": _dollars(_cents(row(original).get("counted_cents")
                                                  or row(original).get("amount_cents"))),
               "refund_source_url": url(refund), "original_source_url": url(original)}
              for refund, original, amount in refund_rows[:ROW_LIMIT]]

    unlinked_rows = ranked(unlinked, lambda record: _cents(row(record).get("amount_cents")))
    unlinked_listed = [{"record_id": record, "company": row(record).get("company", ""),
                        "cycle": row(record).get("cycle"),
                        "amount": _dollars(_cents(row(record).get("amount_cents"))),
                        "source_url": url(record), "description": description(record)}
                       for record in unlinked_rows[:ROW_LIMIT]]

    non_giving_rows = ranked(non_giving, lambda record: _cents(row(record).get("baseline_cents")))
    non_giving_listed = [{"record_id": record, "company": row(record).get("company", ""),
                          "cycle": row(record).get("cycle"),
                          "amount": _dollars(_cents(row(record).get("baseline_cents"))),
                          "role": row(record).get("receipt_role", ""),
                          "description": description(record), "source_url": url(record)}
                         for record in non_giving_rows[:ROW_LIMIT]]

    large_rows = ranked(large, lambda record: _cents(row(record).get("amount_cents")))
    large_listed = [{"record_id": record, "company": row(record).get("company", ""),
                     "cycle": row(record).get("cycle"),
                     "amount": _dollars(_cents(row(record).get("amount_cents"))),
                     "entity": row(record).get("entity_type", ""),
                     "role": row(record).get("receipt_role", ""), "source_url": url(record)}
                    for record in large_rows[:ROW_LIMIT]]

    def total(records, field):
        return _dollars(sum(_cents(row(record).get(field)) for record in records))

    return {
        "schema_version": SCHEMA_VERSION, "run_id": _identifier(run_id), "generated_at": _text(generated_at, 60),
        "basis": {"large_cents": large_cents, "large_individual_cents": large_individual_cents,
                  "text": basis_text(large_cents, large_individual_cents)},
        "refunds": {
            "linked": linked, "linked_count": len(refund_links),
            "linked_amount": _dollars(sum(amount or _cents(row(refund).get("amount_cents"))
                                          for refund, _, amount in refund_links)),
            "unlinked": unlinked_listed, "unlinked_count": len(unlinked),
            "unlinked_amount": total(unlinked, "amount_cents"),
        },
        "outliers": {
            "non_giving": non_giving_listed, "non_giving_count": len(non_giving),
            "non_giving_amount": total(non_giving, "baseline_cents"),
            "large": large_listed, "large_count": len(large),
            "large_amount": total(large, "amount_cents"),
        },
        "counts": {"source_records": source_records},
    }


class _SourceRows:
    """Source rows read from the ledger one record id at a time, and only when asked.

    The Banking ledger holds 849,399 source records; the digest needs a handful
    of their fields for the few hundred rows it can list, so nothing is read
    until a view asks for a specific id.
    """

    def __init__(self, db: sqlite3.Connection):
        self._db = db
        self._cache: dict[str, dict] = {}

    def read(self, record: str) -> dict:
        if record not in self._cache:
            found = self._db.execute(
                "SELECT payload_json FROM source_records WHERE source_id=? LIMIT 1", (record,)).fetchone()
            try:
                value = json.loads(found[0]) if found else {}
            except ValueError:
                value = {}
            self._cache[record] = value if isinstance(value, dict) else {}
        return self._cache[record]

    def field(self, name: str) -> "_SourceField":
        return _SourceField(self, name)

    def receipt_text(self) -> "_SourceDescription":
        return _SourceDescription(self)


class _SourceField:
    def __init__(self, rows: _SourceRows, name: str):
        self._rows, self._name = rows, name

    def get(self, record, default=None):
        value = self._rows.read(str(record)).get(self._name)
        return default if value in (None, "") else value


class _SourceDescription:
    """The receipt text the report's change table shows, from the source row.

    The ledger stores the engine's change rows, which carry cents and reasons
    but no prose, so a digest built from a saved ledger reads the same two
    fields the runner joins in ``presentation`` (run_cross_reference.py:281).
    """

    def __init__(self, rows: _SourceRows):
        self._rows = rows

    def get(self, record, default=None):
        row = self._rows.read(str(record))
        value = "; ".join(part for part in (str(row.get(field) or "").strip()
                                            for field in ("receipt_type_full", "memo_text")) if part)
        return default if not value else value


def _payloads(db: sqlite3.Connection, table: str):
    for (payload,) in db.execute(f"SELECT payload_json FROM {table}"):
        try:
            yield json.loads(payload)
        except ValueError as error:
            raise ValueError(f"The {table} ledger table holds a row that is not valid JSON") from error


def _run_identity(run_dir: Path) -> str:
    """The run id the saved report claims, or the directory's own name."""
    try:
        report = json.loads((run_dir / "report.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return run_dir.name
    identity = report.get("run_id") if isinstance(report, dict) else None
    return identity if isinstance(identity, str) and identity else run_dir.name


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build digest.json for one saved cross-reference run.")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--large-cents", type=int, default=LARGE_CENTS)
    parser.add_argument("--large-individual-cents", type=int, default=LARGE_INDIVIDUAL_CENTS)
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    ledger = run_dir / "ledger.sqlite"
    if not ledger.is_file():
        parser.error(f"No decision ledger at {ledger}")
    for value, name in ((args.large_cents, "--large-cents"),
                        (args.large_individual_cents, "--large-individual-cents")):
        if value <= 0:
            parser.error(f"{name} must be a positive whole number of cents")
    started = time.monotonic()
    with closing(sqlite3.connect(ledger.as_uri() + "?mode=ro", uri=True)) as db:
        sources = _SourceRows(db)
        digest = build_digest(
            _payloads(db, "decisions"), _payloads(db, "links"), _payloads(db, "changes"),
            run_id=_run_identity(run_dir), generated_at=_now(),
            entities=sources.field("entity_type"), source_urls=sources.field("pdf_url"),
            descriptions=sources.receipt_text(),
            large_cents=args.large_cents, large_individual_cents=args.large_individual_cents)
    atomic(run_dir / "digest.json", digest)
    refunds, outliers = digest["refunds"], digest["outliers"]
    print(json.dumps({"run_id": digest["run_id"], "source_records": digest["counts"]["source_records"],
                      "linked_refunds": refunds["linked_count"], "linked_refund_amount": refunds["linked_amount"],
                      "unlinked_adjustments": refunds["unlinked_count"], "unlinked_amount": refunds["unlinked_amount"],
                      "non_giving": outliers["non_giving_count"], "non_giving_amount": outliers["non_giving_amount"],
                      "large": outliers["large_count"], "large_amount": outliers["large_amount"],
                      "elapsed_seconds": round(time.monotonic() - started, 2)}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
