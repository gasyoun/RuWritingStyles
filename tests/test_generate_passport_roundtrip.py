"""Round-trip tests for `rws generate-passport` (H1861).

`generate_style_passport` previously called a nonexistent ``provider.generate``
and crashed with ``AttributeError`` on EVERY provider (mock included), and the
manifest entry ``save_generated_style`` wrote omitted ``source_prompt`` — which
`tools/validate_project.py` requires to keep the ClaudeStyles <-> manifest sets
in sync.  These tests pin both fixes and round-trip the two H1861 passports
(lotman, meletinsky) through the same save/load machinery.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.generation import generate_style_passport, save_generated_style
from ruwritingstyles.providers import MockProvider
from ruwritingstyles.yaml_lite import parse_simple_yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

SEED_MANIFEST = """version: "0.0"
passports:
  - id: seed
    path: styles/passports/seed.yml
    level: private
    cluster: ling_nss
    source_prompt: ClaudeStyles/seed-style.md
"""


def _make_tmp_repo(tmp: Path) -> Path:
    (tmp / "styles" / "passports").mkdir(parents=True)
    (tmp / "ClaudeStyles").mkdir()
    (tmp / "styles" / "manifest.yml").write_text(SEED_MANIFEST, encoding="utf-8")
    return tmp


class GeneratePassportMockProviderTests(unittest.TestCase):
    def test_generate_style_passport_works_with_mock_provider(self) -> None:
        result = generate_style_passport(
            repo_root=REPO_ROOT,
            provider=MockProvider(),
            model=None,
            style_name="Тестовый стиль",
            description="проверка офлайн-генерации",
        )
        for key in ("passport_id", "passport_yaml", "source_prompt_md"):
            self.assertTrue(result.get(key), f"missing {key!r} in generation result")

    def test_save_generated_style_round_trips_mock_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_tmp_repo(Path(tmp))
            result = generate_style_passport(
                repo_root=repo,
                provider=MockProvider(),
                model=None,
                style_name="Тестовый стиль",
                description="проверка офлайн-генерации",
            )
            passport_id = save_generated_style(repo, result)
            passport_path = repo / "styles" / "passports" / f"{passport_id}.yml"
            prompt_path = repo / "ClaudeStyles" / f"{passport_id}-style.md"
            self.assertTrue(passport_path.exists())
            self.assertTrue(prompt_path.exists())
            manifest_text = (repo / "styles" / "manifest.yml").read_text(encoding="utf-8")
            self.assertIn(f"id: {passport_id}", manifest_text)
            self.assertIn(
                f"source_prompt: ClaudeStyles/{passport_id}-style.md", manifest_text
            )
            parsed = parse_simple_yaml(passport_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed.get("id"), passport_id)


class H1861PassportRoundTripTests(unittest.TestCase):
    """The two real H1861 passports round-trip through the save/load machinery."""

    PASSPORT_IDS = ("lotman", "meletinsky")

    def test_real_passports_round_trip_through_save_generated_style(self) -> None:
        for passport_id in self.PASSPORT_IDS:
            with self.subTest(passport_id=passport_id):
                passport_yaml = (
                    REPO_ROOT / "styles" / "passports" / f"{passport_id}.yml"
                ).read_text(encoding="utf-8")
                source_prompt_md = (
                    REPO_ROOT / "ClaudeStyles" / f"{passport_id}-style.md"
                ).read_text(encoding="utf-8")
                parsed_source = parse_simple_yaml(passport_yaml)

                with tempfile.TemporaryDirectory() as tmp:
                    repo = _make_tmp_repo(Path(tmp))
                    saved_id = save_generated_style(
                        repo,
                        {
                            "passport_id": passport_id,
                            "cluster_id": parsed_source["cluster"],
                            "passport_yaml": passport_yaml,
                            "source_prompt_md": source_prompt_md,
                        },
                    )
                    self.assertEqual(saved_id, passport_id)
                    written = (
                        repo / "styles" / "passports" / f"{passport_id}.yml"
                    ).read_text(encoding="utf-8")
                    self.assertEqual(written, passport_yaml)
                    reparsed = parse_simple_yaml(written)
                    self.assertEqual(reparsed, parsed_source)
                    manifest_text = (repo / "styles" / "manifest.yml").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn(
                        f"source_prompt: ClaudeStyles/{passport_id}-style.md",
                        manifest_text,
                    )

    def test_real_passports_parse_with_expected_identity(self) -> None:
        expected_clusters = {"lotman": "lit_structural", "meletinsky": "lit_mythopoetics"}
        for passport_id, cluster in expected_clusters.items():
            with self.subTest(passport_id=passport_id):
                parsed = parse_simple_yaml(
                    (
                        REPO_ROOT / "styles" / "passports" / f"{passport_id}.yml"
                    ).read_text(encoding="utf-8")
                )
                self.assertEqual(parsed["id"], passport_id)
                self.assertEqual(parsed["cluster"], cluster)
                self.assertEqual(
                    parsed["source_prompt"], f"ClaudeStyles/{passport_id}-style.md"
                )


if __name__ == "__main__":
    unittest.main()
