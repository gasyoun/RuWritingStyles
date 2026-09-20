"""tests for tools/build_w24_harvest_report.py — W2.4 report generator."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "tools" / "build_w24_harvest_report.py"

spec = importlib.util.spec_from_file_location("build_w24_harvest_report", GENERATOR)
mod = importlib.util.module_from_spec(spec)
sys.modules["build_w24_harvest_report"] = mod
spec.loader.exec_module(mod)

RUN_DATE = "20-09-2026"


def _sidecar(slug: str, article: int, source: str) -> dict:
    return {
        "journal_slug": slug,
        "article_id": str(article),
        "extraction": {"source": source, "extractor": "x", "verdict": "pass", "harvested_on": RUN_DATE},
        "selection": {"verdict": "include"},
    }


@pytest.fixture()
def corpus_dir(tmp_path: Path) -> Path:
    pdf = tmp_path / "PDFtoTXT"
    pdf.mkdir()
    (pdf / "a1.json").write_text(json.dumps(_sidecar("j-one", 1, "html")), encoding="utf-8")
    (pdf / "a2.json").write_text(json.dumps(_sidecar("j-one", 2, "pdf")), encoding="utf-8")
    # A stale sidecar from an earlier date must not be counted.
    stale = _sidecar("j-one", 3, "pdf")
    stale["extraction"]["harvested_on"] = "19-08-2026"
    (pdf / "a3.json").write_text(json.dumps(stale), encoding="utf-8")
    quarantine = tmp_path / "quarantine"
    quarantine.mkdir()
    (quarantine / "q1.json").write_text(
        json.dumps({"sidecar": _sidecar("j-one", 4, "")}), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture()
def driver_json(tmp_path: Path) -> Path:
    data = {
        "started": "2026-09-20T15:19:22",
        "journals": [
            {
                "slug": "j-one",
                "status": "ok",
                "written": 2,
                "already_pass": 1,
                "quarantined": 1,
                "selection_skipped": {"uncertain": 7},
                "source_split": {"html": 1, "pdf": 1},
                "elapsed_seconds": 12.5,
            },
            {"slug": "j-bad", "status": "failed", "error": "GET failed after retries: x"},
        ],
    }
    path = tmp_path / "driver.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_sidecar_stats_counts_only_run_date(corpus_dir: Path) -> None:
    stats = mod.sidecar_stats(corpus_dir, RUN_DATE)
    assert stats["sidecar_files"] == 2
    assert stats["sources"] == {"html": 1, "pdf": 1}
    assert stats["quarantined"] == 1
    assert stats["per_journal"]["j-one"]["written"] == 2


def test_driver_stats_aggregates(driver_json: Path) -> None:
    stats = mod.driver_stats(driver_json)
    assert stats["journals_ok"] == 1
    assert stats["written"] == 2
    assert stats["already_pass"] == 1
    assert stats["source_split"] == {"html": 1, "pdf": 1}
    assert stats["journals_failed"] == [
        {"slug": "j-bad", "status": "failed", "error": "GET failed after retries: x"}
    ]


def test_render_carries_the_contract_numbers(driver_json: Path, corpus_dir: Path) -> None:
    fragment = mod.render(mod.driver_stats(driver_json), mod.sidecar_stats(corpus_dir, RUN_DATE), RUN_DATE, 50)
    # counts, quarantine size and the per-journal extraction-source split (W2.4)
    assert "**2**" in fragment  # written
    assert "Quarantined this run: **1**" in fragment
    assert "`j-one` | ok | 2 | 1 | 1 | uncertain 7 | html 1, pdf 1 | 12.5" in fragment
    assert "j-bad" in fragment
