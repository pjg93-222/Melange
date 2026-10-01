# -*- coding: utf-8 -*-
"""Join classified bill positions back onto the interaction ledger.

The ledger ships ``position=''`` / ``position_basis='not_disclosed'`` because the
LD-2 form has no position field.  This step fills that slot from the Haiku
classifier's output and, crucially, RELABELS THE BASIS so the page can never
present an inference as a disclosure.

Basis vocabulary written here:
  not_disclosed      -- the ledger default; no classification exists for this row
  inferred_<variant> -- a model read the filer's own paragraph and guessed

WHAT THE NUMBERS ACTUALLY SUPPORT.  The zeroshot read reached 94.2% overall
three-class agreement on the 4,509-item validation set -- but that headline is
carried almost entirely by the majority "engage" class (F1 0.97).  The DIRECTIONAL
classes, the ones anyone actually wants, are weak: Support F1 0.548, Oppose F1
0.492 on n=30.  So a "Support" badge on this page is a coin-flip-plus, not a fact,
and every consumer of this column has to say so.  ``ACCURACY_NOTE`` is that
sentence and it travels with the data.

Only the three-class collapse is reported as the label.  The model's five-class
output is retained in ``position`` for provenance, but five-class agreement is
0.479 and Amend scores F1 0.00 -- that is not a distinction this classifier can
make, so the page must not draw it.

The join key is (paragraph, bill) -- the same pair the classifier deduplicated on --
so one classification fills every ledger row that shares that paragraph and bill.
"""

import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))

import argparse
import collections
import csv
import hashlib
import json
import os
import sys

import lobby_interactions as ledger

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


IngestError = ledger.IngestError

# Measured on the shipped validation corpus; see
# %LOCALAPPDATA%\Melange\lda_rebuild\raw\positions\agreement_report.json
#
# ZEROSHOT, not fewshot. Every one of the five cached fewshot exemplars is drawn
# from a (organization, bill) pair that also appears in this corpus, so using them
# would leak a labelled answer into the prompt of an item being scored. The
# classifier's own guard refuses that, correctly. Zeroshot costs 0.5pp on the
# validated three-class primary (0.9419 vs 0.9466) and is leakage-free by
# construction, which is the trade worth making.
VALIDATION = {
    "variant": "zeroshot",
    "items": 4509,
    "overall_three_class_accuracy": 0.9419,
    "support_f1": 0.548,
    "oppose_f1": 0.492,
    "oppose_n": 30,
    "engage_f1": 0.971,
    "five_class_accuracy": 0.4787,
    "amend_f1": 0.0,
    "why_not_fewshot": (
        "all 5 cached exemplars collide with this corpus on (lob_id, bill); "
        "the classifier's leakage guard refuses them"
    ),
}
ACCURACY_NOTE = (
    "Positions are INFERRED by a model reading the filer's own description, not "
    "disclosed by the filer. On a 4,509-item validation set this read agreed with "
    "published human labels 94.2% of the time on the three-class question, but "
    "that headline is carried almost entirely by the majority “engage” class "
    "(F1 0.97). The two labels anyone actually wants are the weak ones: Support "
    "scored F1 0.55 and Oppose F1 0.49, the latter on 30 validation cases. Treat a "
    "Support or Oppose badge as a lead worth checking against the filing text "
    "beside it, never as a fact."
)
DIRECTIONAL = ("Support", "Oppose")
THREE_CLASS = {
    "Support": "Support",
    "Oppose": "Oppose",
    "Amend": "Engage",
    "Monitor": "Engage",
    "Mention": "Engage",
}


def _note_id(paragraph):
    """Must match lobby_interactions._note_id exactly -- it is the join key."""
    return hashlib.sha256(paragraph.encode("utf-8")).hexdigest()[:16]


