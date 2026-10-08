#!/usr/bin/env python3
"""Rate-safe public-page acquisition for employment/education evidence.

The scraper consumes already-discovered source URLs.  It does not use browser
cookies, authenticated sessions, search-engine result scraping, CAPTCHA
handling, cache rotation, or access-control bypasses.  Eight workers may run
across domains, while each domain has exactly one shared in-flight request and
a monotonic start-time pacer.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import threading
import time
from typing import Any, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests


USER_AGENT = "MelangeResearch/1.0 (rate-limited public professional-history research)"
DATE_RANGE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)?\.?\s*(?:19|20)\d{2}\s*(?:-|–|—|to)\s*"
    r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)?\.?\s*(?:19|20)\d{2}|Present|Current|Now)\b",
    re.IGNORECASE,
)
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
EMPLOYMENT_TERMS = re.compile(
    r"\b(?:experience|employment|career|worked|joined|served|director|chief|"
    r"counsel|assistant|advisor|adviser|manager|president|vice president|"
    r"representative|senator|committee|department|office)\b",
    re.IGNORECASE,
)
EDUCATION_TERMS = re.compile(
    r"\b(?:education|university|college|school|academy|bachelor|master|"
    r"doctor|degree|graduated|class of|J\.?D\.?|M\.?A\.?|M\.?S\.?|B\.?A\.?)\b",
    re.IGNORECASE,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_url(value: str) -> str | None:
    try:
        split = urlsplit(value.strip())
    except ValueError:
        return None
    if split.scheme.lower() not in {"http", "https"} or not split.netloc:
        return None
    host = split.hostname.lower() if split.hostname else ""
    if not host:
        return None
    port = split.port
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((split.scheme.lower(), netloc, split.path or "/", split.query, ""))


def nested_urls(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"source_url", "profile_url", "legistorm_profile_url", "legistorm_salary_url"}:
                if isinstance(item, str):
                    yield item
            elif key in {"source_urls", "linkedin_source_urls"} and isinstance(item, list):
                yield from (url for url in item if isinstance(url, str))
            else:
                yield from nested_urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from nested_urls(item)


def read_ndjson(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            yield value


def discover_seeds(root: Path) -> tuple[list[str], dict[str, list[str]]]:
    provenance: dict[str, set[str]] = defaultdict(set)
    patterns = (
        "legistorm_lda_profile_enrichment_*_slice_*.ndjson",
        "legistorm_lda_profile_fanout_*_slice_*.ndjson",
        "public_lda_profile_fanout_*_slice_*.ndjson",
    )
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            for row in read_ndjson(path):
                for raw in nested_urls(row):
                    url = normalized_url(raw)
                    if url:
                        provenance[url].add(str(path))
    return sorted(provenance), {url: sorted(paths) for url, paths in provenance.items()}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts: list[str] = []
        self.title: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript", "svg"}:
            self.hidden += 1
        if lower == "title":
            self.in_title = True
        if lower in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript", "svg"} and self.hidden:
            self.hidden -= 1
        if lower == "title":
            self.in_title = False
        if lower in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "section"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.hidden:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned + " ")
            if self.in_title:
                self.title.append(cleaned)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def extract_text(content: bytes, content_type: str) -> tuple[str, str | None]:
    if "pdf" in content_type.lower() or content.lstrip().startswith(b"%PDF-"):
        # PDF extraction is performed by the bounded offline repair stage.
        # Never let a pathological PDF block a network worker or fall through
        # to binary decoding that manufactures false evidence hints.
        return "", None
    encoding = "utf-8"
    match = re.search(r"charset=([^;\s]+)", content_type, re.IGNORECASE)
    if match:
        encoding = match.group(1).strip('"\'')
    text = content.decode(encoding, errors="replace")
    if "html" not in content_type.lower() and not text.lstrip().lower().startswith("<!doctype html"):
        return text, None
    parser = VisibleTextParser()
    parser.feed(text)
    title = " ".join(parser.title).strip() or None
    return parser.text(), title


def evidence_hints(text: str) -> dict[str, Any]:
    def usable(line: str) -> bool:
        stripped = " ".join(line.split())
        if not stripped or len(stripped) > 2000:
            return False
        if sum(character == "\ufffd" for character in stripped) > max(1, len(stripped) // 100):
            return False
        printable = sum(character.isprintable() or character.isspace() for character in stripped)
        if printable / len(stripped) < 0.95:
            return False
        return sum(character.isalpha() for character in stripped) >= 3

    lines = [" ".join(line.split()) for line in text.splitlines() if usable(line)]
    employment_lines = [line for line in lines if EMPLOYMENT_TERMS.search(line)][:100]
    education_lines = [line for line in lines if EDUCATION_TERMS.search(line)][:100]
    return {
        "date_ranges": sorted(set(DATE_RANGE.findall(text)))[:100],
        "year_tokens": sorted(set(YEAR.findall(text))),
        "employment_lines": employment_lines,
        "education_lines": education_lines,
    }


@dataclass
class DomainState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_started: float = 0.0


class PublicScraper:
    def __init__(
        self,
        output_root: Path,
        *,
        delay: float,
        timeout: float,
        max_bytes: int,
    ) -> None:
        self.output_root = output_root
        self.delay = delay
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.domain_states: defaultdict[str, DomainState] = defaultdict(DomainState)
        self.robots_lock = threading.Lock()
        self.robots: dict[str, tuple[str, RobotFileParser | None]] = {}
        self.raw_root = output_root / "raw"
        self.text_root = output_root / "text"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.text_root.mkdir(parents=True, exist_ok=True)

    def robots_decision(self, url: str) -> tuple[bool, str]:
        split = urlsplit(url)
        origin = f"{split.scheme}://{split.netloc}"
        host = split.hostname.lower() if split.hostname else ""
        with self.robots_lock:
            cached = self.robots.get(origin)
        if cached:
            status, parser = cached
            return (parser.can_fetch(USER_AGENT, url), status) if parser else (status == "ROBOTS_404", status)

        # Robots acquisition shares the same per-domain lock and monotonic
        # pacer as page acquisition. Recheck after taking the lock so parallel
        # workers cannot issue duplicate robots requests for a new origin.
        state = self.domain_states[host]
        with state.lock:
            with self.robots_lock:
                cached = self.robots.get(origin)
            if cached:
                status, parser = cached
                return (parser.can_fetch(USER_AGENT, url), status) if parser else (status == "ROBOTS_404", status)

            wait = self.delay - (time.monotonic() - state.last_started)
            if wait > 0:
                time.sleep(wait)
            state.last_started = time.monotonic()
            robots_url = urljoin(origin, "/robots.txt")
            try:
                response = requests.get(
                    robots_url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                if response.status_code == 404:
                    status, parser = "ROBOTS_404", None
                elif response.status_code == 200:
                    parser = RobotFileParser()
                    parser.set_url(robots_url)
                    parser.parse(response.text.splitlines())
                    status = "ROBOTS_PARSED"
                else:
                    status, parser = f"ROBOTS_HTTP_{response.status_code}", None
            except requests.RequestException:
                status, parser = "ROBOTS_UNAVAILABLE", None
            with self.robots_lock:
                self.robots[origin] = (status, parser)
        if parser:
            return parser.can_fetch(USER_AGENT, url), status
        return status == "ROBOTS_404", status

    def fetch(self, url: str, provenance: list[str]) -> dict[str, Any]:
        split = urlsplit(url)
        host = split.hostname.lower() if split.hostname else ""
        if host == "linkedin.com" or host.endswith(".linkedin.com"):
            return self.skipped(url, provenance, "AUTHENTICATED_OR_RESTRICTED_LINKEDIN")
        if host in {"google.com", "www.google.com", "bing.com", "www.bing.com"}:
            return self.skipped(url, provenance, "SEARCH_RESULT_PAGE_NOT_SCRAPED")
        if any(token in split.path.lower() for token in ("/login", "/signin", "/auth/")):
            return self.skipped(url, provenance, "AUTH_ENDPOINT_NOT_SCRAPED")
        allowed, robots_status = self.robots_decision(url)
        if not allowed:
            return self.skipped(url, provenance, "ROBOTS_DISALLOWED", robots_status)

        state = self.domain_states[host]
        try:
            with state.lock:
                wait = self.delay - (time.monotonic() - state.last_started)
                if wait > 0:
                    time.sleep(wait)
                state.last_started = time.monotonic()
                response = requests.get(
                    url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain;q=0.9,*/*;q=0.1",
                        "Accept-Language": "en-US,en;q=0.8",
                    },
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=True,
                )
                body = bytearray()
                response_started = time.monotonic()
                for block in response.iter_content(64 * 1024):
                    body.extend(block)
                    if len(body) > self.max_bytes:
                        raise ValueError("response exceeds max-bytes")
                    if time.monotonic() - response_started > self.timeout:
                        raise ValueError("response exceeds wall-clock timeout")
        except (requests.RequestException, ValueError) as exc:
            return {
                "schema_id": "staffer-network-public-page-capture-v1",
                "url": url,
                "status": "FETCH_ERROR",
                "error": type(exc).__name__,
                "captured_at": now(),
                "source_artifacts": provenance,
                "robots_status": robots_status,
            }

        content = bytes(body)
        content_hash = sha256_bytes(content)
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        raw_path = self.raw_root / f"{content_hash}.bin"
        if not raw_path.exists():
            raw_path.write_bytes(content)
        text, title = extract_text(content, content_type)
        text_bytes = text.encode("utf-8")
        text_hash = sha256_bytes(text_bytes)
        text_path = self.text_root / f"{text_hash}.txt"
        if not text_path.exists():
            text_path.write_bytes(text_bytes)
        return {
            "schema_id": "staffer-network-public-page-capture-v1",
            "url": url,
            "final_url": response.url,
            "status": "CAPTURED" if 200 <= response.status_code < 300 else "HTTP_ERROR",
            "http_status": response.status_code,
            "content_type": content_type,
            "bytes": len(content),
            "content_sha256": content_hash,
            "raw_path": str(raw_path),
            "text_bytes": len(text_bytes),
            "text_sha256": text_hash,
            "text_path": str(text_path),
            "title": title,
            "hints": evidence_hints(text),
            "captured_at": now(),
            "source_artifacts": provenance,
            "robots_status": robots_status,
        }

    @staticmethod
    def skipped(
        url: str, provenance: list[str], reason: str, robots_status: str | None = None
    ) -> dict[str, Any]:
        return {
            "schema_id": "staffer-network-public-page-capture-v1",
            "url": url,
            "status": "SKIPPED",
            "skip_reason": reason,
            "captured_at": now(),
            "source_artifacts": provenance,
            "robots_status": robots_status,
        }


def write_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    ordered = sorted(rows, key=lambda row: row["url"])
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in ordered:
                stream.write(canonical_bytes(row))
    return len(ordered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", default="audits/staffer_network/legistorm_fanout")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--per-domain-delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-bytes", type=int, default=10 * 1024 * 1024)
    parser.add_argument("--max-urls", type=int)
    args = parser.parse_args()
    if args.workers < 1 or args.per_domain_delay < 0 or args.timeout <= 0:
        raise SystemExit("invalid worker, delay, or timeout setting")

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    urls, provenance = discover_seeds(input_root)
    if args.max_urls is not None:
        urls = urls[: args.max_urls]
    seed_path = output_root / "public_page_seed_urls.json"
    seed_path.write_bytes(canonical_bytes({
        "schema_id": "staffer-network-public-page-seed-manifest-v1",
        "urls": urls,
        "url_count": len(urls),
        "input_root": str(input_root),
    }))

    scraper = PublicScraper(
        output_root,
        delay=args.per_domain_delay,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(scraper.fetch, url, provenance[url]): url for url in urls
        }
        for future in as_completed(futures):
            records.append(future.result())

    records_path = output_root / "public_page_captures.ndjson.gz"
    write_gzip(records_path, records)
    counts = Counter(row["status"] for row in records)
    skip_counts = Counter(
        row.get("skip_reason") for row in records if row["status"] == "SKIPPED"
    )
    receipt = {
        "schema_id": "staffer-network-public-page-capture-receipt-v1",
        "status": "PASS",
        "generated_at": now(),
        "workers": args.workers,
        "per_domain_delay_seconds": args.per_domain_delay,
        "one_inflight_request_per_domain": True,
        "robots_enforced": True,
        "authenticated_sessions_used": 0,
        "browser_cookies_used": 0,
        "captcha_bypasses": 0,
        "cache_rotations": 0,
        "seed_urls": len(urls),
        "status_counts": dict(sorted(counts.items())),
        "skip_counts": dict(sorted((str(key), value) for key, value in skip_counts.items())),
        "files": [
            {
                "role": "seed_manifest",
                "path": seed_path.name,
                "bytes": seed_path.stat().st_size,
                "sha256": sha256_file(seed_path),
            },
            {
                "role": "captures",
                "path": records_path.name,
                "bytes": records_path.stat().st_size,
                "sha256": sha256_file(records_path),
            },
        ],
    }
    receipt_path = output_root / "public_page_capture_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
