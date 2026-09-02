"""API/CLI report-artifact parity — roadmap-sanskrit-dh.md Ф1 "Унифицировать CLI и Web/API".

Both entry points already share ``core_pipeline``'s ``do_reports()`` step
(``pipeline.py``), so this pins that unification with a real run through the
Web/API code path (``create_prepare_run`` + ``run_full_pipeline``, exactly what
``api.execute_run`` calls) — mirroring ``tests/test_cli_reports.py``'s CLI-side
fixture and assertions so a future divergence between the two entry points
fails a test instead of going unnoticed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.config import load_manifest, load_model_policy
from ruwritingstyles.pipeline import ExecutionMode, PipelineOptions, run_full_pipeline
from ruwritingstyles.runs import create_prepare_run
from ruwritingstyles.segment import normalize_document, segment_markdown


class ApiReportArtifactParityTests(unittest.TestCase):
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
budget_modes:
  standard:
    providers:
      - mock
    max_outbound_attempts: 64
    max_tokens: 750000
    max_wall_seconds: 3600
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

    def test_api_pipeline_writes_cli_and_scholarly_report_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo_fixture(root)
            input_path = root / "input.md"
            original_text = "# Текст\n\nСр. (Zaliznyak 2004).\n"
            input_path.write_text(original_text, encoding="utf-8")

            manifest = load_manifest(root)
            model_policy = load_model_policy(root)
            normalized_text = normalize_document(original_text)
            segments = segment_markdown(normalized_text)
            # PROMPT mode, matching test_cli_reports.py's CLI-side run (no --execute):
            # the report step is deterministic and runs regardless of provider
            # execution, so this stays a lean shared-code-path check rather than
            # dragging in the full execute-mode schema/provider machinery.
            options = PipelineOptions(mode=ExecutionMode.PROMPT, style_ids=tuple(manifest.mvp_style_ids))

            # Exactly what api.execute_run does before backgrounding run_full_pipeline.
            run_dir = create_prepare_run(
                repo_root=root,
                input_path=input_path,
                original_text=original_text,
                normalized_text=normalized_text,
                segments=segments,
                manifest=manifest,
                model_policy=model_policy,
                run_id="api-report-parity",
                provider="mock",
            )

            run_full_pipeline(
                repo_root=root,
                run_dir=run_dir,
                provider_name="mock",
                options=options,
            )

            for filename in (
                "report.md",
                "summary.html",
                "report.tex",
                "references.bib",
                "references-gost.md",
            ):
                self.assertTrue((run_dir / filename).exists(), filename)

            self.assertIn("api-report-parity", (run_dir / "report.tex").read_text(encoding="utf-8"))
            self.assertIn("@book{zaliznyak2004,", (run_dir / "references.bib").read_text(encoding="utf-8"))
            self.assertIn("Зализняк А. А.", (run_dir / "references-gost.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
