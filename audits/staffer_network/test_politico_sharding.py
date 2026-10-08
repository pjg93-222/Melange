"""Pure local tests: sharding never reads or writes crawl data."""

import hashlib
import unittest
import uuid

from audits.staffer_network.politico_sharding import shard_for_uuid


class PoliticoShardingTests(unittest.TestCase):
    def test_sha256_assignment_is_deterministic(self):
        profile_uuid = "b40ed594-ee63-4f9e-a00b-052c4a512056"
        expected = int.from_bytes(hashlib.sha256(profile_uuid.encode("utf-8")).digest(), "big") % 8
        self.assertEqual([shard_for_uuid(profile_uuid, 8) for _ in range(10)], [expected] * 10)
        self.assertEqual(shard_for_uuid("  " + profile_uuid.upper() + "  ", 8), expected)

    def test_eighteen_thousand_uuid_conservation(self):
        identifiers = {str(uuid.UUID(int=index)) for index in range(18_000)}
        shards = [set() for _ in range(8)]
        for profile_uuid in identifiers:
            shard = shard_for_uuid(profile_uuid, 8)
            self.assertGreaterEqual(shard, 0)
            self.assertLess(shard, 8)
            shards[shard].add(profile_uuid)
        self.assertTrue(all(shards), "All eight buckets should receive work")
        self.assertEqual(sum(map(len, shards)), len(identifiers))
        self.assertEqual(set.union(*shards), identifiers)
        for profile_uuid in identifiers:
            self.assertEqual(sum(profile_uuid in shard for shard in shards), 1)

    def test_valid_worker_counts(self):
        for workers in range(1, 9):
            with self.subTest(workers=workers):
                self.assertIn(shard_for_uuid(str(uuid.UUID(int=123)), workers), range(workers))
        self.assertEqual(shard_for_uuid(str(uuid.UUID(int=123)), 1), 0)

    def test_invalid_worker_counts(self):
        for workers in (0, -1, 9, 100, 1.0, "8", None, True, False):
            with self.subTest(workers=workers):
                with self.assertRaises(ValueError):
                    shard_for_uuid("example-uuid", workers)

    def test_blank_or_non_string_uuid(self):
        for profile_uuid in ("", " ", "\n\t", None, 123, b"uuid"):
            with self.subTest(profile_uuid=profile_uuid):
                with self.assertRaises(ValueError):
                    shard_for_uuid(profile_uuid, 8)


if __name__ == "__main__":
    unittest.main()
