"""POST /runs/execute text-body intake (Tier 2 — editor clients submit the note
body, not a server-side path)."""

import os
import shutil
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ruwritingstyles import api

REPO_ROOT = Path(__file__).resolve().parents[1]


class TextIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = api._API_TOKEN
        api._API_TOKEN = ""  # isolate from the auth middleware
        os.environ["RWS_OFFLINE"] = "1"
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        api._API_TOKEN = self._saved

    def _cleanup(self, run_id: str) -> None:
        self.addCleanup(shutil.rmtree, REPO_ROOT / "runs" / run_id, ignore_errors=True)

    def test_text_body_prepares_a_run_without_a_file(self) -> None:
        body = "# Заметка\n\nВеда упоминается без транслитерации.\n"
        resp = self.client.post(
            "/runs/execute",
            json={"text": body, "filename": "my-note.md", "execute": False},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        run_id = resp.json()["run_id"]
        self._cleanup(run_id)
        # The submitted body becomes the run's document verbatim.
        original = (REPO_ROOT / "runs" / run_id / "original.md").read_text(encoding="utf-8")
        self.assertEqual(original, body)
        # The filename labels the run id.
        self.assertIn("my-note", run_id)

    def test_missing_both_text_and_path_is_400(self) -> None:
        resp = self.client.post("/runs/execute", json={"execute": False})
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_oversized_text_is_413(self) -> None:
        os.environ["RWS_MAX_TEXT_CHARS"] = "100"
        try:
            resp = self.client.post(
                "/runs/execute", json={"text": "x" * 101, "execute": False}
            )
            self.assertEqual(resp.status_code, 413, resp.text)
        finally:
            del os.environ["RWS_MAX_TEXT_CHARS"]

    def test_journal_preset_is_written_into_the_run(self) -> None:
        import json

        resp = self.client.post(
            "/runs/execute",
            json={"text": "# T\n\nтекст", "journal": "vestnik-spbu", "execute": False},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        run_id = resp.json()["run_id"]
        self._cleanup(run_id)
        ctx = json.loads(
            (REPO_ROOT / "runs" / run_id / "project-context.json").read_text(encoding="utf-8")
        )
        self.assertEqual(ctx["journal_profile"]["id"], "vestnik-spbu")

    def test_unknown_journal_is_400(self) -> None:
        resp = self.client.post(
            "/runs/execute",
            json={"text": "hi", "journal": "no-such-journal", "execute": False},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_text_filename_directory_parts_are_stripped(self) -> None:
        # A path-like filename must not escape runs/ — only the basename is used.
        resp = self.client.post(
            "/runs/execute",
            json={"text": "hi", "filename": "../../etc/passwd", "execute": False},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        run_id = resp.json()["run_id"]
        self._cleanup(run_id)
        self.assertIn("passwd", run_id)  # slug of the basename, not a traversal


if __name__ == "__main__":
    unittest.main()
