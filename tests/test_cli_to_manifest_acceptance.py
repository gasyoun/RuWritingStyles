"""CLI/API -> persistence -> runtime -> export acceptance (H2576).

H1834 wired `text_domain` at the library layer (`create_prepare_run`) and H1861
rerouted `rws generate-passport` onto `provider.generate_json`. Those tests never
entered through the CLI or the FastAPI `/runs/execute` body, so a non-default
domain submitted by a client still persisted as `unknown`, and a generate-passport
round-trip was never asserted against `rws` + `load_manifest`.

This file pins the full path: the command / request, the durable row, a
downstream behaviour change, and (for `text_domain`) the export bundle.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

os.environ.setdefault("RWS_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient

from ruwritingstyles import api
from ruwritingstyles.cli import main
from ruwritingstyles.config import load_manifest, load_run_metadata
from ruwritingstyles.council import get_cluster_weights
from ruwritingstyles.runs import write_run_manifest
from ruwritingstyles.workspace import init_workspace


RUN_PREFIX = "unittest-h2576"


class _RunCleanup(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_token = api._API_TOKEN
        api._API_TOKEN = ""
        self._remove_runs()

    def tearDown(self) -> None:
        self._remove_runs()
        api._API_TOKEN = self._saved_token

    def _remove_runs(self) -> None:
        runs_dir = ROOT / "runs"
        if not runs_dir.exists():
            return
        for path in runs_dir.glob(f"{RUN_PREFIX}*"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    def _write_note(self, tmp: Path, name: str = "note.md") -> Path:
        note = tmp / name
        note.write_text("# Заметка\n\nЭтимология корня *ved-.\n", encoding="utf-8")
        return note


class CliTextDomainAcceptanceTests(_RunCleanup):
    def test_prepare_persists_nondefault_domain_and_changes_weights(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            note = self._write_note(Path(tmp))
            exit_code = main(
                [
                    "prepare",
                    str(note),
                    "--text-domain",
                    "etymology",
                    "--run-id",
                    f"{RUN_PREFIX}-prepare-etym",
                ]
            )
        self.assertEqual(exit_code, 0)
        run_dir = ROOT / "runs" / f"{RUN_PREFIX}-prepare-etym"
        persisted = load_run_metadata(run_dir)["text_domain"]
        meta = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted, "etymology")
        self.assertEqual(meta["text_domain"], "etymology")

        write_run_manifest(ROOT, run_dir)
        self.assertEqual(load_run_metadata(run_dir)["text_domain"], "etymology")

        manifest = load_manifest(ROOT)
        domain_weights = get_cluster_weights(manifest, persisted)
        neutral_weights = get_cluster_weights(manifest, "unknown")
        self.assertNotEqual(domain_weights, neutral_weights)

    def test_prepare_default_stays_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            note = self._write_note(Path(tmp))
            exit_code = main(
                ["prepare", str(note), "--run-id", f"{RUN_PREFIX}-prepare-default"]
            )
        self.assertEqual(exit_code, 0)
        run_dir = ROOT / "runs" / f"{RUN_PREFIX}-prepare-default"
        self.assertEqual(load_run_metadata(run_dir)["text_domain"], "unknown")

    def test_run_writes_domain_into_council_prompt_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            note = self._write_note(Path(tmp))
            exit_code = main(
                [
                    "run",
                    str(note),
                    "--text-domain",
                    "etymology",
                    "--run-id",
                    f"{RUN_PREFIX}-run-etym",
                    "--provider",
                    "mock",
                ]
            )
        self.assertEqual(exit_code, 0)
        run_dir = ROOT / "runs" / f"{RUN_PREFIX}-run-etym"
        self.assertEqual(load_run_metadata(run_dir)["text_domain"], "etymology")

        prompt = (run_dir / "council.prompt.md").read_text(encoding="utf-8")
        manifest = load_manifest(ROOT)
        domain_weights = get_cluster_weights(manifest, "etymology")
        neutral_weights = get_cluster_weights(manifest, "unknown")
        shifted = [
            style_id
            for style_id, weight in domain_weights.items()
            if weight != neutral_weights[style_id]
        ]
        self.assertTrue(shifted, "etymology must shift at least one cluster weight")
        # The prompt serialises the live weight table; a shifted style's
        # etymology multiplier must appear, proving the persisted domain — not
        # the default — drove council authority.
        sample = shifted[0]
        self.assertIn(f'"{sample}"', prompt)
        self.assertIn(str(domain_weights[sample]), prompt)

        self.assertEqual(main(["export", str(run_dir)]), 0)
        bundle = run_dir / f"{RUN_PREFIX}-run-etym-bundle.zip"
        self.assertTrue(bundle.exists())
        with ZipFile(bundle) as archive:
            names = set(archive.namelist())
            run_json = json.loads(
                archive.read(f"{RUN_PREFIX}-run-etym/run.json").decode("utf-8")
            )
            meta = json.loads(
                archive.read(f"{RUN_PREFIX}-run-etym/metadata.json").decode("utf-8")
            )
        self.assertIn(f"{RUN_PREFIX}-run-etym/run.json", names)
        self.assertIn(f"{RUN_PREFIX}-run-etym/metadata.json", names)
        self.assertEqual(run_json["text_domain"], "etymology")
        self.assertEqual(meta["text_domain"], "etymology")


class ApiTextDomainAcceptanceTests(_RunCleanup):
    def test_execute_persists_nondefault_domain(self) -> None:
        client = TestClient(api.app)
        resp = client.post(
            "/runs/execute",
            json={
                "text": "# Заметка\n\nЭтимология корня *ved-.\n",
                "filename": f"{RUN_PREFIX}-api.md",
                "text_domain": "etymology",
                "execute": False,
                "provider": "mock",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        run_id = resp.json()["run_id"]
        run_dir = ROOT / "runs" / run_id
        self.addCleanup(shutil.rmtree, run_dir, ignore_errors=True)
        persisted = load_run_metadata(run_dir)["text_domain"]
        self.assertEqual(persisted, "etymology")
        meta = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["text_domain"], "etymology")
        manifest = load_manifest(ROOT)
        self.assertNotEqual(
            get_cluster_weights(manifest, persisted),
            get_cluster_weights(manifest, "unknown"),
        )

    def test_omitted_domain_stays_unknown(self) -> None:
        client = TestClient(api.app)
        resp = client.post(
            "/runs/execute",
            json={
                "text": "# T\n\nтекст",
                "filename": f"{RUN_PREFIX}-api-default.md",
                "execute": False,
                "provider": "mock",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        run_dir = ROOT / "runs" / resp.json()["run_id"]
        self.addCleanup(shutil.rmtree, run_dir, ignore_errors=True)
        self.assertEqual(load_run_metadata(run_dir)["text_domain"], "unknown")

    def test_unknown_domain_is_400(self) -> None:
        client = TestClient(api.app)
        resp = client.post(
            "/runs/execute",
            json={"text": "hi", "text_domain": "not-a-domain", "execute": False},
        )
        self.assertEqual(resp.status_code, 400, resp.text)


class CliGeneratePassportAcceptanceTests(unittest.TestCase):
    def test_cli_writes_source_prompt_into_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            init_workspace(workspace)
            env = os.environ.copy()
            env["RWS_WORKSPACE"] = str(workspace)
            env["RWS_OFFLINE"] = "1"
            with patch.dict(os.environ, env, clear=False):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    exit_code = main(
                        [
                            "generate-passport",
                            "Тестовый стиль",
                            "--description",
                            "проверка CLI-to-manifest",
                            "--provider",
                            "mock",
                        ]
                    )
                self.assertEqual(exit_code, 0, buf.getvalue())
                output = buf.getvalue()
                self.assertIn("mock-generated-style", output)

                passport = workspace / "styles" / "passports" / "mock-generated-style.yml"
                # save_generated_style always suffixes `-style.md` onto the
                # passport_id, so a mock id of `mock-generated-style` lands as
                # `mock-generated-style-style.md`. The acceptance pin is that
                # whatever path was written is also the manifest `source_prompt`.
                prompt = workspace / "ClaudeStyles" / "mock-generated-style-style.md"
                self.assertTrue(passport.exists(), passport)
                self.assertTrue(prompt.exists(), prompt)
                manifest_text = (workspace / "styles" / "manifest.yml").read_text(
                    encoding="utf-8"
                )
                self.assertIn("id: mock-generated-style", manifest_text)
                self.assertIn(
                    "source_prompt: ClaudeStyles/mock-generated-style-style.md",
                    manifest_text,
                )

                # Downstream: the catalog loader refuses a row without
                # source_prompt. A successful load + list-styles line is the
                # runtime effect of the persisted field.
                loaded = load_manifest(workspace)
                style_ids = [ref.style_id for ref in loaded.passports]
                self.assertIn("mock-generated-style", style_ids)
                listed = io.StringIO()
                with redirect_stdout(listed):
                    self.assertEqual(main(["list-styles"]), 0)
                listed_text = listed.getvalue()
                self.assertIn("mock-generated-style", listed_text)
                # Path.relative_to uses the OS separator; accept either slash.
                self.assertRegex(
                    listed_text,
                    r"prompt: ClaudeStyles[/\\]mock-generated-style-style\.md",
                )


if __name__ == "__main__":
    unittest.main()
