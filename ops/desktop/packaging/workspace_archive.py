"""Read-only, streaming containers for fixed compiled analytical member enums.

This parser grants no application/profile authority and extracts no filesystem
paths. Domain factories must additionally validate record and SQLite schemas.
"""
import hashlib
import os
from pathlib import Path
import stat
import struct
import threading
import zipfile
import zlib

from module_application_contracts import DataIntakeBlocked
from module_data_snapshot import parse, regular
from workspace_data_contract import ARCHIVE_MEMBERS, MiB

BLOCK = 64 * 1024
MAX_DIRECTORY = MiB


def require(value):
    if not value:
        raise DataIntakeBlocked('integrity')


def identity(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns


def stamp(info):
    return (*identity(info), info.st_ctime_ns)


def extras(raw):
    found = {}
    while raw:
        require(len(raw) >= 4)
        kind, size = struct.unpack('<HH', raw[:4])
        require(kind == 1 and kind not in found and size <= len(raw) - 4)
        found[kind], raw = raw[4:4 + size], raw[4 + size:]
    return found


class DomainArchive:
    def __init__(self, path, *, app_id, kind, role, expected_sha256, is_cancelled=lambda: False):
        require((app_id, kind, role) in ARCHIVE_MEMBERS and callable(is_cancelled)
                and type(expected_sha256) is str and len(expected_sha256) == 64)
        self.members, self.budget = ARCHIVE_MEMBERS[(app_id, kind, role)]
        self.path, self.cancelled, self.stream, self.zip = Path(path), is_cancelled, None, None
        self.lock = threading.RLock()
        self.index = {}
        try:
            before = regular(self.path)
            require(before.st_nlink == 1)
            flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
            self.stream = os.fdopen(os.open(self.path, flags), 'rb')
            self.opened, self.named = os.fstat(self.stream.fileno()), regular(self.path)
            require(stat.S_ISREG(self.opened.st_mode) and identity(before) == identity(self.opened) == identity(self.named)
                    and stamp(before) == stamp(self.named))
            digest = hashlib.sha256()
            for block in iter(lambda: self.stream.read(BLOCK), b''):
                require(not self.cancelled())
                digest.update(block)
            require(digest.hexdigest() == expected_sha256)
            self._check()
            directory = self._directory()
            self.zip = zipfile.ZipFile(self.stream)
            entries = self.zip.infolist()
            require(len(entries) == len(self.members) and {entry.filename for entry in entries} == set(self.members)
                    and len({entry.filename.casefold() for entry in entries}) == len(entries))
            total = 0
            ordered = sorted(entries, key=lambda entry: entry.header_offset)
            for number, entry in enumerate(ordered):
                require(entry.orig_filename == entry.filename and entry.filename in self.members and not entry.is_dir()
                        and entry.flag_bits & ~0x800 == 0 and entry.compress_type in (0, 8)
                        and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
                        and entry.external_attr & 0xffff & ~0x21 == 0 and not entry.comment
                        and 0 <= entry.file_size <= self.budget and entry.compress_size >= 0)
                extras(entry.extra)
                total += entry.file_size
                require(total <= self.budget)
                self.stream.seek(entry.header_offset)
                header = self.stream.read(30)
                require(len(header) == 30)
                signature, version, flag, codec, _time, _date, crc, packed, decoded, name_size, extra_size = struct.unpack('<4s5H3L2H', header)
                require(signature == b'PK\x03\x04' and version in (20, 45) and flag == entry.flag_bits
                        and codec == entry.compress_type and crc == entry.CRC)
                require(self.stream.read(name_size) == entry.filename.encode('ascii'))
                local_extras = extras(self.stream.read(extra_size))
                if packed == 0xffffffff or decoded == 0xffffffff:
                    values = local_extras.get(1, b'')
                    require(len(values) == 16)
                    decoded, packed = struct.unpack('<QQ', values)
                require(packed == entry.compress_size and decoded == entry.file_size)
                offset = entry.header_offset + 30 + name_size + extra_size
                following = ordered[number + 1].header_offset if number + 1 < len(ordered) else directory
                require(entry.header_offset == 0 if number == 0 else True)
                require(offset + packed == following)
                self.index[entry.filename] = entry, offset
            self._check()
        except (OSError, ValueError, zipfile.BadZipFile, struct.error, UnicodeError) as error:
            self.close()
            if type(error) is DataIntakeBlocked:
                raise
            raise DataIntakeBlocked('storage' if isinstance(error, OSError) else 'integrity') from None

    def _directory(self):
        size = self.opened.st_size
        require(size >= 22)
        self.stream.seek(size - 22)
        end = self.stream.read(22)
        signature, disk, central_disk, disk_count, count, central_size, central_offset, comment_size = struct.unpack('<4s4H2LH', end)
        require(signature == b'PK\x05\x06' and disk == central_disk == 0 and disk_count == count and comment_size == 0)
        end_offset = size - 22
        self.stream.seek(max(0, size - 42))
        locator = self.stream.read(20)
        if locator.startswith(b'PK\x06\x07') or count == 0xffff or central_size == 0xffffffff or central_offset == 0xffffffff:
            require(size >= 98)
            tag, zip_disk, offset, disks = struct.unpack('<4sLQL', locator)
            require(tag == b'PK\x06\x07' and zip_disk == 0 and disks == 1 and offset == size - 98)
            self.stream.seek(offset)
            record = self.stream.read(56)
            tag, record_size, _made, _version, zip_disk, zip_central_disk, disk_count, count, central_size, central_offset = struct.unpack('<4sQ2H2L4Q', record)
            require(tag == b'PK\x06\x06' and record_size == 44 and zip_disk == zip_central_disk == 0 and disk_count == count)
            end_offset = offset
        require(count == len(self.members) and 0 < central_size <= MAX_DIRECTORY
                and central_offset > 0 and central_offset + central_size == end_offset)
        return central_offset

    def _check(self):
        require(self.stream is not None and not self.stream.closed and not self.cancelled())
        require(stamp(os.fstat(self.stream.fileno())) == stamp(self.opened)
                and stamp(regular(self.path)) == stamp(self.named)
                and identity(os.fstat(self.stream.fileno())) == identity(regular(self.path)))

    def chunks(self, member):
        """No output names or extraction; one bounded decompressor at a time."""
        with self.lock:
            yield from self._chunks(member)

    def _chunks(self, member):
        require(member in self.index)
        self._check()
        entry, offset = self.index[member]
        self.stream.seek(offset)
        left, received, crc = entry.compress_size, 0, 0
        decoder = zlib.decompressobj(-15) if entry.compress_type == 8 else None
        try:
            while left:
                require(not self.cancelled())
                block = self.stream.read(min(BLOCK, left))
                require(block)
                left -= len(block)
                while block:
                    raw = decoder.decompress(block, BLOCK) if decoder else block
                    block = decoder.unconsumed_tail if decoder else b''
                    if decoder:
                        require(not decoder.unused_data and not (decoder.eof and (block or left)))
                    received += len(raw)
                    require(received <= entry.file_size and received <= self.budget)
                    crc = zlib.crc32(raw, crc)
                    if raw:
                        yield raw
            require((decoder is None or decoder.eof) and received == entry.file_size and crc == entry.CRC)
            self._check()
        except (OSError, ValueError, zlib.error) as error:
            if type(error) is DataIntakeBlocked:
                raise
            raise DataIntakeBlocked('storage' if isinstance(error, OSError) else 'integrity') from None

    def json(self, member, *, limit=32 * MiB):
        require(member.endswith('.json') and self.index[member][0].file_size <= limit)
        try:
            return parse(b''.join(self.chunks(member)))
        except ValueError:
            raise DataIntakeBlocked('integrity') from None

    def rows(self, member, *, max_line=8 * MiB, max_records=32_000_000):
        require(member.endswith('.ndjson'))
        buffer, count = b'', 0
        for chunk in self.chunks(member):
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                require(0 < len(line) <= max_line)
                count += 1
                require(count <= max_records)
                try:
                    yield parse(line)
                except ValueError:
                    raise DataIntakeBlocked('integrity') from None
            require(len(buffer) <= max_line)
        require(not buffer)

    def close(self):
        with self.lock:
            if self.zip is not None:
                self.zip.close()
            if self.stream is not None:
                self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
