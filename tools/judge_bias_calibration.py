#!/usr/bin/env python3
"""H6845 — LLM-judge bias calibration probes (W8), offline recompute lane.

The probes themselves were first built by H4658 (tools/judge_bias_probe.py:
length correlation) and H5010 (tools/position_order_paired.py,
tools/position_bias_pair.py: paired position-swap). This tool does NOT rebuild
them; it closes the owed residuals:

  1. recompute-addendum   Independent paired-family recomputation of the H5010
                          addendum (second-session) set from the saved raw
                          responses (evals/probes/h5010_order_paired/) — the
                          residual left open in POSITION_PAIR_RESULTS §53 and
                          ORDER_PAIRED §Verifier. Zero paid calls.
  2. length-correlation   Re-derivation of the judge-verdict vs answer-length
                          Spearman axes from the committed rater artifacts
                          (parity vs the H4658 committed figures). Zero calls.
  3. self-preference      Bounded own-family favouritism screen over graded
                          records that carry (judged_by, produced_by, score)
                          provenance. The committed h073gov artifacts carry no
                          producer-family metadata, so on real data the screen
                          reports UNMEASURED rather than inventing an estimate;
                          selftest proves the detector on synthetic data.
                          Measuring it for real needs new judge calls — outside
                          this handoff's $0.00 spend cap (see the H6845 report).

Stdlib only. No network. No model calls in any subcommand.

_Гасунс_
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

Z95 = 1.959963984540054
ADDENDUM_DIR_DEFAULT = "evals/probes/h5010_order_paired"
SHEET_DEFAULT = "evals/annotation/sheet-h073gov.json"
RATERS_DEFAULT = [
    "evals/annotation/raterB-h073gov.json",
    "evals/annotation/raterC-h073gov-swap-2026-09-14.json",
]
H4658_JSON_DEFAULT = "evals/probes/judge-bias-h073gov-2026-09-14.json"


# ------------------------------------------------------------------- statistics

def wilson95(k: int, n: int) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    z = Z95
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, center - half), 6), round(min(1.0, center + half), 6)]


def _rank(data):
    order = sorted(range(len(data)), key=lambda i: data[i])
    ranks = [0.0] * len(data)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and data[order[j + 1]] == data[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            ranks[order[t]] = avg
        i = j + 1
    return ranks


def spearman(xs, ys):
    """Spearman rho with average-rank tie handling; None on degenerate input."""
    n = len(xs)
    if n < 3 or len(xs) != len(ys):
        return None, "n<3 or length mismatch"
    rx, ry = _rank(xs), _rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None, "zero variance in score axis (degenerate: constant verdicts)"
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return round(sxy / math.sqrt(sxx * syy), 4), None


# ------------------------------------------------------- 1. addendum recompute

def recompute_addendum(mapping, responses, sheet) -> dict:
    """Independent paired recompute of the H5010 addendum set.

    Deliberately does NOT import tools/position_order_paired.py: the point of
    the residual is a second implementation agreeing (or disagreeing) with the
    committed analysis from the raw artifacts alone.
    """
    resp_by_task = {r["task"]: r for r in responses}
    by_run = {r["run"]: r for r in sheet["runs"]}
    canon_of = {}
    for run in sheet["runs"]:
        req = set(run.get("required_finding_types", []))
        aliases = run.get("accepted_finding_aliases", {})
        for a in aliases.values():
            req.update(a)
        canon_of[run["run"]] = req

    pairs, invalid = {}, []
    for m in mapping:
        resp = resp_by_task.get(m["task"])
        if resp is None:
            invalid.append({"task": m["task"], "reason": "missing_response"})
            continue
        v = {"caught": resp.get("caught"),
             "type_correct": resp.get("type_correct"),
             "false_positives": resp.get("false_positives")}
        if (v["caught"] not in ("yes", "partial", "no")
                or not isinstance(v["type_correct"], bool)
                or not isinstance(v["false_positives"], int)):
            invalid.append({"task": m["task"], "reason": "malformed_verdict"})
            continue
        pairs.setdefault(m["run"], {})[m["condition"]] = v

    rows = []
    presentations = []  # (target_pos, positive)
    for run_id, conds in sorted(pairs.items()):
        if set(conds) != {"original", "reversed"}:
            invalid.append({"run": run_id, "reason": "missing_condition"})
            continue
        a, b = conds["original"], conds["reversed"]
        run = by_run[run_id]
        row = {
            "run": run_id,
            "caught_flip": a["caught"] != b["caught"],
            "type_correct_flip": a["type_correct"] != b["type_correct"],
            "fp_flip": a["false_positives"] != b["false_positives"],
            "fp_A": a["false_positives"], "fp_B": b["false_positives"],
        }
        row["discordant"] = (row["caught_flip"] or row["type_correct_flip"]
                             or row["fp_flip"])
        rows.append(row)
        for cond, v in (("original", a), ("reversed", b)):
            findings = list(run["findings"])
            if cond == "reversed":
                findings = findings[::-1]
            tpos = next((pos for pos, f in enumerate(findings, 1)
                         if f.get("type") in canon_of[run_id]), None)
            positive = (v["caught"] == "yes") or (v["type_correct"] is True)
            presentations.append((tpos, positive))

    n = len(rows)
    k = sum(1 for r in rows if r["discordant"])
    yes_pos = sorted(tpos for tpos, positive in presentations
                     if positive and tpos is not None)
    no_pos = sorted(tpos for tpos, positive in presentations
                    if not positive and tpos is not None)
    direction = {
        "positive_verdicts_target_pos_1_2": sum(1 for tpos, positive in presentations
                                                if positive and tpos is not None and tpos <= 2),
        "positive_verdicts_target_pos_3plus": sum(1 for tpos, positive in presentations
                                                  if positive and tpos is not None and tpos > 2),
        "negative_verdicts_target_pos_1_2": sum(1 for tpos, positive in presentations
                                                if not positive and tpos is not None and tpos <= 2),
        "negative_verdicts_target_pos_3plus": sum(1 for tpos, positive in presentations
                                                  if not positive and tpos is not None and tpos > 2),
        "median_target_pos_when_positive": yes_pos[len(yes_pos) // 2] if yes_pos else None,
        "median_target_pos_when_negative": no_pos[len(no_pos) // 2] if no_pos else None,
    }
    ey, ly = direction["positive_verdicts_target_pos_1_2"], \
        direction["positive_verdicts_target_pos_3plus"]
    en, ln = direction["negative_verdicts_target_pos_1_2"], \
        direction["negative_verdicts_target_pos_3plus"]
    direction["first_position_preference_detected"] = bool(
        direction["median_target_pos_when_positive"] is not None
        and direction["median_target_pos_when_negative"] is not None
        and direction["median_target_pos_when_positive"]
        < direction["median_target_pos_when_negative"]
        and ey / max(1, ey + ly) > en / max(1, en + ln))

    return {
        "probe": "H6845 addendum-set paired recompute (h5010_order_paired raws)",
        "n_items": n,
        "n_invalid": len(invalid),
        "invalid": invalid,
        "axis_flips": {
            "caught": sum(1 for r in rows if r["caught_flip"]),
            "type_correct": sum(1 for r in rows if r["type_correct_flip"]),
            "false_positives": sum(1 for r in rows if r["fp_flip"]),
            "discordant": k,
        },
        "discordant_pairs": k,
        "discordant_runs": [r["run"] for r in rows if r["discordant"]],
        "flip_rate": round(k / n, 6) if n else None,
        "flip_rate_wilson95": wilson95(k, n),
        "directional_first_position": direction,
        "rows": rows,
    }


def parity_addendum(recomputed: dict, committed: dict) -> dict:
    checks = {}
    for key in ("n_items", "n_invalid", "discordant_pairs"):
        checks[key] = recomputed.get(key) == committed.get(key)
    for axis in ("caught", "type_correct", "false_positives"):
        mine = recomputed["axis_flips"][axis]
        committed_key = {"caught": "caught_flip",
                         "type_correct": "type_correct_flip",
                         "false_positives": "fp_flip"}[axis]
        theirs = sum(1 for r in committed["rows"] if r[committed_key])
        checks[f"axis_{axis}"] = mine == theirs
    checks["wilson95"] = [round(x, 4) for x in recomputed["flip_rate_wilson95"]] \
        == [round(x, 4) for x in committed["flip_rate_wilson95"]]
    cd = committed.get("directional_first_position", {})
    for key in ("positive_verdicts_target_pos_1_2",
                "positive_verdicts_target_pos_3plus",
                "negative_verdicts_target_pos_1_2",
                "negative_verdicts_target_pos_3plus",
                "median_target_pos_when_positive",
                "median_target_pos_when_negative",
                "first_position_preference_detected"):
        checks[f"directional.{key}"] = \
            recomputed["directional_first_position"].get(key) == cd.get(key)
    run_diffs = []
    mine = {r["run"]: r for r in recomputed["rows"]}
    for r in committed["rows"]:
        m = mine.get(r["run"])
        if m and m["discordant"] != r["discordant"]:
            run_diffs.append(r["run"])
    checks["per_run_discordance"] = not run_diffs
    return {"parity": all(checks.values()), "checks": checks,
            "per_run_discordance_diffs": run_diffs}


# ----------------------------------------------------- 2. length correlation

def length_correlation(sheet: dict, rater_files: list) -> dict:
    runs = {r["run"]: r for r in sheet["runs"]}
    axes = {}
    for path in rater_files:
        name = Path(path).name
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        verdicts = {v["run"]: v for v in data["runs"]}
        lens = {"chars": [], "words": [], "n_findings": []}
        scores = {"caught": [], "type_correct": [], "false_positives": []}
        for run_id, v in sorted(verdicts.items()):
            run = runs[run_id]
            # judged answer = the run's findings output (H4658 answer_length
            # definition); verbosity bias is about the judged text's length
            text = " ".join(str(f.get("finding", ""))
                            for f in run.get("findings", []))
            lens["chars"].append(len(text))
            lens["words"].append(len(text.split()))
            lens["n_findings"].append(len(run["findings"]))
            scores["caught"].append(1 if v["caught"] == "yes" else 0)
            scores["type_correct"].append(1 if v["type_correct"] else 0)
            scores["false_positives"].append(int(v["false_positives"]))
        for sname, svals in scores.items():
            for lname, lvals in lens.items():
                rho, reason = spearman(svals, lvals)
                pos = [lv for sv, lv in zip(svals, lvals) if sv > 0]
                neg = [lv for sv, lv in zip(svals, lvals) if sv <= 0]
                key = f"{name}_{sname}~{lname}"
                axes[key] = {
                    "spearman_rho": rho,
                    "undefined_reason": reason,
                    "n": len(svals),
                    "group_means": {
                        f"positive_mean_{lname}":
                            round(sum(pos) / len(pos), 1) if pos else None,
                        f"nonpositive_mean_{lname}":
                            round(sum(neg) / len(neg), 1) if neg else None,
                        "n_positive": len(pos),
                    },
                }
    finite = {k: v["spearman_rho"] for k, v in axes.items()
              if v["spearman_rho"] is not None}
    max_key = max(finite, key=lambda k: abs(finite[k])) if finite else None
    return {
        "probe": "H6845 judge-score vs answer-length re-derivation (zero calls)",
        "n_runs": len(runs),
        "rater_files": [Path(p).name for p in rater_files],
        "axes": axes,
        "max_abs_rho": {"axis": max_key,
                        "rho": finite.get(max_key) if max_key else None},
    }


def parity_length(recomputed: dict, h4658: dict) -> dict:
    committed = h4658["length_bias"]["axes"]
    checks, diffs = {}, {}
    for key, mine in recomputed["axes"].items():
        if key not in committed:
            continue
        theirs = committed[key]
        if mine["spearman_rho"] is None and theirs["spearman_rho"] is None:
            checks[key] = True
            continue
        if mine["spearman_rho"] is None or theirs["spearman_rho"] is None:
            checks[key] = False
            diffs[key] = (mine["spearman_rho"], theirs["spearman_rho"])
            continue
        checks[key] = abs(mine["spearman_rho"] - theirs["spearman_rho"]) <= 1e-3
        if not checks[key]:
            diffs[key] = (mine["spearman_rho"], theirs["spearman_rho"])
    return {"parity": all(checks.values()) if checks else False,
            "checks": checks, "diffs": diffs,
            "n_compared": len(checks)}


# ------------------------------------------------------ 3. self-preference

def self_preference(records: list, judge: str, perms: int = 10000,
                    seed: int = 6845) -> dict:
    """Own-family favouritism screen. Records need judged_by, produced_by
    (family label), score. Fail-closed: no provenance -> UNMEASURED."""
    sub = [r for r in records if r.get("judged_by") == judge
           and r.get("produced_by") and isinstance(r.get("score"), (int, float))]
    if not records:
        return {"status": "UNMEASURED",
                "reason": "no graded records supplied"}
    missing = [k for k in ("judged_by", "produced_by", "score")
               if all(k not in r for r in records)]
    if missing or not sub:
        return {"status": "UNMEASURED",
                "reason": "graded artifacts carry no (judged_by, produced_by, "
                          "score) provenance fields; measuring the screen on "
                          "real data needs new judged calls — outside this "
                          "handoff's $0.00 spend cap",
                "missing_fields": missing, "n_records": len(records)}
    own = [r["score"] for r in sub
           if r["produced_by"].split("-")[0].lower()
           in judge.lower() or r["produced_by"].lower() in judge.lower()]
    # family match: shared first token OR explicit substring either way
    def same_family(a: str, b: str) -> bool:
        fa, fb = a.lower().split("-")[0], b.lower().split("-")[0]
        return fa == fb or fa in b.lower() or fb in a.lower()
    own = [r["score"] for r in sub if same_family(r["produced_by"], judge)]
    other = [r["score"] for r in sub if not same_family(r["produced_by"], judge)]
    if not own or not other:
        return {"status": "UNMEASURED",
                "reason": f"no within-judge contrast available "
                          f"(own={len(own)}, other={len(other)})",
                "n_judged": len(sub)}
    delta = sum(own) / len(own) - sum(other) / len(other)
    rng = random.Random(seed)
    pooled = own + other
    n_own = len(own)
    extremes = 0
    for _ in range(perms):
        rng.shuffle(pooled)
        d = sum(pooled[:n_own]) / n_own - sum(pooled[n_own:]) / len(pooled[n_own:])
        if abs(d) >= abs(delta) - 1e-12:
            extremes += 1
    p = (extremes + 1) / (perms + 1)
    return {
        "status": "MEASURED",
        "judge": judge,
        "n_own": n_own, "n_other": len(other),
        "mean_own": round(sum(own) / n_own, 4),
        "mean_other": round(sum(other) / len(other), 4),
        "delta_own_minus_other": round(delta, 4),
        "permutation_p_two_sided": round(p, 5),
        "perms": perms, "seed": seed,
        "verdict": "self-preference signal detected" if p < 0.05
                   else "no self-preference signal at p<0.05",
    }


# ------------------------------------------------------------------- selftest

def _synthetic_sheet(n=25):
    return {"runs": [
        {"run": f"synth-{i:02d}",
         "purpose": "t", "required_finding_types": ["x"],
         "accepted_finding_aliases": {}, "input_text": "текст " * (i + 1),
         "findings": [{"id": f"f{i}-{j}", "type": "x", "severity": "minor",
                       "span_id": f"s{j}", "finding": "detail " * (i + 1)}
                      for j in range((i // 8) + 1)]}
        for i in range(n)]}


def selftest() -> dict:
    results = {}

    # --- recompute-addendum controls
    rng = random.Random(7)
    for label, plant in (("positive", True), ("negative", False)):
        sheet = _synthetic_sheet()
        mapping, responses = [], []
        for i, run in enumerate(sheet["runs"]):
            for cond in ("original", "reversed"):
                task = f"task-{len(responses)+1:03d}"
                discordant = plant and i == 3 and cond == "reversed"
                responses.append({
                    "task": task,
                    "caught": "no" if discordant else "yes",
                    "type_correct": not discordant,
                    "false_positives": 1 if discordant else 0,
                    "notes": ""})
                mapping.append({"task": task, "run": run["run"],
                                "condition": cond,
                                "n_findings": len(run["findings"])})
        rng.shuffle(mapping)
        res = recompute_addendum(mapping, responses, sheet)
        want = 1 if plant else 0
        ok = (res["discordant_pairs"] == want and res["n_invalid"] == 0
              and res["flip_rate"] == want / 25)
        results[f"addendum_{label}_control"] = \
            "PASS" if ok else f"FAIL (got {res['discordant_pairs']}, want {want})"

    # --- length-correlation controls
    sheet = _synthetic_sheet()
    rater = {"rater_b": "synthetic", "runs": [
        {"run": r["run"], "caught": "yes",
         "type_correct": (i % 2 == 0), "false_positives": i}
        for i, r in enumerate(sheet["runs"])]}
    lc = length_correlation(sheet, [])
    # planted: false_positives grows with i, input length grows with i -> |rho| high
    rater_path_ok = True
    fp_axis = None
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "synth_rater.json"
        p.write_text(json.dumps(rater), encoding="utf-8")
        lc = length_correlation(sheet, [str(p)])
        fp_axis = lc["axes"]["synth_rater.json_false_positives~chars"]
        rater_path_ok = fp_axis["spearman_rho"] is not None \
            and abs(fp_axis["spearman_rho"]) > 0.9
    deg = spearman([1, 1, 1], [1, 2, 3])
    results["length_planted_monotone"] = "PASS" if rater_path_ok \
        else f"FAIL (rho={fp_axis['spearman_rho'] if fp_axis else None})"
    results["length_degenerate_constant"] = "PASS" if deg[0] is None \
        else f"FAIL (got {deg[0]})"

    # --- self-preference controls
    records = []
    for i in range(40):
        fam = "glm" if i % 2 == 0 else "claude"
        score = 3 if fam == "glm" else 2  # judge=glm-family favours own family
        records.append({"judged_by": "glm-judge", "produced_by": f"{fam}-x",
                        "score": score})
    pos = self_preference(records, "glm-judge", perms=2000)
    results["selfpref_positive_control"] = \
        "PASS" if pos["status"] == "MEASURED" and pos["permutation_p_two_sided"] < 0.05 \
        else f"FAIL (p={pos.get('permutation_p_two_sided')})"
    for r in records:
        r["score"] = 2  # family-independent
    neg = self_preference(records, "glm-judge", perms=2000)
    results["selfpref_negative_control"] = \
        "PASS" if neg["status"] == "MEASURED" and neg["permutation_p_two_sided"] >= 0.05 \
        else f"FAIL (p={neg.get('permutation_p_two_sided')})"
    unmeasured = self_preference([{"run": "x", "caught": "yes"}], "glm-judge")
    results["selfpref_unmeasured_failclosed"] = \
        "PASS" if unmeasured["status"] == "UNMEASURED" else "FAIL"

    ok = all(v == "PASS" for v in results.values())
    return {"selftest": "PASS" if ok else "FAIL", "controls": results}


# ------------------------------------------------------------------------ CLI

def cmd_recompute(args) -> int:
    d = Path(args.dir)
    sheet = json.loads(Path(args.sheet).read_text(encoding="utf-8"))
    mapping = json.loads((d / "mapping_hidden.json").read_text(encoding="utf-8"))
    responses = json.loads(
        (d / "responses_raw.json").read_text(encoding="utf-8"))["responses"]
    res = recompute_addendum(mapping, responses, sheet)
    committed = json.loads(
        (d / "order_paired_analysis.json").read_text(encoding="utf-8"))
    res["parity_vs_committed"] = parity_addendum(res, committed)
    out = {"probe": res["probe"], "date": args.date, "n_items": res["n_items"],
           "n_invalid": res["n_invalid"], "axis_flips": res["axis_flips"],
           "discordant_pairs": res["discordant_pairs"],
           "discordant_runs": res["discordant_runs"],
           "flip_rate": res["flip_rate"],
           "flip_rate_wilson95": res["flip_rate_wilson95"],
           "directional_first_position": res["directional_first_position"],
           "parity_vs_committed": res["parity_vs_committed"],
           "rows": res["rows"]}
    if args.out:
        Path(args.out).write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    p = res["parity_vs_committed"]
    print(f"recompute-addendum: n={res['n_items']} discordant="
          f"{res['discordant_pairs']}/25 wilson={res['flip_rate_wilson95']} "
          f"parity={'PASS' if p['parity'] else 'FAIL'} "
          f"({sum(p['checks'].values())}/{len(p['checks'])} checks)")
    return 0 if p["parity"] and res["n_invalid"] == 0 else 1


def cmd_length(args) -> int:
    sheet = json.loads(Path(args.sheet).read_text(encoding="utf-8"))
    res = length_correlation(sheet, args.raters)
    if args.compare:
        h4658 = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        res["parity_vs_h4658"] = parity_length(res, h4658)
    res["date"] = args.date
    if args.out:
        Path(args.out).write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    p = res.get("parity_vs_h4658", {})
    print(f"length-correlation: max|rho|={res['max_abs_rho']} "
          f"parity={'PASS' if p.get('parity') else 'FAIL'} "
          f"({p.get('n_compared', 0)} axes compared)")
    return 0 if p.get("parity") else 1


def cmd_selfpref(args) -> int:
    records = json.loads(Path(args.records).read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = records.get("records") or records.get("runs") or []
    res = self_preference(records, args.judge, perms=args.perms)
    res["date"] = args.date
    res["records_source"] = args.records
    if args.out:
        Path(args.out).write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"self-preference: {res['status']} "
          f"{res.get('delta_own_minus_other', '')} "
          f"{res.get('verdict', res.get('reason', ''))[:80]}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("recompute-addendum",
                       help="independent paired recompute of the H5010 addendum set")
    p.add_argument("--dir", default=ADDENDUM_DIR_DEFAULT)
    p.add_argument("--sheet", default=SHEET_DEFAULT)
    p.add_argument("--out")
    p.add_argument("--date", default="2026-10-22")
    p.set_defaults(func=cmd_recompute)

    p = sub.add_parser("length-correlation",
                       help="judge-verdict vs length Spearman from committed raters")
    p.add_argument("--sheet", default=SHEET_DEFAULT)
    p.add_argument("--raters", nargs="+", default=RATERS_DEFAULT)
    p.add_argument("--compare", default=H4658_JSON_DEFAULT)
    p.add_argument("--out")
    p.add_argument("--date", default="2026-10-22")
    p.set_defaults(func=cmd_length)

    p = sub.add_parser("self-preference",
                       help="own-family favouritism screen over graded records")
    p.add_argument("--records", required=True)
    p.add_argument("--judge", required=True)
    p.add_argument("--perms", type=int, default=10000)
    p.add_argument("--out")
    p.add_argument("--date", default="2026-10-22")
    p.set_defaults(func=cmd_selfpref)

    p = sub.add_parser("selftest", help="offline controls, no model calls")
    p.set_defaults(func=lambda a: _print_selftest())

    args = ap.parse_args(argv)
    return args.func(args)


def _print_selftest() -> int:
    res = selftest()
    print(json.dumps(res, indent=1))
    return 0 if res["selftest"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
