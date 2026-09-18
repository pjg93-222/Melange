"""Byte-faithful patch helper. Detects the file's line ending (LF or CRLF),
works in LF internally, writes back with the same ending. Every anchor must
occur exactly once."""

_ENDING = {}


def load(path):
    data = open(path, "rb").read()
    crlf, lf = data.count(b"\r\n"), data.count(b"\n")
    if crlf and crlf != lf:
        raise SystemExit(f"{path}: mixed line endings ({crlf} CRLF of {lf} LF)")
    if data.count(b"\r") != crlf:
        raise SystemExit(f"{path}: lone CR bytes present")
    _ENDING[path] = b"\r\n" if crlf else b"\n"
    print(path, "line ending", "CRLF" if crlf else "LF", "lines", lf)
    return data.decode("utf-8").replace("\r\n", "\n")


def replace_once(text, anchor, replacement, label):
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"anchor {label!r} found {count} times, expected 1")
    return text.replace(anchor, replacement)


def save(path, text):
    ending = _ENDING[path]
    data = text.encode("utf-8")
    if ending == b"\r\n":
        data = data.replace(b"\n", b"\r\n")
    open(path, "wb").write(data)
    print("wrote", path, "ending", "CRLF" if ending == b"\r\n" else "LF", "lines", data.count(b"\n"))
