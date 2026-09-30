"""Publication identity, atomic pointer switching and actual R-publisher/Python-consumer integration."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
sys.path.insert(0, str(ROOT / 'forecast' / 'contracts'))
import giving_forecast as gf
import contract


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.v1 = self.dir / 'giving-models-v1.json'
        self.v2 = self.dir / 'giving-models-v2.json'
        shutil.copyfile(ROOT / 'app' / 'data' / self.v1.name, self.v1)
        self.bundle = contract.example('models')
        self.v2.write_text(json.dumps(self.bundle), encoding='utf-8')
        self.patches = [patch.object(gf, 'MODEL_FILE', self.v1), patch.object(gf, 'MODEL_FILE_V2', self.v2),
                        patch.dict(os.environ, {'MENTAT_GIVING_MODELS': ''})]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        gf._load.cache_clear()
        self.addCleanup(gf._load.cache_clear)

    def pointer(self, path, **edits):
        raw = path.read_bytes()
        bundle = json.loads(raw)
        pointer = dict(schema_version=1, active=path.relative_to(self.dir).as_posix(), sha256=hashlib.sha256(raw).hexdigest(),
                       model_version=bundle['model_version'], model_schema_version=bundle['schema_version'])
        pointer.update(edits)
        (self.dir / 'giving-models-current.json').write_text(json.dumps(pointer), encoding='utf-8')
        return pointer

    def test_legacy_selection_and_explicit_override(self):
        self.assertEqual(gf.models()['schema_version'], 2)
        self.v2.unlink()
        self.assertEqual(gf.models()['schema_version'], 1)
        (self.dir / 'giving-models-current.json').write_text('broken', encoding='utf-8')
        with patch.dict(os.environ, {'MENTAT_GIVING_MODELS': str(self.v1)}):
            self.assertEqual(gf.models()['schema_version'], 1)

    def test_v1_rollback_wins_even_when_v2_remains(self):
        self.pointer(self.v2)
        self.assertEqual(gf.models()['schema_version'], 2)
        self.pointer(self.v1)
        self.assertTrue(self.v2.exists())
        self.assertEqual(gf.models()['schema_version'], 1)

    def test_pointer_selects_immutable_bytes_independent_of_compatibility_alias(self):
        digest = hashlib.sha256(self.v2.read_bytes()).hexdigest()
        target = self.dir / 'versions' / digest / self.v2.name
        target.parent.mkdir(parents=True)
        shutil.copyfile(self.v2, target)
        self.pointer(target)
        self.v2.write_text('incomplete compatibility alias', encoding='utf-8')
        self.assertEqual(gf.models()['model_version'], self.bundle['model_version'])

    def test_invalid_pointer_never_falls_back_to_an_existing_bundle(self):
        variants = [({'schema_version': 2}, 'pointer schema'), ({'schema_version': True}, 'pointer schema'),
                    ({'sha256': '0' * 64}, 'SHA-256'), ({'model_version': 'wrong'}, 'model version'),
                    ({'model_schema_version': 1}, 'model schema'), ({'active': '../giving-models-v2.json'}, 'active path'),
                    ({'active': str(self.v2)}, 'active path'), ({'active': 'versions/' + '0' * 64 + '/giving-models-v2.json'}, 'missing')]
        for edits, error in variants:
            with self.subTest(edits=edits):
                self.pointer(self.v2, **edits)
                with self.assertRaisesRegex(ValueError, error):
                    gf.models()
        for malformed in ('{', '[]', 'null'):
            (self.dir / 'giving-models-current.json').write_text(malformed, encoding='utf-8')
            with self.assertRaises(ValueError):
                gf.models()

    def test_pointer_checks_bundle_schema_and_revalidates_after_a_file_changes(self):
        self.pointer(self.v2)
        gf.models()
        self.v2.write_text(self.v2.read_text() + ' ', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            gf.models()
        shutil.copyfile(self.v1, self.v2)
        self.pointer(self.v2, model_schema_version=2)
        with self.assertRaisesRegex(ValueError, 'model schema'):
            gf.models()

    @unittest.skipUnless(shutil.which('Rscript'), 'Rscript required for actual publisher integration')
    def test_r_publisher_repeated_publish_failure_and_rollback(self):
        # Load only the publisher's dependencies: no raw-data refit or fitted fixture substitutes.
        refit = ROOT / 'forecast' / 'refit'
        source = self.dir / 'candidate.json'
        source.write_text(json.dumps(self.bundle), encoding='utf-8')
        script = self.dir / 'publish.R'
        script.write_text(r"""
args <- commandArgs(trailingOnly = TRUE)
assign('.RF_HOME', args[1], envir = globalenv())
Sys.setenv(RF_RUNTIME = file.path(args[2], 'runtime'))
for (f in c('rf_config.R', 'rf_io.R', 'rf_schema.R', 'rf_gates.R', 'rf_publish.R')) source(file.path(args[1], 'R', f))
b <- jsonlite::fromJSON(args[3], simplifyVector = FALSE)
gates <- data.frame(gate = 'publication integration', status = 'PASS', detail = '')
if (args[4] == 'publish') rf_publish(b, gates, dir = args[2])
if (args[4] == 'fail') {
  .rf_write_pointer <- function(...) stop('injected switch failure')
  tryCatch(rf_publish(b, gates, dir = args[2]), error = function(e) { cat(conditionMessage(e)); quit(status=3L) })
}
if (args[4] == 'rollback') rf_rollback(args[5], dir = args[2])
""", encoding='utf-8')
        def run(operation, version=''):
            return subprocess.run(['Rscript', str(script), str(refit), str(self.dir), str(source), operation, version],
                                  capture_output=True, text=True, timeout=60)
        # No pointer exists initially, so both producer and consumer correctly discover legacy v2.
        first = run('publish')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        original = gf.models()
        original_path = gf.model_path()
        self.assertIn('/versions/', original_path.as_posix())
        original_bytes = original_path.read_bytes()
        next_bundle = copy.deepcopy(self.bundle)
        next_bundle['model_version'] = 'refit-20261001-deadbeef'
        source.write_text(json.dumps(next_bundle), encoding='utf-8')
        failed = run('fail')
        self.assertEqual(failed.returncode, 3, failed.stdout + failed.stderr)
        self.assertEqual(gf.models()['model_version'], original['model_version'])
        self.assertEqual(original_path.read_bytes(), original_bytes)
        published = run('publish')
        self.assertEqual(published.returncode, 0, published.stdout + published.stderr)
        self.assertEqual(gf.models()['model_version'], next_bundle['model_version'])
        self.assertNotEqual(gf.model_path(), original_path)
        self.assertEqual(original_path.read_bytes(), original_bytes)
        back = run('rollback', original['model_version'])
        self.assertEqual(back.returncode, 0, back.stdout + back.stderr)
        self.assertEqual(gf.models()['model_version'], original['model_version'])
        back_v1 = run('rollback', json.loads(self.v1.read_text())['model_version'])
        self.assertEqual(back_v1.returncode, 0, back_v1.stdout + back_v1.stderr)
        self.assertEqual(gf.models()['schema_version'], 1)
        self.assertTrue(self.v2.exists())


if __name__ == '__main__':
    unittest.main()
