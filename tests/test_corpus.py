import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.corpus import CorpusManager
from ruwritingstyles.db import Database

SAMPLE = (
    "A tatpurusa compound is analysed by vigraha.\n\n"
    "A bahuvrihi compound refers to something outside itself.\n\n"
    "The dvandva joins coordinate members.\n"
)


class CorpusManagerTests(unittest.TestCase):
    def _manager(self, tmp: Path) -> CorpusManager:
        Database(tmp)  # creates corpus_metadata + corpus_segments (FTS5)
        corpus_dir = tmp / "corpus"
        corpus_dir.mkdir()
        (corpus_dir / "Tubb_2007.txt").write_text(SAMPLE, encoding="utf-8")
        cm = CorpusManager(tmp)
        cm.corpus_dir = corpus_dir
        return cm

    def test_ingest_then_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cm = self._manager(Path(tmp))
            cm.ingest_all()
            hits = cm.search("vigraha")
            self.assertTrue(hits)
            self.assertIn("vigraha", hits[0]["snippet"].lower())
            self.assertTrue(hits[0]["file"].endswith("Tubb_2007.txt"))

    def test_search_or_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cm = self._manager(Path(tmp))
            cm.ingest_all()
            hits = cm.search("bahuvrihi OR dvandva", limit=5)
            self.assertGreaterEqual(len(hits), 2)

    def test_stats_reports_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cm = self._manager(Path(tmp))
            before = cm.stats()
            self.assertEqual(before["indexed_files"], 0)
            self.assertEqual(before["available_txt"], ["Tubb_2007.txt"])
            cm.ingest_all()
            after = cm.stats()
            self.assertEqual(after["indexed_files"], 1)
            self.assertEqual(after["indexed_segments"], 3)

    def test_ingest_is_idempotent_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cm = self._manager(Path(tmp))
            cm.ingest_all()
            cm.ingest_all()  # second pass skips already-indexed
            self.assertEqual(cm.stats()["indexed_segments"], 3)


if __name__ == "__main__":
    unittest.main()
