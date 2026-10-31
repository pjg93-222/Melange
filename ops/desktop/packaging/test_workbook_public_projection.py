"""Fabricated workbooks test redaction, caches, closed policy and namespace bytes."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

import workbook_public_projection as p


MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Community Banks Industry Spending Overview.xlsx'
        self.out = self.root / 'out'
        self.out.mkdir()

    def workbook(self, *, street_formula=False, unknown=False, active=False):
        strings = ['Source ID', 'Street 1', 'Street 2', 'ZIP', 'TotalGiving',
                   '900 PRIVATE HOME ROAD', 'APT PRIVATE-9', '12345-6789',
                   'stable-source-id', 'public-office-77', 'UNUSED PRIVATE STREET']
        shared = ('<sst xmlns="' + MAIN + '" count="11" uniqueCount="11">' +
                  ''.join('<si><t>' + value + '</t></si>' for value in strings) + '</sst>')
        # mc/x14ac declarations must survive even though only mc:Ignorable uses one.
        header = ('<worksheet xmlns="' + MAIN + '" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
                  'xmlns:x14ac="http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac" mc:Ignorable="x14ac">')
        sheet = header + '<sheetData><row r="1"><c r="A1"><f>SUM(2,3)</f><v>5</v></c><c r="B1" t="s"><v>9</v></c></row>'
        sheet += '<row r="5"><c r="A5" t="s"><v>0</v></c></row><row r="6">'
        sheet += '<c r="A6" t="s"><v>8</v></c><c r="B6" t="s">' + ('<f>UNSAFE()</f>' if street_formula else '') + '<v>5</v></c>'
        sheet += '<c r="C6" t="s"><v>6</v></c><c r="D6" t="s"><v>7</v></c><c r="E6"><v>1234.50</v></c></row></sheetData></worksheet>'
        columns = ['Company', 'Employer', 'Occupation', 'ZIP', 'TotalGiving']
        # Closed contributor schema uses street1/2; Company/Employer/Occupation are also present.
        columns = ['Company', 'Street 1', 'Street 2', 'ZIP', 'TotalGiving', 'Employer', 'Occupation']
        table = '<table xmlns="' + MAIN + '" name="' + ('UnknownTable' if unknown else 'ContributorDetailTable') + '" ref="A5:G6"><tableColumns>'
        table += ''.join('<tableColumn id="' + str(i) + '" name="' + name + '"/>' for i, name in enumerate(columns, 1)) + '</tableColumns></table>'
        relation = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/></Relationships>'
        with zipfile.ZipFile(self.source, 'w') as archive:
            archive.writestr('xl/sharedStrings.xml', shared)
            archive.writestr('xl/worksheets/sheet1.xml', sheet)
            archive.writestr('xl/worksheets/_rels/sheet1.xml.rels', relation)
            archive.writestr('xl/tables/table1.xml', table)
            archive.writestr('xl/styles.xml', '<styleSheet xmlns="' + MAIN + '"/>')
            if active:
                archive.writestr('xl/externalLinks/externalLink1.xml', '<externalLink/>')
        return self.source.read_bytes()

    def run_projection(self, directory=None):
        raw = self.source.read_bytes()
        return p.project_workbook(self.source, (directory or self.out) / self.source.name,
                                  expected_sha256=hashlib.sha256(raw).hexdigest(), expected_bytes=len(raw))

    def test_exact_semantics_and_namespaces_survive_with_orphan_values_removed(self):
        before = self.workbook()
        receipt = self.run_projection()
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(receipt['changedDonorCells'], {'blank': 2, 'zip': 1})
        self.assertTrue(receipt['cachedFormulaValuesPreserved'])
        with zipfile.ZipFile(self.out / self.source.name) as archive:
            xml = archive.read('xl/worksheets/sheet1.xml')
            self.assertIn(b'mc:Ignorable="x14ac"', xml)
            self.assertIn(b'xmlns:x14ac=', xml)
            self.assertIn(b'<f>SUM(2,3)</f><v>5</v>', xml)
            self.assertIn(b'<v>1234.50</v>', xml)
            shared = archive.read('xl/sharedStrings.xml')
            self.assertNotIn(b'PRIVATE', shared)
            self.assertNotIn(b'12345-6789', shared)
            self.assertIn(b'public-office-77', shared)
            self.assertIn(b'>12345</t>', xml)

    def test_same_inputs_produce_identical_bytes(self):
        self.workbook()
        first = self.run_projection()
        second = self.root / 'second'
        second.mkdir()
        self.assertEqual(first['projected']['sha256'], self.run_projection(second)['projected']['sha256'])

    def test_unknown_fields_formulas_and_active_content_fail_closed(self):
        for options in ({'unknown': True}, {'street_formula': True}, {'active': True}):
            self.workbook(**options)
            with self.assertRaises(p.ProjectionError):
                self.run_projection()
            self.assertFalse((self.out / self.source.name).exists())

    def test_wrong_parent_and_existing_destination_refuse_without_changing_original(self):
        original = self.workbook()
        with self.assertRaises(p.ProjectionError):
            p.project_workbook(self.source, self.out / self.source.name, expected_sha256='0' * 64, expected_bytes=len(original))
        (self.out / self.source.name).write_bytes(b'owner fixture')
        with self.assertRaises(p.ProjectionError):
            self.run_projection()
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual((self.out / self.source.name).read_bytes(), b'owner fixture')

    def test_streaming_split_boundaries_and_unknown_postal_values(self):
        class Small(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 3))
        raw = b'<worksheet><c r="A1"><v>123</v></c><c r="B2"/><tail/></worksheet>'
        result = io.BytesIO()
        p.cell_stream(Small(raw), lambda value: value, result)
        self.assertEqual(result.getvalue(), raw)
        self.assertEqual(p.zip5('00123-4567; 999991234 | 54321'), '00123; 99999; 54321')
        self.assertEqual(p.zip5('00123; foreign-postal; 123; 999991234'), '00123; 99999')
        self.assertEqual(p.zip5('unexpected postal value'), '')

    def test_changed_numeric_cache_and_reintroduced_orphan_string_fail_independent_verifier(self):
        self.workbook()
        self.run_projection()
        with zipfile.ZipFile(self.source) as original:
            policies, _ = p.ranges(original)
            _, _, texts, _ = p.shared_strings(original)
        for mutation in ('numeric-cache', 'orphan-string'):
            tampered = self.root / (mutation + '.xlsx')
            with zipfile.ZipFile(self.out / self.source.name) as source, zipfile.ZipFile(tampered, 'w') as output:
                for info in source.infolist():
                    raw = source.read(info)
                    if mutation == 'numeric-cache' and info.filename == 'xl/worksheets/sheet1.xml':
                        raw = raw.replace(b'<v>1234.50</v>', b'<v>1234.51</v>')
                    if mutation == 'orphan-string' and info.filename == 'xl/sharedStrings.xml':
                        raw = raw.replace(b'</sst>', b'<si><t>ORPHAN PRIVATE STREET</t></si></sst>')
                    output.writestr(info, raw)
            with self.assertRaises(p.ProjectionError):
                p.verify_parity(self.source, tampered, policies=policies, safe_source_texts=texts)

    def test_editor_absolute_path_metadata_is_removed_without_namespace_reserialization(self):
        raw = (b'<workbook xmlns="' + MAIN.encode() + b'" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
               b'xmlns:x15ac="http://schemas.microsoft.com/office/spreadsheetml/2010/11/ac" mc:Ignorable="x15ac">'
               b'<mc:AlternateContent><mc:Choice Requires="x15ac"><x15ac:absPath url="C:\\Users\\fixture\\private\\"/></mc:Choice></mc:AlternateContent>'
               b'<sheets/></workbook>')
        result = p.metadata_member('xl/workbook.xml', raw, p.PublicationProjection())
        self.assertNotIn(b'Users', result)
        self.assertIn(b'xmlns:x15ac=', result)
        self.assertIn(b'mc:Ignorable="x15ac"', result)
        self.assertIn(b'<sheets/>', result)


if __name__ == '__main__':
    unittest.main()
