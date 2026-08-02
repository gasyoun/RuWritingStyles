"""text_domain field wiring through schema -> CLI -> run.json -> council (H1834).

H1479 already pinned the DOMAIN_CLUSTER_WEIGHTS table itself; this file pins the
*plumbing* around it: the closed TEXT_DOMAINS vocabulary stays in lockstep with
schemas/run.schema.json and the eval manifest, an explicit domain persists through
run creation AND through the write_run_manifest refresh cycle (which re-derives
text_domain from metadata.json — the wipe-back trap), and the persisted value, not
a hardcoded default, is what shifts get_cluster_weights output.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.config import load_manifest, load_model_policy, load_run_metadata
from ruwritingstyles.council import DOMAIN_CLUSTER_WEIGHTS, TEXT_DOMAINS, get_cluster_weights
from ruwritingstyles.runs import create_prepare_run, write_run_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]


class TextDomainVocabularyTests(unittest.TestCase):
    def test_schema_enum_matches_text_domains(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "schemas" / "run.schema.json").read_text(encoding="utf-8")
        )
        field = schema["properties"]["text_domain"]
        self.assertEqual(set(field["enum"]), set(TEXT_DOMAINS))
        self.assertEqual(field["default"], "unknown")
        self.assertIn("unknown", TEXT_DOMAINS)

    def test_every_weight_table_row_is_a_valid_domain(self) -> None:
        self.assertTrue(set(DOMAIN_CLUSTER_WEIGHTS) <= set(TEXT_DOMAINS))

    def test_every_eval_case_domain_is_a_valid_domain(self) -> None:
        manifest = json.loads(
            (REPO_ROOT / "evals" / "manifest.json").read_text(encoding="utf-8")
        )
        used = {
            case["metadata"]["text_domain"]
            for case in manifest.get("cases", [])
            if "text_domain" in case.get("metadata", {})
        }
        self.assertTrue(used, "eval manifest declares no text_domain — fixture broke")
        self.assertTrue(used <= set(TEXT_DOMAINS), used - set(TEXT_DOMAINS))


class TextDomainPersistenceTests(unittest.TestCase):
    def _prepare(self, root: Path, text_domain: str) -> Path:
        return create_prepare_run(
            repo_root=root,
            input_path=Path("note.md"),
            original_text="text",
            normalized_text="text",
            segments=[],
            manifest=load_manifest(REPO_ROOT),
            model_policy=load_model_policy(REPO_ROOT),
            run_id="h1834-run",
            metadata={"text_domain": text_domain},
        )

    def test_explicit_domain_lands_in_run_json_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._prepare(Path(tmp), "etymology")
            self.assertEqual(load_run_metadata(run_dir)["text_domain"], "etymology")
            meta = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["text_domain"], "etymology")

    def test_domain_survives_manifest_refresh(self) -> None:
        # write_run_manifest rebuilds run.json from the DB + metadata.json; a
        # domain carried only in the initial run.json would be wiped back to
        # "unknown" by the first step update.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = self._prepare(root, "etymology")
            write_run_manifest(root, run_dir)
            self.assertEqual(load_run_metadata(run_dir)["text_domain"], "etymology")


class TextDomainWeightActivationTests(unittest.TestCase):
    def test_persisted_domain_changes_cluster_weights(self) -> None:
        # The acceptance criterion: the domain read back from a run's durable
        # state — not a hardcoded default — produces different council weights.
        manifest = load_manifest(REPO_ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = create_prepare_run(
                repo_root=Path(tmp),
                input_path=Path("note.md"),
                original_text="text",
                normalized_text="text",
                segments=[],
                manifest=manifest,
                model_policy=load_model_policy(REPO_ROOT),
                run_id="h1834-weights",
                metadata={"text_domain": "etymology"},
            )
            persisted = load_run_metadata(run_dir)["text_domain"]
        self.assertEqual(persisted, "etymology")
        domain_weights = get_cluster_weights(manifest, persisted)
        neutral_weights = get_cluster_weights(manifest, "unknown")
        self.assertNotEqual(domain_weights, neutral_weights)
        # And directionally: etymology boosts the etymology school, suppresses
        # the normativists (G-04 row: ling_iesh 1.5, ling_nss 0.5).
        by_cluster = {
            ref.cluster_id: ref.style_id
            for ref in manifest.passports
            if ref.cluster_id == ref.style_id
        }
        self.assertGreater(
            domain_weights[by_cluster["ling_iesh"]],
            neutral_weights[by_cluster["ling_iesh"]],
        )
        self.assertLess(
            domain_weights[by_cluster["ling_nss"]],
            neutral_weights[by_cluster["ling_nss"]],
        )


if __name__ == "__main__":
    unittest.main()
