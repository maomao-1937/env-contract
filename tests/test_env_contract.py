import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'env_contract.py'


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def scan(self, source='', example='', extra=()):
        (self.root / 'app.py').write_text(source, encoding='utf-8')
        (self.root / '.env.example').write_text(example, encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root), '--example',
                                 str(self.root / '.env.example'), '--format', 'json', *extra],
                                capture_output=True, text=True)
        return result

    def test_help(self):
        self.assertEqual(subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True).returncode, 0)

    def test_aliases_and_defaults(self):
        p = self.scan('import os as sysos\nfrom os import getenv as ge, environ as env\n'
                      'a=sysos.getenv("A")\nb=ge("B", "fallback")\nc=env["C"]\nd=env.get("D", default="d")\n',
                      'A=\nB=\nC=\nD=\n')
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = {u['name']: u['classification'] for u in json.loads(p.stdout)['usages']}
        self.assertEqual(rows, {'A': 'optional', 'B': 'optional', 'C': 'required', 'D': 'optional'})

    def test_missing_and_example_only_names_no_values(self):
        p = self.scan('import os\nx=os.environ["NEEDED"]\n', 'UNUSED=synthetic-do-not-print\n')
        self.assertEqual(p.returncode, 1)
        report = json.loads(p.stdout)
        self.assertEqual(report['missing'], ['NEEDED'])
        self.assertEqual(report['example_only'], ['UNUSED'])
        self.assertNotIn('synthetic-do-not-print', p.stdout + p.stderr)

    def test_comments_strings_not_accesses(self):
        p = self.scan('# os.environ["NO"]\nx = \'os.getenv("NO")\'\n')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['usages'], [])

    def test_source_is_not_executed_or_modified(self):
        marker = self.root / 'must-not-exist.txt'
        source = 'from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\nraise RuntimeError("must not run")\n'
        p = self.scan(source)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.root / 'app.py').read_text(encoding='utf-8'), source)

    def test_dynamic_access_incomplete(self):
        p = self.scan('import os\nk="A"\nx=os.getenv(k)\n')
        self.assertEqual(p.returncode, 3)
        self.assertTrue(json.loads(p.stdout)['incomplete'])

    def test_dynamic_default_classification(self):
        p = self.scan('import os\nx=os.getenv("A", compute())\n', 'A=\n')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['usages'][0]['classification'], 'unknown')

    def test_syntax_error_incomplete_sanitized(self):
        p = self.scan('synthetic-private !!!')
        self.assertEqual(p.returncode, 3)
        self.assertNotIn('synthetic-private', p.stdout + p.stderr)

    def test_generated_and_env_trees_skipped(self):
        for directory in ('.git', '.venv', 'venv', 'node_modules', 'build', 'dist', '__pycache__'):
            path = self.root / directory
            path.mkdir()
            (path / 'bad.py').write_text('!!!', encoding='utf-8')
        self.assertEqual(self.scan().returncode, 0)

    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'outside.py'
            target.write_text('import os\nx=os.environ["OUTSIDE"]', encoding='utf-8')
            try:
                (self.root / 'linked.py').symlink_to(target)
            except OSError:
                self.skipTest('symlinks unavailable')
            self.assertEqual(self.scan().returncode, 0)

    def test_keyword_getenv(self):
        p = self.scan('import os\nx=os.getenv(key="A", default="x")\n', 'export A=synthetic\n')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['usages'][0]['name'], 'A')

    def test_invalid_example(self):
        p = self.scan('', 'not an assignment\n')
        self.assertEqual(p.returncode, 2)

    def test_invalid_root(self):
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.root / 'absent'), '--example', 'absent'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)

    def test_empty_or_skipped_only_root_is_incomplete(self):
        for skipped in (False, True):
            with self.subTest(skipped_only=skipped):
                root = self.root / ('skipped' if skipped else 'empty')
                root.mkdir()
                example = root / '.env.example'
                example.write_text('', encoding='utf-8')
                if skipped:
                    (root / '.venv').mkdir()
                    (root / '.venv' / 'app.py').write_text('x=1', encoding='utf-8')
                p = subprocess.run([sys.executable, str(SCRIPT), str(root), '--example', str(example), '--format', 'json'], capture_output=True, text=True)
                self.assertEqual(p.returncode, 3)
                report = json.loads(p.stdout)
                self.assertEqual(report['scanned_files'], 0)
                self.assertIn('no readable Python source files', [r['reason'] for r in report['incomplete']])

    def test_scanned_file_count(self):
        p = self.scan('x=1\n')
        self.assertEqual(json.loads(p.stdout)['scanned_files'], 1)

    def test_invalid_encoding_incomplete(self):
        (self.root / 'broken.py').write_bytes(b'\xff')
        self.assertEqual(self.scan().returncode, 3)

    def test_write_only_ignored(self):
        self.assertEqual(self.scan('import os\nos.environ["A"]="synthetic"\n').returncode, 0)

    def test_augmented_write_reads_required(self):
        p = self.scan('import os\nos.environ["A"] += "suffix"\n')
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)['usages'][0]['classification'], 'required')

    def test_unsupported_method_incomplete(self):
        self.assertEqual(self.scan('import os\nx=os.environ.pop("A")\n').returncode, 3)

    def test_duplicate_example_invalid(self):
        self.assertEqual(self.scan('', 'A=one\nA=two\n').returncode, 2)

    def test_dynamic_default_not_required(self):
        p = self.scan('from os import environ\nx=environ.get("A", compute())\n', 'A=\n')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['usages'][0]['classification'], 'unknown')


if __name__ == '__main__':
    unittest.main()
