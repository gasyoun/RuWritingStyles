"""CLI run artifact parity tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ruwritingstyles.cli import build_parser, cmd_run


class CliReportArtifactTests(unittest.TestCase):
    def _repo_fixture(self, root: Path) -> None:
        (root / "README.md").write_text("# fixture\n", encoding="utf-8")
        (root / "ClaudeStyles").mkdir()
        (root / "styles" / "passports").mkdir(parents=True)
        (root / "styles" / "prompts").mkdir(parents=True)
        (root / "knowledge").mkdir()

        (root / "styles" / "manifest.yml").write_text(
            """
mvp_style_ids:
  - fixture-style
clusters: []
passports:
  - id: fixture-style
    path: styles/passports/fixture-style.yml
    source_prompt: styles/prompts/fixture-style.md
""".lstrip(),
            encoding="utf-8",
        )
        (root / "styles" / "passports" / "fixture-style.yml").write_text(
            "id: fixture-style\nname: Fixture Style\nrole: Test reviewer\n",
            encoding="utf-8",
        )
        (root / "styles" / "prompts" / "fixture-style.md").write_text(
            "Review fixture text conservatively.\n", encoding="utf-8"
        )
        (root / "model_policy.yml").write_text(
            """
default_provider: mock
default_development_mode:
  model: mock
  reasoning: low
  speed: fast
""".lstrip(),
            encoding="utf-8",
        )
        (root / "knowledge" / "bibliography.json").write_text(
            json.dumps(
                [
                    {
                        "id": "Zaliznyak 2004",
                        "author": "Зализняк А. А.",
                        "year": 2004,
                        "title": "Древненовгородский диалект",
                        "kind": "book",
                        "city": "М.",
                        "publisher": "Языки славянской культуры",
                        "pages": "872",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_run_writes_cli_and_scholarly_report_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo_fixture(root)
            input_path = root / "input.md"
            input_path.write_text("# Текст\n\nСр. (Zaliznyak 2004).\n", encoding="utf-8")

            args = build_parser().parse_args(
                [
                    "run",
                    str(input_path),
                    "--run-id",
                    "cli-report-parity",
                    "--provider",
                    "mock",
                    "--no-lint-translit",
                ]
            )
            with patch("ruwritingstyles.cli.repo_root_from", return_value=root):
                self.assertEqual(cmd_run(args), 0)

            run_dir = root / "runs" / "cli-report-parity"
            for filename in (
                "report.md",
                "summary.html",
                "report.tex",
                "references.bib",
                "references-gost.md",
            ):
                self.assertTrue((run_dir / filename).exists(), filename)

            self.assertIn("cli-report-parity", (run_dir / "report.tex").read_text(encoding="utf-8"))
            self.assertIn("@book{zaliznyak2004,", (run_dir / "references.bib").read_text(encoding="utf-8"))
            self.assertIn("Зализняк А. А.", (run_dir / "references-gost.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
