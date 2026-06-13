import json
import os
import shutil
import unittest
from pathlib import Path

# Deterministic mock runs must not touch the network (the MockProvider simulates
# a search_scholar tool call during verification).
os.environ.setdefault("RWS_OFFLINE", "1")

from ruwritingstyles.config import load_manifest, load_model_policy
from ruwritingstyles.execution import execute_review_artifact
from ruwritingstyles.pipeline import core_pipeline
from ruwritingstyles.providers import provider_from_name
from ruwritingstyles.review import create_review_bundle
from ruwritingstyles.runs import create_prepare_run
from ruwritingstyles.segment import normalize_document, segment_markdown

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = "# Заметка\n\nСлово X произошло от слова Y (Zaliznyak 2004).\n"


class CorePipelineTests(unittest.TestCase):
    def _prepare(self, run_id: str):
        run_dir = REPO_ROOT / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))
        norm = normalize_document(DOC)
        segs = segment_markdown(norm)
        manifest = load_manifest(REPO_ROOT)
        model_policy = load_model_policy(REPO_ROOT)
        create_prepare_run(
            repo_root=REPO_ROOT, input_path=Path("note.md"), original_text=DOC,
            normalized_text=norm, segments=segs, manifest=manifest,
            model_policy=model_policy, run_id=run_id, provider="mock", profile="researcher",
        )
        return run_dir, manifest, model_policy

    def test_execute_produces_all_artifacts(self) -> None:
        run_dir, manifest, model_policy = self._prepare("unittest-core-exec")
        core_pipeline(
            repo_root=REPO_ROOT, run_dir=run_dir, provider_name="mock",
            manifest=manifest, model_policy=model_policy, execute=True,
        )
        for name in ("council.json", "revision.json", "revised.md",
                     "verification.json", "translit-lint.json", "citations.json",
                     "report.md", "references-gost.md"):
            self.assertTrue((run_dir / name).exists(), f"missing {name}")
        council = json.loads((run_dir / "council.json").read_text(encoding="utf-8"))
        self.assertEqual(council.get("status"), "completed")

        # Run is self-describing on disk (not DB-dependent): run.json carries
        # final status, metrics and step outcomes.
        run_manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run_manifest["status"], "completed")
        self.assertIn("bloom_stats", run_manifest["metrics"])
        self.assertIn("citation_stats", run_manifest["metrics"])
        self.assertTrue(run_manifest["steps"])

    def test_prompt_only_mode_builds_bundles_without_executing(self) -> None:
        run_dir, manifest, model_policy = self._prepare("unittest-core-prompt")
        core_pipeline(
            repo_root=REPO_ROOT, run_dir=run_dir, provider_name="mock",
            manifest=manifest, model_policy=model_policy, execute=False,
        )
        # Bundles exist as prompt-ready shells; no provider-filled revision.
        self.assertTrue((run_dir / "council.json").exists())
        self.assertTrue(any((run_dir / "reviews").glob("*.prompt.md")))
        council = json.loads((run_dir / "council.json").read_text(encoding="utf-8"))
        self.assertEqual(council.get("status"), "prompt_ready")
        self.assertFalse((run_dir / "revised.md").exists())

    def test_on_update_streams_step_events(self) -> None:
        run_dir, manifest, model_policy = self._prepare("unittest-core-events")
        events = []
        core_pipeline(
            repo_root=REPO_ROOT, run_dir=run_dir, provider_name="mock",
            manifest=manifest, model_policy=model_policy, execute=True,
            on_update=lambda e: events.append(e),
        )
        types = {e["type"] for e in events}
        self.assertIn("run_status", types)
        self.assertIn("step_update", types)
        self.assertTrue(any(e.get("status") == "completed" and e["type"] == "run_status" for e in events))
        # Each completed step carries an artifact path or None, never crashes.
        step_ids = {e["step_id"] for e in events if e["type"] == "step_update"}
        self.assertIn("review", step_ids)
        self.assertIn("reports", step_ids)


class ExecutionLayerTests(unittest.TestCase):
    def test_execute_review_artifact_fills_findings(self) -> None:
        run_id = "unittest-exec-review"
        run_dir = REPO_ROOT / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))
        norm = normalize_document(DOC)
        segs = segment_markdown(norm)
        manifest = load_manifest(REPO_ROOT)
        model_policy = load_model_policy(REPO_ROOT)
        create_prepare_run(
            repo_root=REPO_ROOT, input_path=Path("note.md"), original_text=DOC,
            normalized_text=norm, segments=segs, manifest=manifest,
            model_policy=model_policy, run_id=run_id, provider="mock",
        )
        style_id = manifest.mvp_style_ids[0]
        bundle = create_review_bundle(
            repo_root=REPO_ROOT, run_dir=run_dir, style_id=style_id, manifest=manifest,
        )
        before = json.loads(bundle.review_json.read_text(encoding="utf-8"))
        self.assertEqual(before["status"], "prompt_ready")

        execute_review_artifact(
            repo_root=REPO_ROOT, review_path=bundle.review_json,
            provider=provider_from_name("mock"),
            model=model_policy.resolve_model("style_review", "mock"),
        )
        after = json.loads(bundle.review_json.read_text(encoding="utf-8"))
        self.assertEqual(after["status"], "completed")
        self.assertTrue(after["findings"])


if __name__ == "__main__":
    unittest.main()
