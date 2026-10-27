"""Bounded concurrent inventory reads using the existing directory ZIP guards.

This changes scheduling only. The source path, private-content, held-file,
identity and resource checks remain in directory_zip.py; no source is modified.
"""
from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import importlib.util
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location("_directory_inventory_guards", Path(__file__).with_name("directory_zip.py"))
guards = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guards)

MAX_WORKERS, MAX_PENDING = 8, 16


def _read_record(file, name):
    # Keep the pre-read leaf check as well as stream_file's before/open/after
    # identity and content checks; perform all file I/O inside the bounded pool.
    guards.physical(file)
    size, digest = guards.stream_file(file)
    return {"path": name, "size": size, "sha256": digest}


def inventory_for(source, app_id, version, workers=8):
    guards.require(type(workers) is int and 1 <= workers <= MAX_WORKERS, "Invalid inventory worker count")
    guards.require(app_id in guards.ENTRYPOINTS and isinstance(version, str) and guards.VERSION.fullmatch(version), "Invalid package identity")
    source = Path(source).absolute()
    guards.parent_chain(source)
    records, omitted, aliases, directories, total = [], [], set(), {}, 0
    pending = set()
    pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="directory-inventory")

    def collect():
        nonlocal total
        completed, _ = wait(pending, return_when=FIRST_COMPLETED)
        pending.difference_update(completed)
        for future in completed:
            record = future.result()
            total += record["size"]
            guards.require(total <= guards.MAX_TOTAL, "Package resource limit exceeded")
            records.append(record)

    try:
        for current, dirs, filenames in os.walk(source, followlinks=False):
            guards.physical(Path(current), directory=True)
            dirs.sort()
            filenames.sort()
            for directory in dirs:
                relative = (Path(current) / directory).relative_to(source).as_posix()
                guards.safe_path(relative)
                guards.physical(Path(current) / directory, directory=True)
                guards.refuse_private(relative + "/placeholder")
            for filename in filenames:
                file = Path(current) / filename
                name = guards.safe_path(file.relative_to(source).as_posix())
                guards.require(name.upper() != guards.INVENTORY.upper(), "Source already contains a directory inventory")
                if guards.excluded(name):
                    guards.physical(file)
                    omitted.append(name)
                    continue
                guards.refuse_private(name)
                key = name.upper()
                guards.require(key not in aliases, "Case-insensitive duplicate file")
                aliases.add(key)
                guards.require(len(aliases) <= guards.MAX_FILES, "Package resource limit exceeded")
                parts = name.split("/")[:-1]
                while parts:
                    parent = "/".join(parts)
                    guards.require(directories.get(parent.upper(), parent) == parent, "Directory case alias")
                    directories[parent.upper()] = parent
                    parts.pop()
                pending.add(pool.submit(_read_record, file, name))
                if len(pending) >= MAX_PENDING:
                    collect()
        while pending:
            collect()
    finally:
        for future in pending:
            future.cancel()
        # Running readers finish their guards before this function can return or
        # raise; queued work is canceled after the first observed failure.
        pool.shutdown(wait=True, cancel_futures=True)

    guards.require(not aliases.intersection(directories), "File and directory collision")
    records.sort(key=lambda item: item["path"])
    names = {item["path"] for item in records}
    guards.require(guards.ENTRYPOINTS[app_id] in names and "resources/app.asar" in names, "Incomplete Electron application tree")
    guards.require(any(name.startswith(f"resources/runtime/{app_id}/") for name in names), "Application runtime is missing")
    return {"schemaVersion": 1, "appId": app_id, "version": version, "entrypoint": guards.ENTRYPOINTS[app_id], "files": records}, omitted
