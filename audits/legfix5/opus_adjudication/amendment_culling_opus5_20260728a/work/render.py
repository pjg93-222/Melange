#!/usr/bin/env python3
"""Render review cards as compact text for reading. Display only; decides nothing."""
from __future__ import annotations
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent


def render(pool: str, lo: int = 0, hi: int = 10_000, w_guard: int = 240,
           w_head: int = 420, show_head: bool = True) -> None:
    cards = json.loads((HERE / "cards" / f"{pool}.json").read_text(encoding="utf-8"))
    for i, c in enumerate(cards):
        if not (lo <= i < hi):
            continue
        print(f"--- [{i}] {c['k']}  {c['type']}  amends {c.get('amends','')}  "
              f"len={c['textlen']}  tier={c.get('tier')}")
        if c.get("purpose"):
            print(f"    PURPOSE: {c['purpose'][:300]}")
        for cid, terms in (c.get("guard_text") or {}).items():
            print(f"    GUARD {cid}:")
            for t in terms:
                print(f"      * {t['t']} [{t['op']}{'/spec' if t['spec'] else ''}] :: {t['w'][:w_guard]}")
        if c.get("guard_remarks"):
            print(f"    GUARD(remarks-only) {c['guard_remarks']}")
        for p in (c.get("press") or []):
            print(f"    PRESS[{p['label']}] {p['title']}")
        if c.get("sidecar"):
            print(f"    SIDECAR {c['sidecar']}")
        for fam, wins in (c.get("strict") or {}).items():
            print(f"    STRICT {fam}: {wins[0][:200] if wins else ''}")
        for aw in (c.get("anchor_windows") or []):
            print(f"    ANCHOR :: {aw[:260]}")
        if show_head and c.get("head"):
            print(f"    TEXT: {c['head'][:w_head]}")
        if c.get("remarks"):
            print(f"    REMARKS: {c['remarks'][:300]}")
        if c.get("action"):
            print(f"    ACTION: {c['action'][:110]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    render(a[0], int(a[1]) if len(a) > 1 else 0, int(a[2]) if len(a) > 2 else 10_000,
           w_guard=int(a[3]) if len(a) > 3 else 240,
           w_head=int(a[4]) if len(a) > 4 else 420,
           show_head=(a[5] != "0") if len(a) > 5 else True)
