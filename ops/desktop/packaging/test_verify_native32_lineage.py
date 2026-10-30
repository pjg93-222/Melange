"""Synthetic closed-lineage verifier fixtures, not production native evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import re
import unittest
from unittest.mock import patch

import verify_native_release as n


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class SealedLineageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='native32 lineage fixture ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.client = self.root / 'capsule/ops/desktop/client'
        self.client.mkdir(parents=True)
        self.frozen = self.client.parents[2]
        self.commit = 'e' * 40
        self.proof_path = self.root / 'origin.json'

    def write(self, path, value):
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {'path': str(path), 'sha256': sha(raw)}

    def make(self, app='melange'):
        old = {'app.py': {'size': 7, 'sha256': '1' * 64}}
        reader = b'reviewed reader fixture'
        if app == 'melange':
            old.update({n.GRAPH33_SOURCE: {'size': 10, 'sha256': '2' * 64},
                        n.SERVICE33_SOURCE: {'size': 11, 'sha256': '4' * 64},
                        n.READER32_SOURCE: {'size': len(reader), 'sha256': sha(reader)}})
        self.retained = old
        self.sources = copy.deepcopy(old)
        self.prefix = 'resources/runtime/' + app + '/'
        self.original = {self.prefix + 'sources/' + name: row for name, row in old.items()}
        self.original[self.prefix + 'source-provenance.json'] = {'size': 17, 'sha256': '3' * 64}
        inherited = None
        reader_hash = n.READER32_PROOF
        if app == 'melange':
            inherited = self.write(self.root / 'reader32.json', {'status': 'passed', 'appId': app,
                'overrideSourceCommit': n.SEALED32_CLIENT, 'override': {'bytes': len(reader), 'sha256': sha(reader)}})
            reader_hash = inherited['sha256']
        self.report = {'status': 'passed', 'appId': app, 'version': '1.0.32',
            'clientCommit': n.SEALED32_CLIENT, 'sourceCommit': n.SEALED_NATIVE32[app]['source'],
            'installerSha256': n.SEALED_NATIVE32[app]['installer'], 'applicationFiles': self.original,
            'sourceProvenance': {'originProofSha256': reader_hash}}
        report_ref = self.write(self.root / 'native32.json', self.report)
        self.pin = {**n.SEALED_NATIVE32[app], 'report': report_ref['sha256']}
        overrides, blobs = [], {}
        if app == 'melange':
            for name in n.MELANGE33_GIT_SOURCES:
                raw = b'# exact fixture Git blob: ' + name.encode() + b'\n'
                graph = self.frozen / name
                graph.parent.mkdir(parents=True,exist_ok=True)
                graph.write_bytes(raw)
                blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                overrides.append({'gitPath': name, 'path': str(graph), 'bytes': len(raw), 'sha256': sha(raw), 'gitBlob': blob})
                blobs[name] = {'gitObject': blob, 'bytes': len(raw), 'sha256': sha(raw)}
                self.sources[name] = {'size': len(raw), 'sha256': sha(raw)}
        archive = self.frozen / 'committed-source.zip'
        archive.write_bytes(b'fixture for trusted-controller Git archive binding')
        frozen = {'status': 'passed-committed-source-freeze', 'sourceClientCommit': self.commit,
            'protectedResidueWritten': False, 'archiveContainsProtectedResidue': False,
            'allNamedGitBlobsMatch': True, 'archiveSha256': sha(archive.read_bytes()), 'sourceGitBlobs': blobs,
            **{phase: {'head': self.commit, 'remoteBranchCommit': self.commit, 'trackedStatus': ''} for phase in ('before', 'after')}}
        evidence = self.write(self.frozen / 'source-freeze-evidence.json', frozen)
        self.write(self.frozen / 'capsule-provenance.json', {'commit': self.commit, 'version': '1.0.33',
            'sourceFreezeEvidenceSha256': evidence['sha256'], 'archiveSha256': frozen['archiveSha256']})
        canonical = json.dumps(old, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        self.source_commit = self.commit if app == 'melange' else self.pin['source']
        self.proof = {'schemaVersion': 1, 'appId': app, 'status': 'passed',
            'provenanceKind': 'sealed-native32-with-exact-git-overrides', 'baseVersion': '1.0.32',
            'baseSourceCommit': self.pin['source'], 'clientCommit': self.commit, 'sourceCommit': self.source_commit,
            'baseNativeReport': report_ref, 'baseSourceProvenanceSha256': '3' * 64,
            'baseSourceMapSha256': sha(canonical), 'sourceFileCount': len(old), 'overrides': overrides,
            'sourceFreezeEvidence': evidence, 'inheritedReaderProof': inherited}
        self.origin = {'kind': self.proof['provenanceKind'], 'baseVersion': '1.0.32', 'baseSourceCommit': self.pin['source'],
            'baseNativeReportSha256': report_ref['sha256'], 'proofSha256': '', 'sharedBootstrapSourceCommit': self.commit,
            'sourceFileCount': len(old), 'gitOverrideFileCount': len(overrides), 'retainedExportFileCount': len(old)-len(overrides)}
        self.app, self.reader_hash = app, reader_hash
        self.refresh()

    def refresh(self):
        self.origin['proofSha256'] = self.write(self.proof_path, self.proof)['sha256']

    def verify(self):
        # Synthetic tests replace ONLY the immutable production evidence pins.
        with patch.dict(n.SEALED_NATIVE32, {self.app: self.pin}), patch.object(n, 'READER32_PROOF', self.reader_hash):
            return n.sealed32_source_origin(app=self.app, origin=self.origin, proof_file=self.proof_path,
                client=self.client, client_commit=self.commit, source_commit=self.source_commit,
                sources=self.sources, retained=self.retained, original_reference=self.original)

    def test_exact_graph_git_override_and_inherited_reader_are_bound(self):
        self.make()
        self.assertEqual(self.verify(), self.origin['proofSha256'])

    def test_terrier_and_mentat_inherit_exact32_sources_without_fabricated_old_diff(self):
        for app in ('terrier', 'mentat'):
            self.make(app)
            self.assertEqual(self.verify(), self.origin['proofSha256'])
            self.sources['app.py']['sha256'] = '9' * 64
            with self.assertRaises(n.Refused):
                self.verify()

    def test_any_other_source_or_inherited_reader_change_is_refused(self):
        self.make()
        for name in ('app.py', n.READER32_SOURCE):
            before = copy.deepcopy(self.sources[name])
            self.sources[name]['sha256'] = '9' * 64
            with self.assertRaises(n.Refused):
                self.verify()
            self.sources[name] = before

    def test_actual_report_hash_and_whole_baseline_source_map_are_required(self):
        self.make()
        path = Path(self.proof['baseNativeReport']['path'])
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(n.Refused):
            self.verify()
        self.write(path, self.report)
        self.retained['app.py']['sha256'] = '0' * 64
        with self.assertRaises(n.Refused):
            self.verify()

    def test_override_must_equal_the_actual_frozen_git_blob_and_freeze_commit(self):
        self.make()
        graph = Path(self.proof['overrides'][0]['path'])
        graph.write_bytes(b'changed actual graph bytes')
        with self.assertRaises(n.Refused):
            self.verify()

    def test_capsule_must_hash_the_actual_freeze_record_and_actual_archive(self):
        self.make()
        path = self.frozen / 'capsule-provenance.json'
        value = json.loads(path.read_bytes())
        value['sourceFreezeEvidenceSha256'] = '0' * 64
        self.write(path, value)
        with self.assertRaises(n.Refused):
            self.verify()
        value['sourceFreezeEvidenceSha256'] = self.proof['sourceFreezeEvidence']['sha256']
        self.write(path, value)
        (self.frozen / 'committed-source.zip').write_bytes(b'not the frozen archive')
        with self.assertRaises(n.Refused):
            self.verify()

    def test_unapproved_source_override_and_unknown_proof_fields_are_refused(self):
        self.make()
        self.proof['overrides'][0]['gitPath'] = 'unapproved.py'
        self.refresh()
        with self.assertRaises(n.Refused):
            self.verify()
        self.proof['overrides'][0]['gitPath'] = n.GRAPH33_SOURCE
        self.proof['genericOverrideAuthority'] = True
        self.refresh()
        with self.assertRaises(n.Refused):
            self.verify()

    def test_duplicate_graph_cannot_replace_the_required_service_git_proof(self):
        self.make()
        self.proof['overrides'][1]=copy.deepcopy(self.proof['overrides'][0])
        self.refresh()
        with self.assertRaises(n.Refused):self.verify()


class Overlay33Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='reviewed overlay33 ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.program = self.root / 'base'
        self.overlay = self.root / 'overlay'
        self.program.mkdir()
        self.manifest = self.overlay / 'manifest.json'

    def put(self, root, relative, raw):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def run_overlay(self, app, relative, *, existing=False):
        if existing:
            self.put(self.program, relative, b'retained source')
        raw = b'reviewed exact new helper'
        self.put(self.overlay / 'files', relative, raw)
        value = {'schemaVersion': 1, 'appId': app, 'version': '1.0.33',
            'clientCommit': 'a' * 40, 'sourceCommit': 'b' * 40,
            'files': [{'path': relative, 'bytes': len(raw), 'sha256': sha(raw)}]}
        self.manifest.write_text(json.dumps(value))
        return n.source_overlays(*n.scan(self.program), app, '1.0.33', self.manifest, 'a' * 40, 'b' * 40)

    def test_new_helper_is_explicit_but_missing_old_helper_is_never_a_new_addition(self):
        prefix = 'resources/runtime/mentat/bootstrap/'
        result = self.run_overlay('mentat', prefix + 'workspace_cache.py')
        self.assertIn(prefix + 'workspace_cache.py', result[0])
        (self.overlay / 'files' / (prefix + 'workspace_cache.py')).unlink()
        with self.assertRaises(n.Refused):
            self.run_overlay('mentat', prefix + 'desktop_backend.py')

    def test_only_melange_graph_is_allowed_and_legacy_reader_is_inherited(self):
        prefix = 'resources/runtime/melange/sources/'
        self.assertIn(prefix + n.GRAPH33_SOURCE, self.run_overlay('melange', prefix + n.GRAPH33_SOURCE, existing=True)[0])
        (self.overlay / 'files' / (prefix + n.GRAPH33_SOURCE)).unlink()
        with self.assertRaises(n.Refused):
            self.run_overlay('melange', prefix + n.READER32_SOURCE, existing=True)

    def test_producer_and_independent_verifier_have_the_same_explicit_reviewed_roster(self):
        source = (Path(__file__).parent.parent / 'client/build-plugin-free.cjs').read_text()
        def names(label):
            block = source.split('const ' + label + ' = Object.freeze([', 1)[1].split(']);', 1)[0]
            return set(re.findall(r"'([^']+\.py)'", block))
        self.assertEqual(names('BOOTSTRAP_OVERLAY33'), n.BOOTSTRAP_OVERLAY33)
        self.assertEqual(names('BOOTSTRAP_ADDITIONS33'), n.BOOTSTRAP_ADDITIONS33)
        self.assertEqual(len(n.BOOTSTRAP_OVERLAY33), 43)
        self.assertEqual(len(n.BOOTSTRAP_ADDITIONS33), 16)


if __name__ == '__main__':
    unittest.main()
