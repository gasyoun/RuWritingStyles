#!/usr/bin/env python3
"""Two-rater gold-annotation harness for the gold expert cases (GOLD_SANSKRIT by
default; `extract --tag GOLD_DICTIONARY` selects the dictionary-register set).

Implements the inter-rater half of evals/GOLD_PROTOCOL.md ("Разметка экспертами"):
rater A is the mechanical scorer verdict already stored in each run's
eval-result.json; rater B is an independent expert (per the 11-07-2026 author
decision: a second AI model, distinct from the provider under evaluation,
disclosed in the paper). The tool keeps rater B blind: `extract` emits an
annotation sheet WITHOUT any scorer verdicts; `agree` merges rater B's
judgments back, computes percent agreement + Cohen's kappa against rater A,
and writes the per-case gold-annotation.json files the protocol requires.

Usage:
    python tools/gold_annotation.py extract --prefix 20260703-h073gov --repeats 5 \
        --out evals/annotation/sheet-h073gov.json
    python tools/gold_annotation.py agree --sheet evals/annotation/sheet-h073gov.json \
        --judgments evals/annotation/raterB-h073gov.json \
        --out-dir evals/annotation
"""
import argparse
import io
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
GOLD_TAG = "GOLD_SANSKRIT"


def load_gold_cases(tag: str = GOLD_TAG):
    manifest = json.loads((ROOT / "evals" / "manifest.json").read_text(encoding="utf-8"))
    cases = manifest["cases"] if isinstance(manifest, dict) else manifest
    return [
        c for c in cases
        if tag in c.get("tags", []) and "deterministic" not in c.get("tags", [])
    ]


def run_dir(prefix: str, case_id: str, rep: int) -> Path:
    return ROOT / "runs" / f"{prefix}-{case_id}-r{rep:02d}"


def collect_findings(rd: Path):
    findings = []
    for review_file in sorted((rd / "reviews").glob("*.review.json")):
        review = json.loads(review_file.read_text(encoding="utf-8"))
        for f in review.get("findings", []):
            findings.append({
                "id": f.get("id"),
                "style_id": f.get("style_id"),
                "span_id": f.get("span_id"),
                "severity": f.get("severity"),
                "type": f.get("type"),
                "finding": f.get("finding"),
            })
    council = json.loads((rd / "council.json").read_text(encoding="utf-8"))
    decisions = {d.get("finding_id"): d.get("status") for d in council.get("decisions", [])}
    for f in findings:
        f["council_status"] = decisions.get(f["id"])
    return findings


def cmd_extract(args):
    sheet = {"prefix": args.prefix, "repeats": args.repeats, "runs": []}
    for case in load_gold_cases(args.tag):
        input_text = (ROOT / case["input"]).read_text(encoding="utf-8")
        for rep in range(1, args.repeats + 1):
            rd = run_dir(args.prefix, case["id"], rep)
            if not rd.is_dir():
                print(f"skip (missing): {rd.name}", file=sys.stderr)
                continue
            verification = json.loads((rd / "verification.json").read_text(encoding="utf-8"))
            sheet["runs"].append({
                "run": rd.name,
                "case_id": case["id"],
                "purpose": case.get("purpose"),
                "required_finding_types": case["scoring"].get("required_finding_types"),
                "accepted_finding_aliases": case["scoring"].get("accepted_finding_aliases", {}),
                "input_text": input_text,
                "findings": collect_findings(rd),
                "verification_status": verification.get("status"),
            })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sheet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(sheet['runs'])} runs). Scorer verdicts are NOT included: "
          f"rater B must judge from this sheet only.")


def scorer_verdict(rd: Path):
    """Rater A: the mechanical scorer's stored verdict for a run."""
    er = json.loads((rd / "eval-result.json").read_text(encoding="utf-8"))
    matched = er.get("matched_expected_risks") or er.get("scoring", {}).get(
        "matched_required_finding_types") or []
    return {
        "detected": bool(matched),
        "matched_types": matched,
        "passed": bool(er.get("scoring", {}).get("passed")),
    }


