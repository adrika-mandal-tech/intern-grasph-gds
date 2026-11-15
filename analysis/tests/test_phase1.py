"""Offline regression tests. All temporary files stay inside this workspace."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pull_cache as cache
from grasph_client import Truncated
spec = importlib.util.spec_from_file_location('profile_task', ROOT / 'tasks' / 'task01_profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class FakeGrasph:
    base = 'http://127.0.0.1:7475'

    def __init__(self):
        self.pulls = 0
        self.truncated = False
        self.bad_endpoint = False
        self.wrong_count = False

    def status(self):
        return {'node_count': 568960, 'relationship_count': 774266}

    def schema(self, namespace):
        return {'node_schemas': [{'label': 'Seller', 'properties': [{'name': 'seller_id'}, {'name': 'vector'}]}],
                'rel_schemas': [{'rel_type': 'PEER', 'from_label': 'Seller', 'to_label': 'Seller'}]}

    def query(self, q):
        if 'count(' in q:
            return {'rows': [[99 if self.wrong_count else (1 if '[r:' in q else 2)]]}
        if self.truncated:
            raise Truncated('fixture: cap before filter')
        self.pulls += 1
        if 'RETURN r' in q:
            return {'rows': [[{'id': 3, 'from': 1, 'to': 99 if self.bad_endpoint else 2, 'properties': {}}]]}
        if 'vector' in q:
            raise AssertionError('Vectors must not travel')
        return {'rows': [[1, 'a'], [2, 'b']]}


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.path = Path(self.temp.name)
        self.pn = patch.object(cache, 'EXPECTED_NODES', {'Seller': 2})
        self.pr = patch.object(cache, 'EXPECTED_RELS', {'PEER': 1})
        self.pn.start()
        self.pr.start()

    def tearDown(self):
        self.pn.stop()
        self.pr.stop()
        self.temp.cleanup()

    def test_pull_roundtrip_resume_excludes_vectors(self):
        g = FakeGrasph()
        result = cache.pull(g, self.path)
        self.assertTrue(result['complete'])
        self.assertEqual(g.pulls, 2)
        result = cache.pull(g, self.path)
        self.assertEqual(g.pulls, 2)
        self.assertTrue(all(t['reused'] for t in result['tables'].values()))

    def test_truncation_never_committed(self):
        g = FakeGrasph()
        g.truncated = True
        with self.assertRaises(Truncated):
            cache.pull(g, self.path)
        self.assertFalse(json.loads((self.path / 'manifest.json').read_text())['complete'])
        self.assertFalse(list(self.path.glob('*.jsonl.gz')))

    def test_corruption_rejected(self):
        g = FakeGrasph()
        cache.pull(g, self.path)
        (self.path / 'nodes_Seller.jsonl.gz').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'corrupt'):
            cache.pull(g, self.path)

    def test_wrong_source_rejected(self):
        g = FakeGrasph()
        cache.pull(g, self.path)
        g.base = 'http://127.0.0.1:9999'
        with self.assertRaisesRegex(ValueError, 'provenance'):
            cache.pull(g, self.path)

    def test_orphan_rejected(self):
        g = FakeGrasph()
        g.bad_endpoint = True
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            cache.pull(g, self.path)
        self.assertFalse(json.loads((self.path / 'manifest.json').read_text())['complete'])

    def test_count_mismatch_rejected(self):
        g = FakeGrasph()
        g.wrong_count = True
        with self.assertRaisesRegex(ValueError, 'manual'):
            cache.pull(g, self.path)
        self.assertEqual(g.pulls, 0)

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            cache.validate_rows([{'_id': 1}, {'_id': 1}], 2, '_id')

    def test_identifier_validation(self):
        self.assertEqual(cache.ident('OrderItem'), 'OrderItem')
        with self.assertRaises(ValueError):
            cache.ident('Seller) DELETE n')


class ProfileTests(unittest.TestCase):
    def test_zip(self):
        for v in ['01037', 1037, '1037.0']:
            self.assertEqual(profile.norm_zip(v), '01037')
        for v in [None, '', 'junk', 'nan', -1, 1.5]:
            self.assertIsNone(profile.norm_zip(v))

    def test_dates(self):
        self.assertIsNone(profile.parse_date('bad'))
        self.assertIsNone(profile.parse_date(''))
        self.assertEqual(profile.parse_date('2018-06-01 00:00:00').year, 2018)

    def test_distribution(self):
        self.assertEqual(profile.distribution([]), {'n': 0})
        self.assertEqual(profile.distribution([1, 3])['median'], 2)

    def test_concentration_denominator(self):
        c = profile.concentration([10, 0, 0, 0])
        self.assertEqual(c['entities'], 4)
        self.assertEqual(c['items'], 10)
        self.assertEqual(c['top_one_percent_share'], 1)


if __name__ == '__main__':
    unittest.main()
