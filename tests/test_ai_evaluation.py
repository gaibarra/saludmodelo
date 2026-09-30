"""Offline evaluation-tool tests; no database or provider access."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.evaluate_ai import bundle, corpus, digest, encoded, evaluate, fixture, unique_object


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = corpus()
        self.submission = {'corpus_sha256': digest(encoded(self.dataset)), 'origin': 'test double',
                           'results': {c['id']: fixture(c) for c in self.dataset['cases']}}

    def test_coverage_and_reproducibility(self):
        self.assertEqual(len(self.dataset['cases']), 54)
        self.assertEqual(len({c['unit'] for c in self.dataset['cases']}), 9)
        self.assertEqual(encoded(self.dataset), encoded(corpus()))
        inventory = json.loads(Path('imports/source-inventory.json').read_text())
        for case in self.dataset['cases']:
            self.assertIn(case['source_reference'], inventory)

    def test_provenance_is_not_semantic_accuracy(self):
        report = evaluate(self.dataset, self.submission, synthetic=True)
        self.assertEqual(report['contract_valid'], 45)
        self.assertEqual(report['human_reviews_completed'], 0)
        self.assertEqual(report['semantic_quality'], 'not_evaluated')
        self.assertTrue(all(r['fixture_expectation_met'] for r in report['results']))
        false_claims = [r for r in report['results'] if r['known_semantic_failure']]
        self.assertEqual(len(false_claims), 9)
        self.assertTrue(all(r['contract_valid'] for r in false_claims))

    def test_unknown_missing_and_wrong_corpus_fail_closed(self):
        for mutation in ('missing', 'extra', 'hash', 'origin'):
            candidate = copy.deepcopy(self.submission)
            if mutation == 'missing': candidate['results'].pop('OD01-missing')
            if mutation == 'extra': candidate['results']['unknown'] = {}
            if mutation == 'hash': candidate['corpus_sha256'] = '0' * 64
            if mutation == 'origin': candidate['origin'] = ''
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                evaluate(self.dataset, candidate)

    def test_corrupt_results_are_rejected_without_dumping_content(self):
        for value in (None, [], {}, {'secret': 'PRIVATE'}):
            candidate = copy.deepcopy(self.submission)
            candidate['results']['OD01-missing'] = value
            report = evaluate(self.dataset, candidate)
            self.assertFalse(report['results'][0]['contract_valid'])
            self.assertNotIn('PRIVATE', encoded(report).decode())
            self.assertNotIn('fixture_expectation_met', report['results'][0])

    def test_autoapproval_and_unbounded_questions_rejected(self):
        for field, value in (('requires_human_review', False), ('follow_up_questions', ['a', 'b', 'c'])):
            candidate = copy.deepcopy(self.submission)
            candidate['results']['OD01-missing'][field] = value
            self.assertFalse(evaluate(self.dataset, candidate)['results'][0]['contract_valid'])

    def test_bundle_integrity_permissions_and_preservation(self):
        with tempfile.TemporaryDirectory(prefix='salud-ai-eval-') as tmp:
            out = Path(tmp) / 'run'
            with patch('socket.socket', side_effect=AssertionError('No network')):
                bundle(out)
            manifest = json.loads((out / 'manifest.json').read_text())
            for name, sha in manifest.items():
                self.assertEqual(digest((out / name).read_bytes()), sha)
                self.assertEqual((out / name).stat().st_mode & 0o777, 0o600)
            self.assertEqual(out.stat().st_mode & 0o777, 0o700)
            review = out / 'human-review.csv'
            review.write_text('manual annotation')
            with self.assertRaises(FileExistsError): bundle(out)
            self.assertEqual(review.read_text(), 'manual annotation')
            external = bundle(Path(tmp) / 'external', out / 'outputs.json')
            self.assertEqual(external['mode'], 'supplied_outputs')
            self.assertEqual(external['human_reviews_completed'], 0)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"results":{},"results":{}}', object_pairs_hook=unique_object)

    def test_modified_source_stops_generation(self):
        with patch('tools.evaluate_ai.SOURCE') as source:
            source.read_bytes.return_value = b'changed'
            with self.assertRaises(ValueError): corpus()


if __name__ == '__main__':
    unittest.main()
