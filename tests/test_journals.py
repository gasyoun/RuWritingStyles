import json
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.journals import list_journal_presets, load_journal_preset
from ruwritingstyles.project import (
    load_project_context,
    resolve_journal_profile,
    set_journal_profile,
    update_project_context,
)
from ruwritingstyles.translit_lint import lint_text

REPO_ROOT = Path(__file__).resolve().parents[1]

VYA = {
    "id": "vya",
    "name": "Вопросы языкознания",
    "max_chars": 40000,
    "citation_format": "GOST-R-7.0.100-2018",
    "transliteration_scheme": "IAST",
    "first_mention_rule": "ru+iast",
    # The D10 gate refuses unverified profiles on attach; this fixture stands
    # for the hand-verified repo presets (which carry verified: true).
    "verified": True,
}

TERMS = [
    {"ru": "бхашья", "iast": "bhāṣya"},
    {"ru": "самаса", "iast": "samāsa"},
]


class PresetLoadingTests(unittest.TestCase):
    def test_repo_presets_are_listed(self) -> None:
        ids = list_journal_presets(REPO_ROOT)
        self.assertIn("vya", ids)
        self.assertIn("ppv", ids)
        self.assertIn("vestnik-spbu", ids)

    def test_load_known_preset(self) -> None:
        preset = load_journal_preset(REPO_ROOT, "vya")
        self.assertIsNotNone(preset)
        self.assertEqual(preset["name"], "Вопросы языкознания")
        self.assertEqual(preset["citation_format"], "author-year-brackets")

    def test_unknown_preset_returns_none(self) -> None:
        self.assertIsNone(load_journal_preset(REPO_ROOT, "no-such-journal"))


class ProjectContextTests(unittest.TestCase):
    def test_set_journal_profile_creates_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / ".rws-project"
            path = set_journal_profile(project_dir, VYA)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["journal_profile"]["id"], "vya")
            self.assertIn("stylistic_commitments", data)

    def test_set_journal_preserves_existing_commitments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / ".rws-project"
            project_dir.mkdir(parents=True)
            (project_dir / "project-context.json").write_text(
                json.dumps({"stylistic_commitments": [{"term": "идиом", "decision": "Use it."}]}),
                encoding="utf-8",
            )
            set_journal_profile(project_dir, VYA)
            data = json.loads((project_dir / "project-context.json").read_text(encoding="utf-8"))
            self.assertEqual(len(data["stylistic_commitments"]), 1)
            self.assertEqual(data["journal_profile"]["id"], "vya")

    def test_update_context_preserves_journal_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            set_journal_profile(project_dir, VYA)
            run_dir = project_dir / "run-1"
            run_dir.mkdir()
            (run_dir / "council.json").write_text(
                json.dumps({"stylistic_commitments": [{"term": "самаса", "decision": "Keep."}]}),
                encoding="utf-8",
            )
            update_project_context(project_dir, run_dir)
            data = json.loads((project_dir / "project-context.json").read_text(encoding="utf-8"))
            self.assertEqual(data["journal_profile"]["id"], "vya")
            self.assertEqual(len(data["stylistic_commitments"]), 1)

    def test_resolve_profile_prefers_run_dir_then_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "r1"
            run_dir.mkdir(parents=True)
            # parent-level context
            (run_dir.parent / "project-context.json").write_text(
                json.dumps({"journal_profile": {"id": "ppv", "name": "ППВ"}}), encoding="utf-8"
            )
            self.assertEqual(resolve_journal_profile(run_dir)["id"], "ppv")
            # run-level context wins
            (run_dir / "project-context.json").write_text(
                json.dumps({"journal_profile": VYA}), encoding="utf-8"
            )
            self.assertEqual(resolve_journal_profile(run_dir)["id"], "vya")

    def test_load_context_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_project_context(Path(tmp)), {})


class LinterProfileTests(unittest.TestCase):
    def test_first_mention_required_by_default(self) -> None:
        text = "Жанр бхашьи сложился рано."
        result = lint_text(text, TERMS)
        self.assertIn(
            "missing_iast_on_first_mention", [f["type"] for f in result["findings"]]
        )

    def test_ru_only_profile_suppresses_first_mention(self) -> None:
        text = "Жанр бхашьи сложился рано."
        profile = {"id": "x", "name": "X", "first_mention_rule": "ru-only"}
        result = lint_text(text, TERMS, profile)
        self.assertNotIn(
            "missing_iast_on_first_mention", [f["type"] for f in result["findings"]]
        )


if __name__ == "__main__":
    unittest.main()
