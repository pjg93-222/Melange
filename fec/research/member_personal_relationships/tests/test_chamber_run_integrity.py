"""Verify the completed v6 experiment without refitting or inspecting test labels."""
from collections import Counter
import unittest
import numpy as np
from fec.research.member_personal_relationships.data import ROOT, read_json, digest
from fec.research.member_personal_relationships.run_history import read_rows
from fec.research.member_personal_relationships.run_chamber_degrees import (
    OUT, FROZEN, HISTORY, verify_prepared)
from fec.research.member_personal_relationships.chamber_work import chamber_at


class CompletedRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_rows(OUT / 'annotations.ndjson')
        cls.results = read_json(OUT / 'model_results.json')
        cls.assignment = read_json(FROZEN / 'member_assignment.json')

    def test_frozen_inputs_and_result_receipts(self):
        manifest = verify_prepared()
        self.assertFalse(manifest['test_outcomes_used'])
        receipt = read_json(OUT / 'run_receipt.json')
        self.assertEqual(receipt['prefit_manifest_sha256'], digest(OUT / 'prefit_manifest.json'))
        for path, expected in receipt['results_sha256'].items():
            self.assertEqual(digest(ROOT / path), expected)
        for path, expected in read_json(OUT / 'report_receipt.json')['files_sha256'].items():
            self.assertEqual(digest(OUT / path), expected)

    def test_development_members_and_axis_missingness(self):
        self.assertEqual(len(self.rows), 73)
        self.assertEqual(len({r['id'] for r in self.rows}), 73)
        self.assertEqual(len({tuple(sorted(r['pair'])) for r in self.rows}), 64)
        for row in self.rows:
            for member in row['pair']:
                self.assertEqual(self.assignment[member]['split'], 'development')
            for axis in ('affinity', 'friction'):
                if row[axis] is None:
                    self.assertIsNone(row[axis + '_range'])
                else:
                    low, high = row[axis + '_range']
                    self.assertLessEqual(low, row[axis])
                    self.assertLessEqual(row[axis], high)
            if row['display'] == 'supported_neutral':
                self.assertTrue(row['neutral_evidence'])
                self.assertEqual((row['affinity'], row['friction']), (0, 0))
        self.assertEqual(sum(r['affinity'] is not None for r in self.rows), 35)
        self.assertEqual(sum(r['friction'] is not None for r in self.rows), 12)

    def test_every_fold_purges_members_and_transitive_source_families(self):
        by_id = {r['id']: r for r in self.rows}
        for model in self.results.values():
            for axis, fit in model.items():
                for prediction in fit['predictions']:
                    held = by_id[prediction['id']]
                    endpoints = set(held['pair'])
                    excluded = {i for i, r in enumerate(self.rows) if endpoints & set(r['pair'])}
                    # Independent fixed-point check, including unassessed source bridges.
                    while True:
                        families = {f for i in excluded for f in self.rows[i]['families']}
                        additions = {i for i, r in enumerate(self.rows) if families & set(r['families'])}
                        if additions <= excluded:
                            break
                        excluded |= additions
                    expected = [i for i, r in enumerate(self.rows) if i not in excluded and r[axis] is not None]
                    self.assertEqual(prediction['train_indices'], expected)
                    self.assertEqual(prediction['train_observed_grades'], sorted({self.rows[i][axis] for i in expected}))

    def test_predictions_and_independently_recomputed_scores(self):
        for model in self.results.values():
            for fit in model.values():
                predictions = fit['predictions']
                p = np.array([r['probability_by_grade'] for r in predictions])
                y = np.array([r['observed_grade'] for r in predictions])
                counts = Counter(tuple(sorted(r['pair'])) for r in predictions)
                w = np.array([1 / counts[tuple(sorted(r['pair']))] for r in predictions])
                self.assertTrue(np.isfinite(p).all())
                self.assertTrue((p >= 0).all())
                np.testing.assert_allclose(p.sum(axis=1), 1, atol=1e-12)
                ll = np.average(-np.log(np.maximum(p[np.arange(len(y)), y], 1e-15)), weights=w)
                mae = np.average(np.abs(p @ np.arange(5) - y), weights=w)
                rps = np.average(np.mean((p.cumsum(axis=1)[:, :4] - (y[:, None] <= np.arange(4))) ** 2, axis=1), weights=w)
                for key, value in [('ordinal_log_loss', ll), ('mean_absolute_grade_error', mae), ('ranked_probability_score', rps)]:
                    self.assertAlmostEqual(fit['metrics'][key], value, places=12)
                self.assertLess(fit['max_gradient_norm'], 2e-6)
                self.assertTrue((np.diff(fit['full_development_model']['cutpoints']) > 0).all())

    def test_dated_chambers_work_and_output_unknowns(self):
        members = read_json(HISTORY / 'members.json')
        features = read_json(OUT / 'features.json')
        profiles = {r['id']: r for r in read_rows(OUT / 'dated_relationship_profiles.ndjson')}
        for row in self.rows:
            self.assertEqual(row['chamber'], chamber_at(members, row['actor'], row['target'], row['date']))
            work = features[row['id']]
            if row['chamber'] == 'cross_chamber' or row['date'] < '2019-01-03':
                self.assertIsNone(work['shared_original_bills'])
                self.assertIsNone(work['direct_propensity'])
            for axis in ('affinity', 'friction'):
                self.assertEqual(profiles[row['id']][axis], row[axis])
                if row[axis] is None:
                    self.assertIsNone(profiles[row['id']]['development_predictions'][axis])
        snapshots = read_json(OUT / 'work_audit.json')['snapshots']
        for chamber in ('House', 'Senate'):
            points = sorted((r['before'], r['bill_count']) for r in snapshots if r['chamber'] == chamber)
            self.assertTrue(all(b[1] >= a[1] for a, b in zip(points, points[1:])))

    def test_routine_reviews_are_complete_and_do_not_manufacture_labels(self):
        candidates = read_rows(OUT / 'routine_encounter_candidates.ndjson')
        reviewed = read_rows(OUT / 'routine_reviewed.ndjson')
        self.assertEqual(len(reviewed), 23)
        self.assertEqual({r['source_rowid'] for r in reviewed}, {r['source_rowid'] for r in candidates})
        for row in reviewed:
            self.assertFalse(row['use_as_relationship_label'])
            self.assertFalse(row['neutral_evidence'])
            self.assertIsNone(row['affinity'])
            self.assertIsNone(row['friction'])
            for member in row['pair']:
                self.assertEqual(self.assignment[member]['split'], 'development')
        audit = read_json(OUT / 'routine_retrieval_audit.json')
        self.assertEqual(audit['queried_development_pairs'], 180)
        self.assertTrue(all(r['no_match_is_unknown'] and not r['relationship_label_assigned'] for r in audit['pair_results']))


if __name__ == '__main__':
    unittest.main()
