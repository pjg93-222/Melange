"""Write a tiny synthetic itoth.txt plus a synthetic filing-header store.

21 pipe-separated OTH fields:
0 CMTE_ID 1 AMNDT_IND 2 RPT_TP 3 TRANSACTION_PGI 4 IMAGE_NUM 5 TRANSACTION_TP
6 ENTITY_TP 7 NAME 8 CITY 9 STATE 10 ZIP 11 EMPLOYER 12 OCCUPATION
13 TRANSACTION_DT 14 TRANSACTION_AMT 15 OTHER_ID 16 TRAN_ID 17 FILE_NUM
18 MEMO_CD 19 MEMO_TEXT 20 SUB_ID

Branches deliberately exercised (see V3_MEASURE_REPORT.md for expected values):
  current / superseded / duplicate / unresolved_version / unresolved_record,
  a multi-filing group headers CAN settle, a multi-filing group they cannot
  (evidence absent), a group that collides INSIDE one filing (never settleable
  by a header), a noncash amendment that wins and deletes a cash edge, a memo
  row, a blank TRAN_ID, an invalid destination and a malformed line.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SMOKE = ROOT / 'smoke'
US = '\x1c'
sys.path.insert(0, r'C:\Users\pgoff\Mentat\mentat\tools')
from fec_filing_headers import parse_header


def row(cmte, amnd, ttype, date, amount, other, tran, file_num, memo, sub):
    return '|'.join([cmte, amnd, 'M6', 'P', 'IMG' + sub, ttype, 'COM', 'RECIPIENT COMMITTEE',
                     'WASHINGTON', 'DC', '20003', '', '', date, amount, other, tran,
                     str(file_num), memo, 'memo text', sub])


def header_evidence(file_num, committee, amendment, amendment_number, original):
    hdr = ['HDR', 'FEC', '8.4', 'NGP', '8',
           ('FEC-%d' % original) if original else '', amendment_number, '']
    report = ['F3X' + amendment, committee, 'SYNTHETIC COMMITTEE', '', '', 'WASHINGTON', 'DC',
              '20003', '', 'M6', '', '', '', '20240501', '20240531', '', '', '']
    prefix = (US.join(hdr) + '\n' + US.join(report) + '\nSA11AI' + US + committee + '\n').encode()
    return {'evidence_scope': 'filing_header_only',
            'header': parse_header(prefix, file_num),
            'prefix_hex': prefix.hex(),
            'prefix_sha256': hashlib.sha256(prefix).hexdigest(),
            'retrieved_at': '2026-09-18T00:00:00+00:00',
            'specification': 'synthetic-smoke-test',
            'url': f'https://docquery.fec.gov/dcdev/posted/{file_num}.fec'}


def main():
    SMOKE.mkdir(parents=True, exist_ok=True)
    headers_dir = SMOKE / 'headers'
    headers_dir.mkdir(exist_ok=True)

    plain = row('C00000001', 'N', '24K', '05152024', '1000.00', 'C00000002', 'T1', 9000000, '', 'SUB0001')
    lines = [
        plain,                                                    # current, edge 1000
        plain,                                                    # byte-identical -> 'duplicate'
        # T9: three filings, headers settle the family; the T amendment is 22Y,
        # so the winning version is NOT cash and the edge disappears.
        row('C00000003', 'N', '24K', '05152024', '2000.00', 'C00000002', 'T9', 9000001, '', 'SUB0002'),
        row('C00000003', 'A', '24K', '05152024', '2500.00', 'C00000002', 'T9', 9000002, '', 'SUB0003'),
        row('C00000003', 'T', '22Y', '05152024', '2500.00', 'C00000002', 'T9', 9000009, '', 'SUB0012'),
        # T20: two filings, headers settle it, the amendment wins -> 1800 current.
        row('C00000010', 'N', '24K', '05202024', '1500.00', 'C00000002', 'T20', 9000010, '', 'SUB0013'),
        row('C00000010', 'A', '24K', '05202024', '1800.00', 'C00000002', 'T20', 9000011, '', 'SUB0014'),
        # T21: one TRAN_ID twice INSIDE one filing -> no header can settle it.
        row('C00000011', 'A', '24K', '05212024', '600.00', 'C00000002', 'T21', 9000012, '', 'SUB0015'),
        row('C00000011', 'A', '24K', '05212024', '650.00', 'C00000002', 'T21', 9000012, '', 'SUB0016'),
        # T10: two filings, NO header evidence supplied -> unresolved_version.
        row('C00000004', 'N', '24K', '06152024', '7000.00', 'C00000005', 'T10', 9000003, '', 'SUB0004'),
        row('C00000004', 'A', '24K', '06152024', '9000.00', 'C00000005', 'T10', 9000004, '', 'SUB0005'),
        # C00000004 also has a perfectly clean edge: the whole committee is
        # blacklisted anyway, which is exactly the cost being measured.
        row('C00000004', 'N', '24G', '07012024', '4000.00', 'C00000006', 'T11', 9000005, '', 'SUB0006'),
        row('C00000001', 'N', '24K', '05162024', '500.00', 'C00000002', 'T2', 9000000, 'X', 'SUB0007'),
        row('C00000007', 'N', '24K', '08012024', '300.00', 'C00000002', '', 9000006, '', 'SUB0009'),
        row('C00000008', 'N', '24K', '08022024', '250.00', 'NOTACMTE', 'T12', 9000007, '', 'SUB0010'),
        row('C00000001', 'N', '24G', '09012024', '750.00', 'C00000006', 'T13', 9000000, '', 'SUB0011'),
        'C00000009|N|M6|P|IMGBAD|24K|COM|BAD ROW|WASHINGTON|DC|20003||',   # 13 fields
    ]
    (SMOKE / 'itoth.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    evidence = [header_evidence(9000000, 'C00000001', 'N', '', None),
                header_evidence(9000001, 'C00000003', 'N', '', None),
                header_evidence(9000002, 'C00000003', 'A', '1', 9000001),
                header_evidence(9000009, 'C00000003', 'T', '2', 9000001),
                header_evidence(9000005, 'C00000004', 'N', '', None),
                header_evidence(9000006, 'C00000007', 'N', '', None),
                header_evidence(9000007, 'C00000008', 'N', '', None),
                header_evidence(9000010, 'C00000010', 'N', '', None),
                header_evidence(9000011, 'C00000010', 'A', '1', 9000010),
                header_evidence(9000012, 'C00000011', 'A', '1', 9000008)]
    for item in evidence:
        (headers_dir / f"{item['header']['file_num']}.json").write_text(
            json.dumps(item, indent=2, sort_keys=True), encoding='utf-8')
    (headers_dir / '9000099.review.json').write_text(
        json.dumps({'error': 'unsupported format', 'url': 'x'}), encoding='utf-8')
    print(f'wrote {len(lines)} rows -> {SMOKE / "itoth.txt"}')
    print(f'wrote {len(evidence)} headers + 1 review file -> {headers_dir}')


if __name__ == '__main__':
    main()
