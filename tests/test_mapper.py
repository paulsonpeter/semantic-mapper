import tempfile
import unittest
from pathlib import Path
import mapper


class MapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.db"
        mapper.initialize(self.path)

    def test_normalized_match_and_unknown(self):
        rows = mapper.match(["  NOISE   from wheel!!! ", "rattling from tyre", "my wheel is noisy"], self.path)
        self.assertEqual([r["concept"] for r in rows], ["WHEEL_NOISE", "WHEEL_NOISE", "UNMAPPED"])
        self.assertEqual(rows[1]["detail"], "RATTLING")

    def test_deletion_survives_restart(self):
        row = mapper.mappings(self.path)[0]
        mapper.delete_mapping(row["id"], self.path)
        mapper.initialize(self.path)
        self.assertEqual(mapper.match([row["phrase"]], self.path)[0]["concept"], "UNMAPPED")

    def test_edit_and_restrict_concept_delete(self):
        row = mapper.mappings(self.path)[0]
        mapper.save_mapping("new phrase", "WHEEL_NOISE", "TEST", row["id"], self.path)
        self.assertEqual(mapper.match(["new phrase"], self.path)[0]["detail"], "TEST")
        with self.assertRaises(ValueError):
            mapper.delete_concept("WHEEL_NOISE", self.path)

    def test_csv_roundtrip_and_atomic_conflict(self):
        self.assertEqual(mapper.import_csv(mapper.export_csv(mapper.mappings(self.path)), self.path), 0)
        content = "phrase,concept,detail\nnew phrase,NEW_CONCEPT,\nnoise from wheel,OTHER_CONCEPT,\n"
        with self.assertRaises(ValueError):
            mapper.import_csv(content, self.path)
        self.assertNotIn("NEW_CONCEPT", mapper.concepts(self.path))
        self.assertEqual(mapper.match(["new phrase"], self.path)[0]["concept"], "UNMAPPED")

    def test_csv_new_and_duplicate(self):
        self.assertEqual(mapper.import_csv("phrase,concept,detail\nbrake squeal,BRAKE_NOISE,SQUEALING\n", self.path), 1)
        with self.assertRaises(ValueError):
            mapper.import_csv("phrase,concept,detail\nfoo,WHEEL_NOISE,\nFOO!,WHEEL_NOISE,\n", self.path)


if __name__ == "__main__":
    unittest.main()