def kappa(pairs):
    """Cohen's kappa over (a, b) boolean pairs."""
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pa_yes = sum(1 for a, _ in pairs if a) / n
    pb_yes = sum(1 for _, b in pairs if b) / n
    pe = pa_yes * pb_yes + (1 - pa_yes) * (1 - pb_yes)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def cmd_agree(args):
    sheet = json.loads(Path(args.sheet).read_text(encoding="utf-8"))
    judgments = json.loads(Path(args.judgments).read_text(encoding="utf-8"))
    jmap = {j["run"]: j for j in judgments["runs"]}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_case = {}
    for entry in sheet["runs"]:
        rd = ROOT / "runs" / entry["run"]
        a = scorer_verdict(rd)
        b = jmap[entry["run"]]
        per_case.setdefault(entry["case_id"], []).append({
            "run": entry["run"],
            "rater_a_detected": a["detected"],
            "rater_a_matched_types": a["matched_types"],
            "rater_b_caught": b["caught"],            # yes | partial | no
            "rater_b_type_correct": b["type_correct"],
            "rater_b_false_positives": b["false_positives"],
            "rater_b_notes": b.get("notes", ""),
        })

    all_pairs = []
    summary = []
    for case_id, rows in per_case.items():
        pairs = [(r["rater_a_detected"], r["rater_b_caught"] in ("yes", "partial"))
                 for r in rows]
        all_pairs.extend(pairs)
        agree_n = sum(1 for a, b in pairs if a == b)
        annotation = {
            "case_id": case_id,
            "provider": judgments.get("provider", "deepseek"),
            "raters": ["A (mechanical scorer, eval-result.json)",
                       judgments.get("rater_b", "B (second AI model)")],
            "runs": rows,
            "caught": all(r["rater_b_caught"] in ("yes", "partial") for r in rows),
            "type_correct": all(r["rater_b_type_correct"] for r in rows),
            "false_positives": sum(r["rater_b_false_positives"] for r in rows),
            "agreement": agree_n / len(rows),
            "kappa": kappa(pairs),
        }
        out = out_dir / f"gold-annotation-{case_id}.json"
        out.write_text(json.dumps(annotation, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        summary.append((case_id, len(rows), annotation["agreement"], annotation["kappa"],
                        annotation["false_positives"]))
        print(f"wrote {out}")

    overall_agree = sum(1 for a, b in all_pairs if a == b) / len(all_pairs)
    overall_kappa = kappa(all_pairs)
    print("\ncase | runs | agreement | kappa | rater-B false positives")
    for case_id, n, agr, k, fp in summary:
        print(f"{case_id} | {n} | {agr:.2f} | {'n/a' if k is None else f'{k:.3f}'} | {fp}")
    print(f"OVERALL | {len(all_pairs)} | {overall_agree:.2f} | "
          f"{'n/a' if overall_kappa is None else f'{overall_kappa:.3f}'}")
    disagreements = [
        r["run"] for rows in per_case.values() for r in rows
        if r["rater_a_detected"] != (r["rater_b_caught"] in ("yes", "partial"))
    ]
    if disagreements:
        print("\nDISAGREEMENTS (need human adjudication):")
        for run in disagreements:
            print(f"  {run}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract", help="emit blinded annotation sheet for rater B")
    ex.add_argument("--prefix", required=True)
    ex.add_argument("--repeats", type=int, default=5)
    ex.add_argument("--tag", default=GOLD_TAG,
                    help="gold tag selecting the expert cases (GOLD_SANSKRIT, GOLD_DICTIONARY)")
    ex.add_argument("--out", required=True)
    ex.set_defaults(func=cmd_extract)
    ag = sub.add_parser("agree", help="merge rater B judgments, compute agreement")
    ag.add_argument("--sheet", required=True)
    ag.add_argument("--judgments", required=True)
    ag.add_argument("--out-dir", required=True)
    ag.set_defaults(func=cmd_agree)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
