"""Deterministic, disjoint UUID assignment for up to eight crawl workers."""

from __future__ import annotations

import hashlib


def shard_for_uuid(profile_uuid: str, workers: int) -> int:
    """Return a zero-based shard using SHA-256 of the normalized UUID text.

    Worker count must stay fixed for a crawl generation: changing it changes
    assignments. This function performs no I/O and uses no process-local hash.
    """
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 8:
        raise ValueError("workers must be an integer between 1 and 8")
    if not isinstance(profile_uuid, str) or not profile_uuid.strip():
        raise ValueError("profile_uuid must be a nonblank string")
    normalized = profile_uuid.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    return int.from_bytes(digest, "big") % workers
