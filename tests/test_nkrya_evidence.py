"""NKRYa evidence (H5283): cache keying, keyness, passport sections, scrutiny evidence — all offline."""

from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.nkrya_evidence import (
    DEFAULT_CACHE_REL, SECTION_END, SECTION_START, SIBLING_CLIENT, LemmaCounts, NkryaEvidence,
    NkryaUnavailable, attach_nkrya_evidence, concordance_payload, evidence_hint, keyness_rows, lemma_query,
    log_ratio, modernize_orthography, portrait_payload, request_key, upsert_section,
)
from ruwritingstyles.scrutiny import create_scrutiny_bundle

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / DEFAULT_CACHE_REL
REPORTS = REPO / "metadata" / "nkrya_keyness"
FIXTURE_RUN = REPO / "tests" / "fixtures" / "scrutiny_nkrya"
HAS_PYMORPHY = importlib.util.find_spec("pymorphy3") is not None
PASSPORTS = ["zalizniak-imennoe", "zalizniak-novgorod", "zalizniak-enklitiki", "zalizniak-udarenie",
             "bartold", "turaev", "krachkovskij", "golenishchev"]


def _write_cache(cache: Path, endpoint: str, payload: dict, response: dict) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    rec = {"request": {"endpoint": endpoint, "payload": payload}, "response": response}
    (cache / f"{request_key(endpoint, payload)}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")


class CacheKeyTests(unittest.TestCase):
    def test_committed_cache_entries_match_their_request(self) -> None:
        files = sorted(CACHE.glob("*.json"))
        self.assertTrue(files, "metadata/nkrya_cache is empty")
        for f in files:
            rec = json.loads(f.read_text(encoding="utf-8"))
            req = rec["request"]
            self.assertEqual(request_key(req["endpoint"], req["payload"]), f.stem, f.name)

    def test_keys_match_the_upstream_client_when_available(self) -> None:
        client = REPO.parent / SIBLING_CLIENT
        if not client.is_file():
            self.skipTest("SanskritLexicography client not checked out beside this repo")
        spec = importlib.util.spec_from_file_location("upstream_nkrya_client", client)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        payload = portrait_payload("сплочённый", "A", "PORTRAIT_FREQUENCY")
        self.assertEqual(request_key("/word-portrait/", payload), mod.request_key("/word-portrait/", payload))
        self.assertEqual(payload["lemma"], "сплоченный")  # portraits are keyed without ё
        self.assertEqual(payload["seed"], mod.SEED)


class KeynessTests(unittest.TestCase):
    def test_log_ratio(self) -> None:
        self.assertAlmostEqual(log_ratio(8, 1_000_000, 1.0), 3.0)
        self.assertAlmostEqual(log_ratio(1, 1_000_000, None), math.log2(1 / 0.01))

    def test_orthography(self) -> None:
        self.assertEqual(modernize_orthography("извѣстныхъ Гіероглифическимъ"), "известных Гиероглифическим")
        self.assertEqual(modernize_orthography("ко\x01смы сло́во"), "космы слово")

    def test_rows_ranked_by_keyness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            _write_cache(cache, "/word-portrait/", portrait_payload("энклитика", "S", "PORTRAIT_FREQUENCY"),
                         {"frequencyData": {"ipm": 0.5, "category": 1}})
            _write_cache(cache, "/word-portrait/", portrait_payload("слово", "S", "PORTRAIT_FREQUENCY"),
                         {"frequencyData": {"ipm": 1000.0, "category": 5}})
            counts = LemmaCounts(tokens=10_000)
            counts.counts.update({("слово", "S"): 20, ("энклитика", "S"): 10})
            rows = keyness_rows(counts, NkryaEvidence(cache), top_n=2)
        self.assertEqual([r["lemma"] for r in rows], ["энклитика", "слово"])
        self.assertAlmostEqual(rows[0]["log_ratio"], round(math.log2(1000 / 0.5), 2))

    def test_offline_miss_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(NkryaUnavailable):
            NkryaEvidence(Path(tmp)).freq("туча", "S")

    def test_upsert_is_idempotent(self) -> None:
        md = "# P\n\n## Лексика\n\nx\n\n## Формулы\n\ny\n"
        section = f"{SECTION_START}\n## Лексическая подпись (НКРЯ)\nA\n{SECTION_END}"
        once = upsert_section(md, section, "## Формулы")
        self.assertLess(once.index("Лексическая подпись"), once.index("## Формулы"))
        again = upsert_section(once, section.replace("\nA\n", "\nB\n"), "## Формулы")
        self.assertEqual(again.count(SECTION_START), 1)
        self.assertIn("\nB\n", again)


