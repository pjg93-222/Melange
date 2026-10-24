"""The personal-texture catch-net publishes rows only for members on the current roster (the desk's key)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FEC = Path(__file__).resolve().parents[2]

PROBE = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import members.personal_texture_layer as ptl
docs = [{'member': 'Sitting Member', 'date': '2026-01-01', 'source': 'CREC', 'locator': 'a', 'url': '',
         'text': 'My father taught me to fish on the river every summer when I was a boy.'},
        {'member': 'Departed Member', 'date': '2026-01-01', 'source': 'CREC', 'locator': 'b', 'url': '',
         'text': 'My mother taught me to read the newspaper every morning when I was a girl.'}]
ptl.iter_docs = lambda: iter(docs)
print(json.dumps(sorted({row['member'] for row in ptl.extract()})))
'''


class PersonalTextureRosterScopeTests(unittest.TestCase):
    def test_departed_member_documents_are_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'data', 'engine'))
            with open(os.path.join(root, 'data', 'engine', 'congestion.json'), 'w', encoding='utf-8') as handle:
                json.dump([{'member': 'Sitting Member', 'bioguide': 'S1'}], handle)
            env = dict(os.environ, MONEYBALL_ROOT=root, PYTHONIOENCODING='utf-8')
            result = subprocess.run([sys.executable, '-c', PROBE, str(FEC)], capture_output=True, text=True,
                                    encoding='utf-8', env=env, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(json.loads(lines[-1]), ['Sitting Member'])
        self.assertIn('skipped 1 documents from 1 names outside the current roster (Departed Member)', result.stdout)


if __name__ == '__main__':
    unittest.main()
