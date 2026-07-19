from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from ruwritingstyles.config import load_manifest, load_model_policy
from ruwritingstyles.runs import create_prepare_run, make_run_id


REPO_ROOT = Path(__file__).resolve().parents[1]


class RunIdTests(unittest.TestCase):
    def test_same_timestamp_and_filename_produce_distinct_ids(self) -> None:
        fixed = datetime(2026, 7, 19, 12, 34, 56, 123456, tzinfo=timezone.utc)
        first = make_run_id(Path("same.md"), fixed)
        second = make_run_id(Path("same.md"), fixed)
        self.assertNotEqual(first, second)
        self.assertRegex(first, r"^20260719-123456-123456-same-[0-9a-f]{8}$")

    def test_suffix_can_be_fixed_for_deterministic_callers(self) -> None:
        fixed = datetime(2026, 7, 19, 12, 34, 56, 123456, tzinfo=timezone.utc)
        self.assertEqual(
            make_run_id(Path("My Note.md"), fixed, "deadbeef"),
            "20260719-123456-123456-my-note-deadbeef",
        )

    def test_explicit_run_id_and_collision_behavior_are_preserved(self) -> None:
        manifest = load_manifest(REPO_ROOT)
        policy = load_model_policy(REPO_ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kwargs = dict(
                repo_root=root,
                input_path=Path("note.md"),
                original_text="text",
                normalized_text="text",
                segments=[],
                manifest=manifest,
                model_policy=policy,
                run_id="explicit-id",
            )
            run_dir = create_prepare_run(**kwargs)
            self.assertEqual(run_dir.name, "explicit-id")
            with self.assertRaises(FileExistsError):
                create_prepare_run(**kwargs)


if __name__ == "__main__":
    unittest.main()