class CommittedPassportTests(unittest.TestCase):
    def test_each_grounded_passport_carries_a_measured_section(self) -> None:
        for p in PASSPORTS:
            with self.subTest(passport=p):
                report = json.loads((REPORTS / f"{p}.json").read_text(encoding="utf-8"))
                md = (REPO / "ClaudeStyles" / f"{p}-style.md").read_text(encoding="utf-8")
                self.assertEqual(md.count(SECTION_START), 1)
                self.assertIn("## Лексическая подпись (НКРЯ)", md)
                self.assertGreaterEqual(len(report["rows"]), 20)
                # every ipm in the report is reproducible from the committed cache, offline
                ev = NkryaEvidence(CACHE)
                for row in report["rows"]:
                    self.assertEqual(ev.freq(row["lemma"], row["pos"])["ipm"], row["nkrya_ipm"], row["lemma"])
                    self.assertIn(f"| {row['lemma']} |", md)
                self.assertTrue(set(report["cache_keys"]) <= {f.stem for f in CACHE.glob("*.json")})


class ScrutinyEvidenceTests(unittest.TestCase):
    def test_hints(self) -> None:
        self.assertEqual(evidence_hint(12.0, 0, 0.0), "modern-only: no 1800-1899 hits")
        self.assertEqual(evidence_hint(490.0, 97723, 1191.0), "19th-century-skewed: x2.4 its whole-corpus rate")
        self.assertTrue(evidence_hint(100.0, 50, 10.0).startswith("modern-skewed"))
        self.assertEqual(evidence_hint(0.8, 102, 1.2), "rare in every period")
        self.assertEqual(evidence_hint(None, 0, None), "unattested in NKRYa main corpus")

    def test_attach_is_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            _write_cache(cache, "/word-portrait/", portrait_payload("блогер", None, "PORTRAIT_FREQUENCY"),
                         {"frequencyData": {"ipm": 3.2, "category": 2}})
            _write_cache(cache, "/lex-gramm/concordance",
                         concordance_payload(lemma_query("блогер"), n=1,
                                             subcorpus_conditions=[{"fieldName": "created",
                                                                    "intRange": {"begin": 1800, "end": 1899}}]),
                         {"queryStats": {"wordUsageCount": 0}, "subcorpStats": {"wordUsageCount": 82049244}})

            findings = [{"span_id": "p001", "category": "anachronism", "severity": "warning", "finding": "x",
                         "suggestion": "y", "confidence": 0.7, "term": "блогер"},
                        {"span_id": "p002", "category": "syntax", "severity": "note", "finding": "«блогер»",
                         "suggestion": "z", "confidence": 0.5}]
            import ruwritingstyles.nkrya_evidence as ne
            saved = ne._morph
            ne._morph = lambda morph: None
            try:
                out = attach_nkrya_evidence(findings, NkryaEvidence(cache))
            finally:
                ne._morph = saved
        ev = out[0]["nkrya_evidence"]
        self.assertEqual((ev["ipm"], ev["hits_1800_1899"], ev["hint"]), (3.2, 0, "modern-only: no 1800-1899 hits"))
        self.assertTrue(ev["advisory"])
        self.assertEqual(out[0]["severity"], "warning")
        self.assertNotIn("nkrya_evidence", out[1])

    @unittest.skipUnless(HAS_PYMORPHY, "pymorphy3 not installed (pip install ruwritingstyles[nkrya])")
    def test_prompt_shows_nkrya_evidence_on_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            for name in ("segments.json", "normalized.md"):
                (run / name).write_text((FIXTURE_RUN / name).read_text(encoding="utf-8"), encoding="utf-8")
            bundle = create_scrutiny_bundle(repo_root=REPO, run_dir=run, nkrya=NkryaEvidence(CACHE))
            prompt = bundle.prompt_md.read_text(encoding="utf-8")
            shell = json.loads(bundle.scrutiny_json.read_text(encoding="utf-8"))
        self.assertIn("## NKRYa Corpus Evidence (advisory)", prompt)
        rows = shell["nkrya"]["evidence"]
        self.assertTrue(rows and all(r.get("status") != "unavailable" for r in rows), rows)
        for r in rows:
            self.assertIn(f"| {r['lemma']} |", prompt)
        self.assertTrue(all(r["ipm_1800_1899"] is not None for r in rows))
        self.assertTrue(any(r["hint"].startswith("19th-century-skewed") for r in rows), [r["hint"] for r in rows])

    def test_prompt_unchanged_without_nkrya(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            for name in ("segments.json", "normalized.md"):
                (run / name).write_text((FIXTURE_RUN / name).read_text(encoding="utf-8"), encoding="utf-8")
            bundle = create_scrutiny_bundle(repo_root=REPO, run_dir=run)
            prompt = bundle.prompt_md.read_text(encoding="utf-8")
            shell = json.loads(bundle.scrutiny_json.read_text(encoding="utf-8"))
        self.assertNotIn("NKRYa", prompt)
        self.assertNotIn("nkrya", shell)


if __name__ == "__main__":
    unittest.main()
