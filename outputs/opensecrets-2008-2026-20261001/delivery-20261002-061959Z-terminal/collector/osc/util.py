"""Shared helpers: time, atomic writes with bounded Windows retry, money parsing, URL canonicalisation."""
from __future__ import annotations
import csv, hashlib, io, json, os, re, time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

BASE = 'https://www.opensecrets.org'
# Windows sharing/access errors: 5 access denied, 32 sharing violation, 33 lock violation.
TRANSIENT_WINERRORS = {5, 32, 33}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_with_retry(src, dst, attempts=8, base_delay=0.2, max_delay=2.0, sleep=time.sleep, replace=os.replace):
    """Atomic os.replace, retried a bounded number of times only for transient Windows
    sharing/access failures. Other errors, and the final failure, propagate unchanged."""
    for attempt in range(1, attempts + 1):
        try:
            return replace(src, dst)
        except PermissionError as exc:
            if getattr(exc, 'winerror', None) not in TRANSIENT_WINERRORS or attempt == attempts:
                raise
            sleep(min(max_delay, base_delay * 2 ** (attempt - 1)))


def atomic_write_bytes(path, data: bytes, **retry):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp')
    with open(tmp, 'wb') as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    replace_with_retry(tmp, path, **retry)


def atomic_write_json(path, obj, **retry):
    atomic_write_bytes(path, json.dumps(obj, indent=2, ensure_ascii=False, default=str).encode('utf-8'), **retry)


def atomic_write_csv(path, fieldnames, rows, **retry):
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='raise', lineterminator='\n')
    writer.writeheader()
    for r in rows:
        writer.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in fieldnames})
    # utf-8-sig so Excel reads it correctly; missing values stay blank (never zero)
    atomic_write_bytes(path, buf.getvalue().encode('utf-8-sig'), **retry)


_BLANK = {'', 'n/a', 'na', '-', '—', '–', 'null', 'none'}


def money(value):
    """Parse a published dollar string to int (float only if cents are present).
    Blank / N/A / dash -> None (NEVER 0). Signed nets: -$5, $-5, ($5), U+2212 minus."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError('bool is not money')
    if isinstance(value, (int, float)):
        return int(value) if float(value) == int(value) else float(value)
    s = str(value).strip().replace('−', '-')
    if s.lower() in _BLANK:
        return None
    neg = False
    if s.startswith('(') and s.endswith(')'):
        neg, s = True, s[1:-1]
    s = s.replace('$', '').replace(',', '').replace(' ', '')
    if s.startswith('-'):
        neg, s = True, s[1:]
    if s.startswith('+'):
        s = s[1:]
    if not re.fullmatch(r'\d+(?:\.\d+)?', s):
        raise ValueError(f'Invalid numeric value: {value!r}')
    try:
        n = Decimal(s)
    except InvalidOperation as exc:  # pragma: no cover
        raise ValueError(f'Invalid numeric value: {value!r}') from exc
    n = -n if neg else n
    return int(n) if n == n.to_integral_value() else float(n)


def pct(value):
    """44.27% -> 44.27 (float); blank -> None."""
    if value is None:
        return None
    t = str(value).strip().replace("%", "")
    return None if t.lower() in _BLANK else float(t.replace(",", ""))


def count(value):
    """Parse an integer count ('2,795', 15); blank -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip().replace(',', '')
    if s.lower() in _BLANK:
        return None
    if not re.fullmatch(r'-?\d+', s):
        raise ValueError(f'Invalid count: {value!r}')
    return int(s)


def canonical_url(url: str) -> str:
    """Absolute, fragment-free, query-sorted: identical logical URLs share one cache entry."""
    url = urljoin(BASE + '/', url.strip())
    sp = urlsplit(url)
    q = urlencode(sorted(parse_qsl(sp.query, keep_blank_values=True)))
    return urlunsplit((sp.scheme.lower(), sp.netloc.lower(), sp.path, q, ''))


def url_key(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode('utf-8')).hexdigest()


def normalized(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (name or '').casefold()).strip()
