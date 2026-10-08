import sys
p = sys.argv[1]; b = open(p, "rb").read(); eol = b"\r\n" if b"\r\n" in b else b"\n"
a = b"'test_sponsor_column','test_stage_billstatus_bulk_enrichment')"
a2 = b"'test_sponsor_column','test_sponsor_column_producer_wiring','test_stage_billstatus_bulk_enrichment')"
c = b"               'test_crosspost_key'," + eol
c2 = c + b"               'test_crosspost_key_engine_wiring'," + eol
assert b.count(a) == 1, ("legislation anchor count", b.count(a))
assert b.count(c) == 1, ("modules anchor count", b.count(c))
assert b"test_sponsor_column_producer_wiring" not in b and b"test_crosspost_key_engine_wiring" not in b
open(p, "wb").write(b.replace(a, a2).replace(c, c2))
print("run_tests.py: 2 wiring suites registered; eol =", "CRLF" if eol == b"\r\n" else "LF")
