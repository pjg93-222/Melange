"""Inline pocket-data.json into mentat-pocket.html between its data markers.

Idempotent: the markers survive the rewrite, so the build can run again over an
already-built page. The data is emitted as a JS object literal (JSON is a subset
of JS object-literal syntax), never as a JSON.parse call.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
PAGE = HERE / 'mentat-pocket.html'
DATA = HERE / 'pocket-data.json'
PATTERN = re.compile(r'(/\*__DATA_START__\*/).*?(/\*__DATA_END__\*/)', re.S)


def main():
    payload = json.loads(DATA.read_text(encoding='utf-8'))
    literal = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    # A JS source file must not contain a raw </script> or U+2028/U+2029.
    literal = (literal.replace('</', '<\\/')
                      .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))
    page = PAGE.read_text(encoding='utf-8')
    if not PATTERN.search(page):
        raise SystemExit('Data markers not found in ' + str(PAGE))
    built = PATTERN.sub(lambda m: m.group(1) + literal + m.group(2), page, count=1)
    PAGE.write_text(built, encoding='utf-8')
    print('inlined {} bytes of data; page is now {} bytes'.format(
        len(literal), PAGE.stat().st_size))


if __name__ == '__main__':
    main()