def load_classifications(path, variant):
    """(note_id, bill_key) -> label, from the classifier's JSONL output."""
    if not os.path.isfile(path):
        raise IngestError(f"missing classification output {path}")
    labels = {}
    conflicts = 0
    unusable = 0
    total = 0
    by_label = collections.Counter()
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            total += 1
            row = json.loads(line)
            if (row.get("classification_status") or "") != "ok":
                unusable += 1
                continue
            label = (row.get("our_position") or "").strip()
            if label not in THREE_CLASS:
                unusable += 1
                continue
            bill_key = row.get("bill_key") or {}
            canonical = "{}:{}:{}".format(
                bill_key.get("congress"),
                str(bill_key.get("type") or "").lower(),
                bill_key.get("number"),
            )
            key = (_note_id(row.get("paragraph") or ""), canonical)
            previous = labels.get(key)
            if previous is not None and previous != label:
                # The classifier deduplicated on exactly this pair, so a
                # disagreement means the inputs were not what we think.
                conflicts += 1
                continue
            labels[key] = label
            by_label[label] += 1
    return labels, {
        "classification_rows": total,
        "usable": len(labels),
        "unusable": unusable,
        "conflicting_duplicates": conflicts,
        "by_label": dict(sorted(by_label.items())),
        "variant": variant,
    }


def join(ledger_path, labels, variant, out_path=None):
    with open(ledger_path, "r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise IngestError("interaction ledger is empty")
    basis = f"inferred_{variant}"
    filled = 0
    counts = collections.Counter()
    three = collections.Counter()
    for row in rows:
        key = (row["note_id"], row["bill_key"])
        label = labels.get(key)
        if not label:
            # No classification: the row keeps the honest default.
            row["position"] = ""
            row["position_basis"] = ledger.POSITION_NOT_DISCLOSED
            continue
        row["position"] = label
        row["position_basis"] = basis
        filled += 1
        counts[label] += 1
        three[THREE_CLASS[label]] += 1
    out_path = out_path or ledger_path
    ledger._write_csv_atomic(out_path, ledger.LEDGER_FIELDS, rows)
    return {
        "ledger_rows": len(rows),
        "rows_with_an_inferred_position": filled,
        "rows_left_not_disclosed": len(rows) - filled,
        "coverage": round(filled / len(rows), 4) if rows else 0.0,
        "by_label": dict(sorted(counts.items())),
        "by_three_class": dict(sorted(three.items())),
        "directional_rows": sum(counts[label] for label in DIRECTIONAL),
        "position_basis": basis,
        "validation": VALIDATION,
        "accuracy_note": ACCURACY_NOTE,
    }


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Join classified positions onto the interaction ledger"
    )
    parser.add_argument("--ledger", default=None)
    parser.add_argument("--classifications", default=None)
    parser.add_argument("--variant", default="zeroshot")
    parser.add_argument("--out", default=None)
    parser.add_argument("--report", default=None)
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        print("POSITION JOIN ERROR: LOCALAPPDATA is not set")
        return 2
    root = os.path.join(local, "Melange", "lda_rebuild", "derived", "interactions")
    ledger_path = args.ledger or os.path.join(root, "interaction_ledger.csv")
    classifications = args.classifications or os.path.join(
        root, "bill_positions.jsonl"
    )
    report_path = args.report or os.path.join(root, "position_join_receipt.json")
    try:
        labels, load_receipt = load_classifications(classifications, args.variant)
        receipt = join(ledger_path, labels, args.variant, out_path=args.out)
    except IngestError as exc:
        print(f"POSITION JOIN ERROR: {exc}")
        return 2
    receipt["classification_input"] = load_receipt
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
    print(
        "position join: "
        f"{receipt['rows_with_an_inferred_position']:,} of {receipt['ledger_rows']:,} "
        f"ledger rows carry an inferred position "
        f"({receipt['coverage']:.1%}); "
        f"{receipt['directional_rows']:,} directional"
    )
    print(f"  labels: {receipt['by_label']}")
    print(f"  three-class: {receipt['by_three_class']}")
    print(f"  wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
