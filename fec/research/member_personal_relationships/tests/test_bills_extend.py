import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fec.research.member_personal_relationships import bills_extend


def make_bill_xml(congress=115, kind='HR', number=1, chamber='House', sponsor='S000001',
                   introduced='2017-01-03', updated='2017-06-01', policy_area='Health',
                   cosponsors=(), titles=None, committee=None):
    """A minimal but structurally realistic BILLSTATUS XML: root <billStatus> wrapping
    <bill>, matching real congress.gov bulk-data files (exercises the root.find('bill')
    branch in _parse_bill, not just the bare-<bill>-root branch)."""
    if titles is None:
        titles = [('Short T', 'Short Title(s) as Introduced'), ('Official T', 'Official Title as Introduced')]
    cosponsor_xml = ''.join(
        f"<item><bioguideId>{m}</bioguideId><sponsorshipDate>{d}</sponsorshipDate>"
        f"<isOriginalCosponsor>{'True' if orig else 'False'}</isOriginalCosponsor>"
        f"<sponsorshipWithdrawnDate>{w or ''}</sponsorshipWithdrawnDate></item>"
        for m, d, orig, w in cosponsors)
    title_xml = ''.join(
        f"<item><title>{text}</title><titleType>{kind_}</titleType><updateDate>{introduced}</updateDate></item>"
        for text, kind_ in titles)
    committee_xml = ''
    if committee:
        code, date, activity = committee
        committee_xml = (f"<item><systemCode>{code}</systemCode><activities>"
                          f"<item><date>{date}</date><name>{activity}</name></item></activities></item>")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<billStatus><bill>
  <congress>{congress}</congress>
  <type>{kind}</type>
  <number>{number}</number>
  <originChamber>{chamber}</originChamber>
  <introducedDate>{introduced}</introducedDate>
  <updateDate>{updated}</updateDate>
  <policyArea><name>{policy_area}</name></policyArea>
  <sponsors><item><bioguideId>{sponsor}</bioguideId></item></sponsors>
  <cosponsors>{cosponsor_xml}</cosponsors>
  <titles>{title_xml}</titles>
  <committees>{committee_xml}</committees>
  <actions><item><actionDate>{introduced}</actionDate><actionCode>1000</actionCode>
    <type>IntroReferral</type><text>Introduced</text></item></actions>
