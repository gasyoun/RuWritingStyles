"""Unit tests for multi-document features: migration and audit."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles.migration import migrate_document_style
from ruwritingstyles.audit import audit_project_consistency
from ruwritingstyles.project import update_project_context

class MultiDocTests(unittest.TestCase):

    def test_migrate_document_style_calls_provider_and_saves_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / "styles").mkdir()
            (repo_root / "styles" / "manifest.yml").write_text("mvp_style_ids: [gasparov]", encoding="utf-8")
            (repo_root / "runs").mkdir()
            (repo_root / "schemas").mkdir()
            
            # Copy real schema or create a dummy one for the test
            schema_src = ROOT / "schemas" / "migration-summary.schema.json"
            (repo_root / "schemas" / "migration-summary.schema.json").write_text(schema_src.read_text(encoding="utf-8"), encoding="utf-8")
            
            input_file = repo_root / "input.md"
            input_file.write_text("Original text.", encoding="utf-8")
            
            # Mock passport summary
            mock_passport = MagicMock()
            mock_passport.style_id = "gasparov"
            mock_passport.name = "Gasparov"
            mock_passport.source_prompt = "styles/passports/gasparov.prompt.md"
            
            (repo_root / "styles" / "passports").mkdir(parents=True)
            (repo_root / "styles" / "passports" / "gasparov.prompt.md").write_text("Gasparov rules.", encoding="utf-8")
            
            mock_provider = MagicMock()
            mock_provider.generate_json.return_value = {
                "migration_summary": "Simplified.",
                "revised_text": "Migrated text."
            }
            
            with patch("ruwritingstyles.config.load_passport_summaries", return_value=[mock_passport]):
                migrated_path = migrate_document_style(
                    repo_root=repo_root,
                    input_file=input_file,
                    from_style_id="unknown",
                    to_style_id="gasparov",
                    provider=mock_provider,
                    model="test-model"
                )
            
            self.assertTrue(migrated_path.exists())
            self.assertEqual(migrated_path.read_text(encoding="utf-8"), "Migrated text.")
            
            # Verify the run directory is unique
            self.assertIn("migration-unknown-to-gasparov-input", str(migrated_path))
            
            summary_path = migrated_path.parent / "migration-summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["migration_summary"], "Simplified.")

    def test_update_project_context_merges_commitments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            run_dir = project_dir / "run-1"
            run_dir.mkdir()
            
            (run_dir / "council.json").write_text(json.dumps({
                "stylistic_commitments": [
                    {"term": "идиом", "decision": "Use 'идиом'.", "rationale": "Formal."}
                ]
            }), encoding="utf-8")
            
            update_project_context(project_dir, run_dir)
            
            context_path = project_dir / "project-context.json"
            self.assertTrue(context_path.exists())
            context = json.loads(context_path.read_text(encoding="utf-8"))
            self.assertEqual(len(context["stylistic_commitments"]), 1)
            self.assertEqual(context["stylistic_commitments"][0]["term"], "идиом")

    def test_audit_project_consistency_detects_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            project_dir = repo_root / "project"
            project_dir.mkdir()
            
            (project_dir / "project-context.json").write_text(json.dumps({
                "commitments": [
                    {"term": "идиом", "decision": "Use 'идиом' instead of 'диалект'."}
                ]
            }), encoding="utf-8")
            
            run_dir = project_dir / "run-1"
            run_dir.mkdir()
            (run_dir / "revision.md").write_text("Этот диалект очень сложный.", encoding="utf-8")
            
            mock_provider = MagicMock()
            mock_provider.generate_json.return_value = {
                "status": "completed",
                "audit_summary": "Found one violation.",
                "violations": [
                    {
                        "document_id": "run-1",
                        "term": "идиом",
                        "issue": "Used 'диалект' instead of 'идиом'.",
                        "severity": "critical"
                    }
                ],
                "passed_commitments": []
            }
            
            result = audit_project_consistency(
                repo_root=repo_root,
                project_dir=project_dir,
                provider=mock_provider,
                model="test-model"
            )
            
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(result["violations"]), 1)
            self.assertEqual(result["violations"][0]["document_id"], "run-1")

if __name__ == "__main__":
    unittest.main()
