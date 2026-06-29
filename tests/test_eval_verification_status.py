import json
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.evals import _ensure_verification_status


class EnsureVerificationStatusTests(unittest.TestCase):
    """Regression guard for the gold-eval `verification_status: missing` bug.

    A timed-out/failed verify stage, or the fact-checking loop's bare
    `{"warnings": [...]}` between-iteration overwrite, could leave
    verification.json without a `status`. `_write_eval_result` then defaulted
    the status to "missing" (an unscoreable plumbing artifact) or the case
    crashed before the result was written. `_ensure_verification_status` repairs
    a status-less doc to an honest `needs_human_review` verdict.
    """

    def _path(self) -> Path:
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        return Path(d) / "verification.json"

    def test_statusless_doc_is_repaired(self):
        p = self._path()
        p.write_text(json.dumps({"summary": "x"}), encoding="utf-8")
        _ensure_verification_status(p, note="verify stage did not complete: Timeout")
        doc = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "needs_human_review")
        self.assertIn("verify stage did not complete: Timeout", doc["warnings"])

    def test_bare_warnings_overwrite_gets_status(self):
        # The exact between-iteration state the loop writes (no status key).
        p = self._path()
        p.write_text(json.dumps({"warnings": ["earlier warning"]}), encoding="utf-8")
        _ensure_verification_status(p)
        doc = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "needs_human_review")
        # Pre-existing warnings are preserved, the repair note is appended.
        self.assertIn("earlier warning", doc["warnings"])
        self.assertEqual(len(doc["warnings"]), 2)

    def test_existing_status_is_untouched(self):
        p = self._path()
        original = {"status": "passed", "warnings": []}
        p.write_text(json.dumps(original), encoding="utf-8")
        _ensure_verification_status(p, note="should not be added")
        doc = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "passed")
        self.assertEqual(doc["warnings"], [])

    def test_blank_status_is_repaired(self):
        p = self._path()
        p.write_text(json.dumps({"status": "  "}), encoding="utf-8")
        _ensure_verification_status(p)
        doc = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "needs_human_review")

    def test_missing_file_is_created(self):
        p = self._path()
        self.assertFalse(p.exists())
        _ensure_verification_status(p, note="no file")
        doc = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "needs_human_review")

    def test_malformed_json_is_repaired(self):
        p = self._path()
        p.write_text("{not valid json", encoding="utf-8")
        _ensure_verification_status(p)
        doc = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "needs_human_review")


if __name__ == "__main__":
    unittest.main()
