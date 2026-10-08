"""Polite, bounded, cache-first HTTP fetcher.

* Ordinary HTTP only: ``requests`` or subprocess ``curl`` with the truthful agent User-Agent.
  No cookies, credentials, browser automation, TLS impersonation, proxies or challenge handling.
* One disk-cache entry per canonical URL: ``<key>.body`` holds the exact response bytes
  (sha256 recorded in ``<key>.meta.json``); failures are cached explicitly.
* Duplicate URLs are fetched once. Bounded concurrency, one global min-interval across all workers.
* Rate-limit policy (persisted in ``retry_state.json`` so it survives restarts):
    - explicit ``Retry-After`` (seconds or HTTP-date) is ALWAYS honoured globally: waits up to ``max_retry_after`` are sat out,
      longer ones DEFER (no early retry) - including workers already waiting and fresh Fetcher instances after a restart;
    - HTTP 429 WITHOUT Retry-After: per-family exponential pause, and after ``family_429_limit`` consecutive 429s the family is
      deferred for ``family_cooldown`` seconds so other families keep progressing; nothing deferred is ever recorded as observed
      or as permanently unavailable.
* Accounting: ``transport_calls`` = actual transport invocations (one curl / one requests.get); redirect hops are counted
  separately (``redirect_hops``), ``http_requests_total`` = calls + hops. URL-level fetches and retries are labelled separately.
"""
from __future__ import annotations
import email.utils, json, random, re, shutil, subprocess, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

from .util import atomic_write_bytes, atomic_write_json, canonical_url, sha256_bytes, url_key, utc_now

USER_AGENT = 'MentatResearchCollector/1.0 (public research data; Python requests)'
DEFINITIVE_FAILURES = {401, 403, 404, 410}
RETRYABLE = {408, 425, 429, 500, 502, 503, 504}
CHALLENGE_TITLE_RE = re.compile(rb'<title[^>]*>\s*(just a moment|attention required|access denied|checking your browser|are you a robot)', re.I)


def is_challenge(body: Optional[bytes]) -> bool:
    """HTTP-200 bot-challenge / access-denied pages are never accepted as source data (bytes are still kept as evidence)."""
    return bool(body) and bool(CHALLENGE_TITLE_RE.search(body[:8000]))


def parse_retry_after(value, now_epoch: Optional[float] = None) -> Optional[float]:
    """Retry-After as delta-seconds or HTTP-date -> seconds to wait (>= 0), else None."""
    if value is None or str(value).strip() == '':
        return None
    v = str(value).strip()
    try:
        return max(0.0, float(v))
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(v)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = now_epoch if now_epoch is not None else datetime.now(timezone.utc).timestamp()
    return max(0.0, dt.timestamp() - now)


def iso_to_epoch(text) -> float:
    try:
        return datetime.fromisoformat(str(text)).timestamp()
    except (TypeError, ValueError):
        return 0.0


class Deferred(Exception):
    """Raised inside the wait loop when the server-requested pause is longer than this run is willing to sit out."""

    def __init__(self, until_epoch: float, scope: str):
        super().__init__(f'deferred until {until_epoch} ({scope})')
        self.until, self.scope = until_epoch, scope


@dataclass
class FetchResult:
    url: str
    key: str
    ok: bool
    status: Optional[int]
    body: Optional[bytes]
    meta: dict
    from_cache: bool = False

    @property
    def text(self) -> str:
        return (self.body or b'').decode('utf-8', errors='replace')

    @property
    def deferred(self) -> bool:
        """Not observed and NOT a final failure: retry after ``resume_after_utc`` (never an observed zero / permanent gap)."""
        return bool(self.meta.get('deferred'))

    @property
    def failure_reason(self) -> str:
        if self.ok:
            return ''
        if self.meta.get('challenge_content'):
            return self.meta.get('error') or 'http200_challenge_content'
        if self.meta.get('error'):
            return str(self.meta['error'])[:80]
        return f'http_{self.status}'


def family_of(url: str) -> str:
    path = re.sub(r'^https?://[^/]+', '', url).split('?')[0]
    parts = [p for p in path.split('/') if p]
    return parts[0] if parts else 'root'


