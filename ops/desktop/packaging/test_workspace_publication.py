import json
import unittest

from workspace_publication import PublicationProjection, assert_public_record


class ProjectionTests(unittest.TestCase):
    def test_auth_urls_and_headers_removed_without_modifying_ids_money_or_public_source(self):
        original = {'source_id': 'PUBLIC-FEC-FIXTURE', 'amount_cents': -1250, 'session': 119,
            'source_url': 'https://api.open.fec.gov/v1/records/?cycle=2026&api_key=fixture-private&sort=date',
            'request_headers': {'Authorization': 'Bearer fixture-private', 'Cookie': 'fixture-private'},
            'metadata': {'access_token': 'fixture-private', 'public': True}}
        projection = PublicationProjection()
        result = projection.record(original)
        self.assertEqual(result, {'source_id': 'PUBLIC-FEC-FIXTURE', 'amount_cents': -1250, 'session': 119,
            'source_url': 'https://api.open.fec.gov/v1/records/?cycle=2026&sort=date', 'metadata': {'public': True}})
        self.assertIn('request_headers', original)
        self.assertNotIn('fixture-private', json.dumps(result))
        self.assertNotIn('fixture-private', json.dumps(projection.receipt()))
        assert_public_record(result)
        with self.assertRaises(ValueError):
            assert_public_record(original)

    def test_local_provenance_keys_and_values_are_stable_opaque_ids_and_hash_mapped(self):
        original = {'sources': {r'C:\Users\recipient\data\facts.csv': 'a' * 64},
                    'source': r'C:\Users\recipient\data\facts.csv'}
        projection = PublicationProjection()
        result = projection.record(original)
        self.assertEqual(list(result['sources']), [result['source']])
        self.assertTrue(result['source'].startswith('workspace-source:'))
        self.assertNotIn('recipient', json.dumps(result))
        self.assertIn(original['source'], projection.receipt()['privateSourcePathMap'])
        assert_public_record(result)

    def test_encoded_query_names_userinfo_and_actual_unicode_placeholders_are_projected(self):
        projection = PublicationProjection()
        result = projection.record({'url': 'https://private:credential@example.org/source?id=1&%61pi_key=fixture&token=fixture',
                                    'title': 'S<U+00E1>nchez', 'label': 'mentat-pocket-scope-v1'})
        self.assertEqual(result['url'], 'https://example.org/source?id=1')
        self.assertEqual(result['title'], 'S\u00e1nchez')
        self.assertEqual(result['label'], 'mentat-pocket-scope-v1')
        assert_public_record(result)

    def test_fragment_and_signed_request_credentials_never_enter_public_receipts(self):
        projection = PublicationProjection()
        result = projection.record({'url': 'https://example.org/public?id=1&jwt=fixture-private#view=table&access_token=fixture-private'})
        self.assertEqual(result['url'], 'https://example.org/public?id=1#view=table')
        self.assertNotIn('fixture-private', json.dumps(projection.receipt()))
        assert_public_record(result)


if __name__ == '__main__':
    unittest.main()