</bill></billStatus>""".encode('utf-8')


class ParseBillTests(unittest.TestCase):
    def test_original_cosponsor_true_and_false(self):
        xml = make_bill_xml(cosponsors=[('A000001', '2017-01-03', True, None),
                                         ('B000002', '2017-02-01', False, None)])
        row = bills_extend._parse_bill(xml)
        by_member = {c['member']: c for c in row['cosponsors']}
        self.assertIs(by_member['A000001']['original'], True)
        self.assertIs(by_member['B000002']['original'], False)

    def test_withdrawn_cosponsor_date_is_captured(self):
        xml = make_bill_xml(cosponsors=[('B000002', '2017-02-01', False, '2017-03-01')])
        row = bills_extend._parse_bill(xml)
        self.assertEqual(row['cosponsors'][0]['withdrawn'], '2017-03-01')

    def test_missing_withdrawal_date_parses_to_none(self):
        xml = make_bill_xml(cosponsors=[('A000001', '2017-01-03', True, None)])
        row = bills_extend._parse_bill(xml)
        self.assertIsNone(row['cosponsors'][0]['withdrawn'])

    def test_date_formats_normalize_to_iso(self):
        self.assertEqual(bills_extend._date('2017-01-03'), '2017-01-03')
        self.assertEqual(bills_extend._date('01/03/2017'), '2017-01-03')
        self.assertEqual(bills_extend._date('2017/01/03'), '2017-01-03')
        self.assertEqual(bills_extend._date('2017-01-03T00:00:00Z'), '2017-01-03')

    def test_unparseable_date_is_none(self):
        self.assertIsNone(bills_extend._date('not-a-date'))
        self.assertIsNone(bills_extend._date(''))
        self.assertIsNone(bills_extend._date(None))

    def test_key_congress_type_number_and_root_wrapper_handled(self):
        xml = make_bill_xml(congress=115, kind='S', number=42)
        row = bills_extend._parse_bill(xml)
        self.assertEqual(row['key'], '115:s:42')
        self.assertEqual(row['congress'], 115)
        self.assertEqual(row['type'], 's')
        self.assertEqual(row['number'], 42)

    def test_finance_at_introduction_true_when_referred_to_finance_committee_on_intro_day(self):
        xml = make_bill_xml(introduced='2017-01-03', committee=('hsag00', '2017-01-03', 'Referred to'))
        row = bills_extend._parse_bill(xml)
        self.assertTrue(row['finance_at_introduction'])

    def test_finance_at_introduction_false_for_non_finance_committee(self):
        xml = make_bill_xml(introduced='2017-01-03', committee=('hsju00', '2017-01-03', 'Referred to'))
        row = bills_extend._parse_bill(xml)
        self.assertFalse(row['finance_at_introduction'])

    def test_titles_filtered_to_as_introduced_only(self):
        xml = make_bill_xml(titles=[('Short T', 'Short Title(s) as Introduced'),
                                     ('Later T', 'Short Title(s) as Enacted')])
        row = bills_extend._parse_bill(xml)
        self.assertEqual([t['kind'] for t in row['titles']], ['Short Title(s) as Introduced'])


class ReshapeTests(unittest.TestCase):
    def test_final_schema_fields_and_filters(self):
        members = {
            'A000001': {'terms': [{'start': '2017-01-03', 'end': '2019-01-03', 'chamber': 'House'}]},
            'S000001': {'terms': [{'start': '2017-01-03', 'end': '2019-01-03', 'chamber': 'House'}]},
            # C000003 is in the roster but its only term starts after this bill's joins:
            # exercises the dated-service exclusion (distinct from B000002, who is not in
            # the roster at all and therefore passes through unchecked).
            'C000003': {'terms': [{'start': '2019-01-03', 'end': '2021-01-03', 'chamber': 'House'}]},
        }
        raw_bill = dict(
            key='115:hr:1', congress=115, type='hr', number=1, chamber='House',
            sponsor='S000001', introduced='2017-01-03', updated='2017-06-01', policy_area='Health',
            titles=[{'text': 'Short T', 'kind': 'Short Title(s) as Introduced', 'updated': '2017-01-03'},
                    {'text': 'Official T', 'kind': 'Official Title as Introduced', 'updated': '2017-01-03'}],
            cosponsors=[
                {'member': 'A000001', 'date': '2017-01-03', 'original': True, 'withdrawn': None},
                {'member': 'B000002', 'date': '2017-02-01', 'original': False, 'withdrawn': '2017-03-01'},
                {'member': 'S000001', 'date': '2017-01-05', 'original': False, 'withdrawn': None},
                {'member': 'C000003', 'date': '2017-02-15', 'original': False, 'withdrawn': None},
            ])
        bills, audit = bills_extend.reshape([raw_bill], members, '2026-09-10', 115, 115)
        self.assertEqual(len(bills), 1)
        row = bills[0]
        self.assertEqual(set(row), set(bills_extend.FINAL_ROW_FIELDS))
        self.assertEqual(sorted(row['joins']), ['A000001', 'B000002'])
        self.assertEqual(row['original'], ['A000001'])
        self.assertEqual(row['withdrawals'], {'B000002': '2017-03-01'})
        self.assertEqual(row['size'], 2)
        self.assertEqual(row['end'], '2019-01-03')
        self.assertEqual(row['title'], 'Short T')
        self.assertEqual(row['area'], 'Health')
        self.assertEqual(row['url'], 'https://www.congress.gov/bill/115th-congress/house-bill/1')
        self.assertEqual(audit['self_signature'], 1)
        self.assertEqual(audit['join_outside_dated_service'], 1)
        self.assertEqual(audit['included_bills'], 1)

    def test_congress_outside_requested_range_is_dropped(self):
        raw_bill = dict(key='116:hr:1', congress=116, type='hr', number=1, chamber='House',
                         sponsor='S000001', introduced='2019-01-03', updated=None, policy_area=None,
                         titles=[], cosponsors=[])
        bills, audit = bills_extend.reshape([raw_bill], {}, '2026-09-10', 115, 115)
        self.assertEqual(bills, [])
        self.assertEqual(audit['outside_congress_or_cutoff'], 1)

    def test_latest_updated_wins_on_duplicate_key(self):
        older = dict(key='115:hr:1', congress=115, type='hr', number=1, chamber='House',
                      sponsor='S000001', introduced='2017-01-03', updated='2017-01-01', policy_area=None,
                      titles=[], cosponsors=[])
        newer = dict(older, updated='2017-06-01')
        bills, audit = bills_extend.reshape([older, newer], {}, '2026-09-10', 115, 115)
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0]['updated'], '2017-06-01')
        self.assertEqual(audit['duplicate_bill_records'], 1)


class VerbatimCopyTests(unittest.TestCase):
    def test_source_bytes_are_appended_byte_identical_after_new_rows(self):
        source_bytes = b'{"key": "116:hr:1", "congress": 116}\n{"key": "116:hr:2", "congress": 116}\n'
        new_rows = [{'key': '115:hr:1', 'congress': 115}]
        with tempfile.TemporaryDirectory() as d:
            out_path = Path(d) / 'bills.ndjson'
            bills_extend.write_output_ndjson(out_path, new_rows, source_bytes)
            content = out_path.read_bytes()
        first_line = (json.dumps(new_rows[0], ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        self.assertEqual(content, first_line + source_bytes)
        self.assertEqual(content[len(first_line):], source_bytes)


class DeterminismTests(unittest.TestCase):
    def test_two_parses_of_the_same_zip_are_byte_identical(self):
        xml1 = make_bill_xml(number=1, cosponsors=[('A000001', '2017-01-03', True, None)])
        xml2 = make_bill_xml(number=2, cosponsors=[('B000002', '2017-02-01', False, None)])
        with tempfile.TemporaryDirectory() as d:
            zip_path = Path(d) / 'BILLSTATUS-115-hr.zip'
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr('BILLSTATUS-115hr1.xml', xml1)
                zf.writestr('BILLSTATUS-115hr2.xml', xml2)
            first = bills_extend.parse_zip_bills(zip_path, 115, 'hr')
            second = bills_extend.parse_zip_bills(zip_path, 115, 'hr')
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        rows1, audit1 = bills_extend.reshape(first, {}, '2026-09-10', 115, 115)
        rows2, audit2 = bills_extend.reshape(second, {}, '2026-09-10', 115, 115)
        self.assertEqual(json.dumps(rows1, sort_keys=True), json.dumps(rows2, sort_keys=True))
        self.assertEqual(audit1, audit2)


class ManifestCountsTests(unittest.TestCase):
    def test_counts_by_congress_and_type(self):
        new_rows = [{'key': '115:hr:1'}, {'key': '115:hr:2'}, {'key': '115:s:1'}]
        existing_lines = [json.dumps({'key': '116:hr:1'}), json.dumps({'key': '116:s:1'}), '', '  ']
        counts = bills_extend.count_by_congress_and_type(new_rows, existing_lines)
        self.assertEqual(counts, {'115': {'hr': 2, 's': 1}, '116': {'hr': 1, 's': 1}})


if __name__ == '__main__':
    unittest.main()