class Fetcher:
    def __init__(self, data_dir, *, refresh=False, retry_failed=False, concurrency=4, min_interval=0.35,
                 transport='auto', user_agent=USER_AGENT, timeout=(15, 60), max_attempts=5,
                 circuit_threshold=3, max_retry_after=300.0, family_429_limit=3, family_cooldown=300.0, family_floor=2.5,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, wall: Callable[[], float] = time.time,
                 request_fn: Optional[Callable] = None, cache_only=False, budget: Optional[int] = None, run_id: Optional[str] = None,
                 stop_after_epoch: Optional[float] = None):
        self.data_dir = Path(data_dir)
        self.cache_dir = self.data_dir / 'cache'
        self.log_path = self.data_dir / 'request_log.jsonl'
        self.state_path = self.data_dir / 'retry_state.json'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.refresh, self.retry_failed, self.concurrency = refresh, retry_failed, max(1, int(concurrency))
        self.min_interval, self.transport, self.ua = float(min_interval), transport, user_agent
        self.timeout, self.max_attempts, self.circuit_threshold = timeout, int(max_attempts), int(circuit_threshold)
        # max_retry_after: longest server-requested wait sat out inline; anything longer defers (globally for explicit Retry-After)
        self.max_retry_after, self._sleep, self._clock, self._wall = max_retry_after, sleep, clock, wall
        self.family_429_limit, self.family_cooldown, self.family_floor = int(family_429_limit), float(family_cooldown), float(family_floor)
        self.cache_only, self.budget, self.stop_after_epoch = cache_only, budget, stop_after_epoch
        self.run_id = run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{threading.get_native_id()}"
        self._request_fn = request_fn  # test seam: fn(url) -> (status, headers, body, final_url); one call == one transport call
        self._locks, self._lock_guard = {}, threading.Lock()
        self._rate_lock, self._next_slot, self._pause_until = threading.Lock(), 0.0, 0.0
        self._log_lock, self._state_lock = threading.Lock(), threading.Lock()
        self._run_results: dict[str, FetchResult] = {}
        self._consec_block: dict[str, int] = {}
        self._family_defer: dict[str, float] = {}     # family -> resume epoch (wall clock)
        self._fam_429: dict[str, int] = {}            # consecutive no-Retry-After 429s per family
        self._fam_pause_until: dict[str, float] = {}  # monotonic
        self._fam_interval: dict[str, float] = {}     # learned per-family min-interval (AIMD); persisted so a restart starts at the learned pace
        self._fam_next: dict[str, float] = {}         # monotonic next slot per family
        self._fam_ok: dict[str, int] = {}
        self._fam_floor: dict[str, float] = {}        # once a family has answered 429 its pace never recovers below this (stops the AIMD sawtooth)
        self._global_resume = 0.0                     # wall-clock epoch of the latest explicit Retry-After
        self._ok_streak = 0
        self.base_interval = self.min_interval
        self._tls = threading.local()
        self.stats = {'transport_calls': 0, 'redirect_hops': 0, 'url_fetches': 0, 'retries': 0, 'http_429': 0, 'bytes_downloaded': 0,
                      'cache_hits': 0, 'duplicate_requests_avoided': 0, 'skipped_circuit_open': 0, 'skipped_deferred': 0, 'skipped_budget': 0,
                      'cache_only_misses': 0, 'challenge_200_rejected': 0, 'deferred_urls': 0, 'transport_by_name': {}, 'status_counts': {}}
        self._stats_lock = threading.Lock()
        self._restore_state()

    # ---- persisted rate-limit state ----------------------------------------------------------------
    def _restore_state(self):
        """A deadline written by an earlier process is enforced by this one: no request is made before it."""
        try:
            d = json.loads(self.state_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        now = self._wall()
        g = float(d.get('global_resume_epoch') or 0)
        if g > now:
            self._global_resume = g
            self._pause_until = self._clock() + (g - now)
        self._family_defer = {k: float(v) for k, v in (d.get('family_resume_epoch') or {}).items() if float(v) > now}
        self._fam_interval = {k: float(v) for k, v in (d.get('family_interval_s') or {}).items() if float(v) > 0}
        self._fam_floor = {k: float(v) for k, v in (d.get('family_floor_s') or {}).items() if float(v) > 0}

    def _save_state(self):
        with self._state_lock:
            now = self._wall()
            fam = {k: v for k, v in self._family_defer.items() if v > now}
            g = self._global_resume if self._global_resume > now else 0
            atomic_write_json(self.state_path, {
                'global_resume_epoch': g,
                'global_resume_utc': datetime.fromtimestamp(g, timezone.utc).isoformat(timespec='seconds') if g else '',
                'family_resume_epoch': fam, 'family_interval_s': dict(self._fam_interval), 'family_floor_s': dict(self._fam_floor),
                'family_resume_utc': {k: datetime.fromtimestamp(v, timezone.utc).isoformat(timespec='seconds') for k, v in fam.items()},
                'updated_utc': utc_now(), 'run_id': self.run_id})

    def active_deferrals(self) -> dict:
        """{'global': epoch|None, 'families': {fam: epoch}} still in the future (for status / resume commands)."""
        now = self._wall()
        return {'global': self._global_resume if self._global_resume > now else None,
                'families': {k: v for k, v in self._family_defer.items() if v > now}}

    # ---- cache -----------------------------------------------------------------------------
    def _paths(self, key):
        d = self.cache_dir / key[:2]
        return d / f'{key}.body', d / f'{key}.meta.json'

    def load_cached(self, url) -> Optional[FetchResult]:
        key = url_key(url)
        body_p, meta_p = self._paths(key)
        if not meta_p.exists():
            return None
        try:
            meta = json.loads(meta_p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None
        body = None
        if body_p.exists():
            body = body_p.read_bytes()
            if sha256_bytes(body) != meta.get('sha256'):
                return None  # corrupt entry -> treated as a miss and refetched
        challenge = meta.get('http_status') == 200 and is_challenge(body)  # re-checked on every cache read
        if challenge:
            meta = {**meta, 'challenge_content': True, 'error': 'http200_challenge_content'}
        ok = meta.get('http_status') == 200 and body is not None and not challenge
        return FetchResult(canonical_url(url), key, ok, meta.get('http_status'), body, meta, from_cache=True)

    def _store(self, key, meta, body: Optional[bytes]):
        body_p, meta_p = self._paths(key)
        if body is not None:
            atomic_write_bytes(body_p, body)
            meta['sha256'], meta['bytes'] = sha256_bytes(body), len(body)
        else:
            meta['sha256'], meta['bytes'] = None, None
            if body_p.exists():
                body_p.unlink()
        atomic_write_json(meta_p, meta)

    def _stat(self, name, n=1):
        with self._stats_lock:
            self.stats[name] += n

    def _count_call(self, transport, status, hops):
        with self._stats_lock:
            self.stats['transport_calls'] += 1
            self.stats['redirect_hops'] += hops
            self.stats['transport_by_name'][transport] = self.stats['transport_by_name'].get(transport, 0) + 1
            k = str(status)
            self.stats['status_counts'][k] = self.stats['status_counts'].get(k, 0) + 1

    @property
    def http_requests_total(self):
        return self.stats['transport_calls'] + self.stats['redirect_hops']

    def _log(self, rec):
        rec = {**rec, 'run_id': self.run_id}
        with self._log_lock:
            with open(self.log_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n')

    # ---- politeness --------------------------------------------------------------------------
    def _wait_slot(self, fam=None):
        """Block until a rate slot is free AND no pause is active; pauses are re-checked after every sleep. A global pause longer
        than ``max_retry_after`` raises Deferred (also for workers that were already waiting when it was set)."""
        while True:
            with self._rate_lock:
                now = self._clock()
                if self._pause_until - now > self.max_retry_after:
                    raise Deferred(self._wall() + (self._pause_until - now), 'global_retry_after')
                fd = self._family_defer.get(fam, 0.0) if fam else 0.0
                if fd > self._wall():   # a family cooldown set by another worker also stops workers already inside their retry loop
                    raise Deferred(fd, 'family_deadline')
                ready = max(self._next_slot, self._pause_until, self._fam_pause_until.get(fam, 0.0) if fam else 0.0, self._fam_next.get(fam, 0.0) if fam else 0.0)
                if now >= ready:
                    self._next_slot = now + self.min_interval
                    if fam and self._fam_interval.get(fam):
                        self._fam_next[fam] = now + self._fam_interval[fam]
                    return
                wait = ready - now
            self._sleep(wait)

    def _pause_all(self, seconds):
        """Explicit server Retry-After: global, persisted, applied even on the final attempt."""
        with self._rate_lock:
            self._pause_until = max(self._pause_until, self._clock() + seconds)
            self._global_resume = max(self._global_resume, self._wall() + seconds)
        self._save_state()

    def _defer_family(self, fam, until_epoch):
        with self._rate_lock:
            self._family_defer[fam] = max(self._family_defer.get(fam, 0), until_epoch)
        self._log({'utc': utc_now(), 'event': 'family_deferred', 'family': fam, 'resume_after_epoch': until_epoch, 'url': ''})
        self._save_state()

    # ---- transports (exactly one transport call per invocation) --------------------------------------
    def _session(self):
        import requests
        s = getattr(self._tls, 'session', None)
        if s is None:
            s = requests.Session()
            s.headers['User-Agent'] = self.ua
            self._tls.session = s
        return s

    def _http_requests(self, url):
        r = self._session().get(url, timeout=self.timeout, allow_redirects=True)
        return r.status_code, dict(r.headers), r.content, r.url, len(r.history)

    def _curl_exe(self):
        return shutil.which('curl.exe') or shutil.which('curl')

    def _http_curl(self, url):
        exe = self._curl_exe()
        if not exe:
            raise RuntimeError('curl not available')
        with tempfile.TemporaryDirectory() as td:
            body_f, hdr_f = Path(td) / 'b', Path(td) / 'h'
            cmd = [exe, '-sS', '-L', '--compressed', '--max-time', str(int(sum(self.timeout))), '-A', self.ua,
                   '-D', str(hdr_f), '-o', str(body_f), '-w', '%{http_code}\n%{num_redirects}\n%{url_effective}', url]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=sum(self.timeout) + 10)
            if p.returncode != 0:
                raise RuntimeError(f'curl exit {p.returncode}: {p.stderr.strip()[:200]}')
            code_s, _, rest = p.stdout.partition('\n')
            hops_s, _, final = rest.partition('\n')
            headers = {}
            for line in hdr_f.read_text(errors='replace').splitlines():  # last redirect hop wins
                k, sep, v = line.partition(':')
                if sep and not line.startswith('HTTP/'):
                    headers[k.strip()] = v.strip()
            return int(code_s), headers, body_f.read_bytes(), final.strip() or url, int(hops_s) if hops_s.strip().isdigit() else 0

    def transport_name(self):
        if self._request_fn:
            return 'injected'
        if self.transport == 'curl' or (self.transport == 'auto' and self._curl_exe()):
            return 'curl'
        return 'requests'

    def _once(self, url):
        """ONE transport call. Observed 2026-10-01: PAC/lobbying pages return 403 to python-requests but 200 to plain curl
        with the same truthful UA, so 'auto' = curl when installed (no requests->curl double request), else requests."""
        if self._request_fn:
            status, headers, body, final = self._request_fn(url)
            return status, headers, body, final, 0, 'injected'
        name = self.transport_name()
        out = self._http_curl(url) if name == 'curl' else self._http_requests(url)
        return (*out, name)

    # ---- core ------------------------------------------------------------------------------
    def _key_lock(self, key):
        with self._lock_guard:
            return self._locks.setdefault(key, threading.Lock())

    def _skip(self, url, key, error, fam, extra=None):
        meta = {'source_url': url, 'http_status': None, 'error': error, 'family': fam, 'retrieved_utc': utc_now(), **(extra or {})}
        return FetchResult(url, key, False, None, None, meta)   # skips are counted in stats, not logged per URL (a deferred crawl would log thousands per pass)

    def _deferred_result(self, url, key, fam, error, until_epoch):
        self._stat('skipped_deferred')
        self._stat('deferred_urls')
        return self._skip(url, key, error, fam, {'deferred': True, 'resume_after_epoch': until_epoch,
                                                 'resume_after_utc': datetime.fromtimestamp(until_epoch, timezone.utc).isoformat(timespec='seconds')})

    def get(self, url, family: Optional[str] = None) -> FetchResult:
        url = canonical_url(url)
        key = url_key(url)
        fam = family or family_of(url)
        with self._key_lock(key):
            if key in self._run_results:
                self._stat('duplicate_requests_avoided')
                return self._run_results[key]
            cached = None if self.refresh else self.load_cached(url)
            if cached is not None:
                transient = cached.status is None or cached.status in RETRYABLE or bool(cached.meta.get('challenge_content'))
                if cached.ok or self.cache_only or (not self.retry_failed and not transient):
                    self._stat('cache_hits')
                    self._run_results[key] = cached
                    return cached
            if self.cache_only:
                self._stat('cache_only_misses')
                res = self._skip(url, key, 'cache_only_miss', fam)
            elif self.stop_after_epoch is not None and self._wall() >= self.stop_after_epoch:   # bounded run: no new request after the wall-clock deadline
                res = self._deferred_result(url, key, fam, 'deferred_run_deadline_reached', self._wall())
            elif self.budget is not None and self.stats['transport_calls'] >= self.budget:
                self._stat('skipped_budget')
                res = self._skip(url, key, 'skipped_request_budget_exhausted', fam)
            elif cached is not None and iso_to_epoch(cached.meta.get('resume_after_utc')) > self._wall():
                # a deadline recorded by an earlier run still stands (a fresh Fetcher / restart must not retry early)
                res = self._deferred_result(url, key, fam, 'deferred_resume_after_not_reached', iso_to_epoch(cached.meta['resume_after_utc']))
            elif self._family_defer.get(fam, 0) > self._wall():
                res = self._deferred_result(url, key, fam, 'deferred_family_retry_after', self._family_defer[fam])
            elif self._consec_block.get(fam, 0) >= self.circuit_threshold:
                self._stat('skipped_circuit_open')
                res = self._skip(url, key, 'skipped_family_circuit_open', fam)
            else:
                res = self._network(url, key, fam)
            if not res.deferred:  # a deferred URL stays retryable within this process once its deadline passes
                self._run_results[key] = res
            return res

    def _network(self, url, key, fam) -> FetchResult:
        self._stat('url_fetches')
        meta = {'source_url': url, 'requested_url': url, 'family': fam, 'user_agent': self.ua}
        status, headers, body, final, hops, tname, error, calls = None, {}, None, url, 0, None, None, 0
        deferred_until, defer_error = None, ''
        for _ in range(self.max_attempts):
            try:
                self._wait_slot(fam)
            except Deferred as d:  # explicit Retry-After longer than this run sits out: stop BEFORE any early retry
                deferred_until = d.until
                defer_error = 'deferred_family_retry_after' if d.scope == 'family_deadline' else 'deferred_retry_after_exceeds_limit'
                break
            calls += 1
            t0 = self._clock()
            try:
                status, headers, body, final, hops, tname = self._once(url)
                error = None
            except Exception as exc:  # noqa: BLE001 - network errors are per-URL data, never fatal
                status, headers, body, hops, error = None, {}, None, 0, f'{type(exc).__name__}: {exc}'[:300]
                tname = tname or self.transport_name()
            self._count_call(tname, status, hops)
            with self._rate_lock:  # adaptive pacing: slow down on 429 (below), recover gradually after sustained 200s
                if status == 200:
                    self._ok_streak += 1
                    if self._ok_streak >= 15 and self.min_interval > self.base_interval:
                        self.min_interval = max(self.base_interval, self.min_interval * 0.75)
                        self._ok_streak = 0
                else:
                    self._ok_streak = 0
            low = {k.lower(): v for k, v in (headers or {}).items()}
            self._log({'utc': utc_now(), 'url': url, 'attempt': calls, 'event': 'transport_call', 'http_status': status, 'redirect_hops': hops,
                       'bytes': len(body or b''), 'elapsed_s': round(self._clock() - t0, 3), 'transport': tname,
                       'retry_after': low.get('retry-after', ''), 'error': error})
            if body:
                self._stat('bytes_downloaded', len(body))
            if status == 429:
                self._stat('http_429')
            wait = parse_retry_after(low.get('retry-after'), self._wall()) if status in (429, 503) else None
            if wait is not None:
                self._pause_all(wait)  # global, exactly what the server asked, applied even to the final attempt
                if wait > self.max_retry_after:
                    deferred_until, defer_error = self._wall() + wait, 'deferred_retry_after_exceeds_limit'
                    self._defer_family(fam, deferred_until)
                    break
            elif status == 429:  # no Retry-After: family-scoped exponential pause, slower global pacing, bounded streak -> family cooldown
                with self._rate_lock:
                    n = self._fam_429[fam] = self._fam_429.get(fam, 0) + 1
                    self._fam_floor[fam] = self.family_floor
                    self._fam_interval[fam] = min(30.0, max(self.family_floor, self._fam_interval.get(fam, 0.0) * 2))   # multiplicative decrease of this family's rate only
                    self._fam_ok[fam] = 0
                    self._fam_pause_until[fam] = self._clock() + min(60.0, 10.0 * 2 ** (n - 1))
                if n >= self.family_429_limit:
                    deferred_until, defer_error = self._wall() + self.family_cooldown, 'deferred_family_429_cooldown'
                    self._defer_family(fam, deferred_until)
                    break
            if status == 200:
                with self._rate_lock:
                    self._fam_429[fam] = 0
                    self._fam_ok[fam] = self._fam_ok.get(fam, 0) + 1
                    if self._fam_interval.get(fam) and self._fam_ok[fam] >= 8:   # additive-style recovery after sustained successes
                        self._fam_interval[fam] = max(self._fam_floor.get(fam, 0.0), self._fam_interval[fam] * 0.8)
                        self._fam_ok[fam] = 0
            if not (status is None or status in RETRYABLE) or calls == self.max_attempts:
                break
            self._stat('retries')
            if wait is None and status != 429:
                self._sleep(min(60.0, 2.0 * 2 ** (calls - 1)) * (0.75 + random.random() * 0.5))
        if calls == 0:  # deferred before any request: nothing observed, the existing cache entry is left untouched
            return self._deferred_result(url, key, fam, defer_error or 'deferred_retry_after_exceeds_limit', deferred_until or self._wall())
        if status in (401, 403):
            self._consec_block[fam] = self._consec_block.get(fam, 0) + 1
        elif status == 200:
            self._consec_block[fam] = 0
        low = {k.lower(): v for k, v in (headers or {}).items()}
        has_body = status == 200 and body is not None
        challenge = bool(has_body and is_challenge(body))
        if challenge:
            self._stat('challenge_200_rejected')
            error = 'http200_challenge_content'
        elif status == 429 and (low.get('cf-mitigated') == 'challenge' or is_challenge(body)):
            challenge, error = True, 'http429_cloudflare_challenge'   # a managed challenge, not a plain rate limit: never solved or bypassed
        meta.update(http_status=status, final_url=final, redirect_hops=hops, retrieved_utc=utc_now(), transport=tname,
                    content_type=low.get('content-type', ''), last_modified=low.get('last-modified', ''),
                    etag=low.get('etag', ''), retry_after=low.get('retry-after', ''), transport_calls=calls, error=error,
                    challenge_content=challenge, run_id=self.run_id)
        if deferred_until:
            meta['resume_after_utc'] = datetime.fromtimestamp(deferred_until, timezone.utc).isoformat(timespec='seconds')
            meta['error'], meta['deferred'] = defer_error, True
            self._stat('deferred_urls')
        self._store(key, meta, body if has_body else None)
        return FetchResult(url, key, bool(has_body and not challenge), status, body if has_body else None, meta)

    def fetch_many(self, urls: Iterable[str], progress: Optional[Callable[[FetchResult], None]] = None):
        urls = list(dict.fromkeys(canonical_url(u) for u in urls))
        results = {}
        if not urls:
            return results
        with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            for res in ex.map(self.get, urls):
                results[res.url] = res
                if progress:
                    progress(res)
        return results
