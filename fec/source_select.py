# -*- coding: utf-8 -*-
"""Deterministic source-file selection for the congress_cosponsor_network_* and
congress_bills_archive_* families (lane SEL).  NEVER uses mtime: file mtimes tie to the second
(and flip when an older file is touched), so the pick must come from the filename or an explicit pin.

Order of authority:
  (a) data/engine/source_pins.json  {pin_key: exact filename}  -- wins when present (fail-closed if the
      pinned file is not among the candidates).  A promotion is an explicit pin edit.
  (b) the timestamp embedded in the filename: YYYYMMDD_HHMMSS (base network, archive, and new
      AUG<YYYYMMDD_HHMMSS>) or the old AUG<YYYYMMDD> form; a missing time sorts as 000000.  Order is
      (date, AUG-over-base, time, full filename), so on the SAME date an AUG beats a base whatever the
      times ('any' mode; the AUG is derived from the base).  Ties break on the full filename, ascending.
      Names with no timestamp sort lowest.

aug mode keeps each caller's old intent:
  'prefer'  AUG-named files if any exist, else the base files   (moneyball_core.select_network_file)
  'exclude' non-AUG only                                        (directed / base-vintage readers)
  'any'     every file, AUG or not                              (press_hcoi, stance_dynamics, ...)
Pin keys: 'congress_cosponsor_network' ('prefer'/'any'), 'congress_cosponsor_network:base' ('exclude'),
'congress_bills_archive'.
"""
import json, os, re

PINS_REL = os.path.join('data', 'engine', 'source_pins.json')
_TS = re.compile(r'(?<!\d)(\d{8})(?:_(\d{6}))?(?!\d)')


def _ts_key(path):
    name = os.path.basename(str(path))
    m = _TS.search(name)
    if not m:
        return ('', 0, '', name)
    # same calendar date: an AUG is derived from a base, so it outranks the base whatever the time
    return (m.group(1), int(_is_aug(path)), m.group(2) or '000000', name)


def _is_aug(path):
    return 'AUG' in os.path.basename(str(path)).upper()


def load_pins(root):
    p = os.path.join(root, PINS_REL)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def select_source(files, pin_key, aug='any', root=None):
    """Pick one path from `files` (same directory).  `root` = repo root holding data/engine/source_pins.json
    (default: the candidates' directory)."""
    files = [str(f) for f in files]
    if aug == 'exclude':
        files = [f for f in files if not _is_aug(f)]
    elif aug == 'prefer':
        files = [f for f in files if _is_aug(f)] or files
    elif aug != 'any':
        raise ValueError('aug must be prefer|exclude|any, got %r' % (aug,))
    if not files:
        raise FileNotFoundError('no candidate files for %s (aug=%s)' % (pin_key, aug))
    pin = load_pins(root or os.path.dirname(files[0])).get(pin_key)
    if pin:
        hit = [f for f in files if os.path.basename(f) == pin]
        if not hit:
            raise FileNotFoundError('source_pins.json pins %s=%s but it is not among the candidates' % (pin_key, pin))
        return hit[0]
    return max(files, key=_ts_key)


def select_network(files, aug='prefer', root=None):
    return select_source(files, 'congress_cosponsor_network:base' if aug == 'exclude' else 'congress_cosponsor_network', aug, root)


def select_archive(files, root=None):
    return select_source(files, 'congress_bills_archive', 'any', root)
