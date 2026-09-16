#!/usr/bin/env python3
"""H5010 — same-judge paired position-bias experiment on the h073gov lane.

Subcommands:
  build     Construct 50 identity-blinded presentations (25 ORIG + 25 REV) in a
            seeded shuffled call order + the hidden arm mapping.
  analyze   Join raw blinded judgments with the mapping, compute paired
            discordance / first-position statistics, emit machine JSON.
  selftest  Offline positive/negative controls (no model calls): a known
            first-position selector must be detected; an order-invariant judge
            must stay invariant after mapping candidate identities back.

Stdlib only. Protocol: evals/probes/POSITION_PAIR_PROTOCOL_h5010_2026-09-17.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHEET = REPO / "evals/annotation/sheet-h073gov.json"
SEED = 5010
PROTO = "evals/probes/POSITION_PAIR_PROTOCOL_h5010_2026-09-17.md"


def norm_text(s: str) -> str:
    return " ".join(s.split())


def finding_key(text: str) -> str:
    return hashlib.sha256(norm_text(text).encode("utf-8")).hexdigest()[:16]


def canonical_first_pos(run: dict) -> int:
    """1-based position of the first finding bearing a required type or alias."""
    req = set(run.get("required_finding_types") or [])
    aliases = run.get("accepted_finding_aliases") or {}
    allowed = set(req)
    for canon, al in aliases.items():
        if canon in req:
            allowed.update(al)
    for i, f in enumerate(run["findings"], start=1):
        if f.get("type") in allowed:
            return i
    return 0  # no canonical finding present


def build(out_dir: Path) -> None:
    sheet = json.loads(SHEET.read_text(encoding="utf-8"))
    presentations, mapping = [], []
    for run in sheet["runs"]:
        n = len(run["findings"])
        for arm, order in (("ORIG", list(range(n))), ("REV", list(range(n))[::-1])):
            findings = [
                {
                    "pos": j + 1,
                    "type": run["findings"][k]["type"],
                    "finding": run["findings"][k]["finding"],
                    "_key": finding_key(run["findings"][k]["finding"]),
                }
                for j, k in enumerate(order)
            ]
            presentations.append(
                {
                    "input_text": run["input_text"],
                    "case_purpose": run["purpose"],
                    "required_finding_types": run["required_finding_types"],
                    "accepted_finding_aliases": run.get("accepted_finding_aliases", {}),
                    "findings": findings,
                }
            )
            mapping.append(
                {
                    "run": run["run"],
                    "arm": arm,
                    "n_findings": n,
                    "target_pos": canonical_first_pos(run) if arm == "ORIG"
                    else (n + 1 - canonical_first_pos(run) if canonical_first_pos(run) else 0),
                    "finding_order_keys": [f["_key"] for f in findings],
                }
            )
    rng = random.Random(SEED)
    idx = list(range(len(presentations)))
    rng.shuffle(idx)
    blinded = []
    call_order = []
    for new_i, old_i in enumerate(idx, start=1):
        pres = dict(presentations[old_i])
        pres["pres_id"] = f"P{new_i:02d}"
        blinded.append(pres)
        call_order.append(old_i)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "presentations.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in blinded) + "\n",
        encoding="utf-8",
    )
    hidden = {m["run"]: m for m in mapping}
    (out_dir / "mapping.json").write_text(
        json.dumps(
            {
                "seed": SEED,
                "protocol": PROTO,
                "call_order_presentations": [f"P{i+1:02d}" for i in idx],
                "by_pres": {
                    f"P{pos+1:02d}": mapping[old_i] for pos, old_i in enumerate(idx)
                },
                "_by_run_hidden": hidden,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"built {len(blinded)} presentations, seed={SEED}, out={out_dir}")


# ---------------------------------------------------------------- statistics --
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple:
    if n == 0:
        return (0.0, 0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, max(0.0, (c - h) / d), min(1.0, (c + h) / d))


CAUGHT_RANK = {"no": 0, "partial": 1, "yes": 2}


def pair_stats(orig: dict, rev: dict) -> dict:
    caught_o, caught_r = str(orig["caught"]).lower(), str(rev["caught"]).lower()
    tc_o, tc_r = bool(orig["type_correct"]), bool(rev["type_correct"])
    fp_o, fp_r = int(orig["false_positives"]), int(rev["false_positives"])
    return {
        "caught_any_flip": caught_o != caught_r,
        "caught_adjacent_flip": abs(CAUGHT_RANK.get(caught_o, -1) - CAUGHT_RANK.get(caught_r, -1)) == 1
        and caught_o != caught_r,
        "type_correct_flip": tc_o != tc_r,
        "fp_delta": fp_r - fp_o,
        "fp_flip": fp_o != fp_r,
    }


def analyze(judgments_path: Path, mapping_path: Path, out_path: Path) -> dict:
    judgments = json.loads(judgments_path.read_text(encoding="utf-8"))
    mp = json.loads(mapping_path.read_text(encoding="utf-8"))
    by_pres = mp["by_pres"]
    rows, invalid = [], []
    for pid, m in by_pres.items():
        j = judgments.get(pid)
        if not j or "caught" not in j:
            invalid.append(pid)
            continue
        rows.append((m["run"], m["arm"], m["target_pos"], pid, j))
    runs = {}
    for run, arm, tpos, pid, j in rows:
        runs.setdefault(run, {})[arm] = (tpos, pid, j)
    n = 0
    agg = {
        "caught_any": 0, "caught_adjacent": 0, "type_correct": 0, "fp": 0,
        "discords_first_pos_pref": 0, "discords_directional": 0,
    }
    per_run = {}
    for run, arms in sorted(runs.items()):
        if "ORIG" not in arms or "REV" not in arms:
            invalid.append(run)
            continue
        (tp_o, po, jo), (tp_r, pr, jr) = arms["ORIG"], arms["REV"]
        st = pair_stats(jo, jr)
        st.update({"run": run, "target_pos_orig": tp_o, "target_pos_rev": tp_r,
                   "pres_orig": po, "pres_rev": pr})
        per_run[run] = st
        n += 1
        for key in ("caught_any", "caught_adjacent", "type_correct", "fp"):
            if st["caught_any_flip" if key == "caught_any" else
                  ("caught_adjacent_flip" if key == "caught_adjacent" else
                   ("type_correct_flip" if key == "type_correct" else "fp_flip"))]:
                agg[key] += 1
        if st["type_correct_flip"]:
            fav_orig = bool(jo["type_correct"])
            if tp_o and tp_r:
                early_orig = tp_o <= tp_r
                agg["discords_directional"] += 1
                if fav_orig == early_orig:
                    agg["discords_first_pos_pref"] += 1
    stats = {}
    for key in ("caught_any", "caught_adjacent", "type_correct", "fp"):
        p, lo, hi = wilson(agg[key], n)
        stats[key] = {"flips": agg[key], "n": n, "rate": round(p, 4),
                      "wilson95": [round(lo, 4), round(hi, 4)]}
    result = {
        "protocol": PROTO,
        "judge": "glm-5.3-flash (z-ai, opencode/zai-coding-plan/glm-5.3-flash)",
        "seed": SEED,
        "denominator": n,
        "invalid": sorted(set(invalid)),
        "primary": stats,
        "directional_first_position": {
            "discordant_type_correct_pairs": agg["discords_directional"],
            "favours_earlier_target_position": agg["discords_first_pos_pref"],
        },
        "per_run": per_run,
        "threshold": "concern if rate >= 0.20 or wilson95 lower > 0.10 on caught_any/type_correct",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    conc = []
    for key in ("caught_any", "type_correct"):
        s = stats[key]
        conc.append(f"{key}: {s['flips']}/{s['n']} (Wilson95 {s['wilson95']})")
    print("analyze:", "; ".join(conc))
    if result["invalid"]:
        print("INVALID:", result["invalid"])
    return result


# ------------------------------------------------------------------ controls --
def selftest() -> int:
    failures = []

    # ---- negative control: order-invariant judge -> zero flips ----
    def invariant_judge(pres: dict) -> dict:
        on_target = any(
            f["type"] in set(pres["required_finding_types"])
            | {a for al in pres.get("accepted_finding_aliases", {}).values() for a in al}
            for f in pres["findings"]
        )
        return {"caught": "yes" if on_target else "no",
                "type_correct": on_target, "false_positives": 0}

    inv_flip, n_inv = 0, 0
    for a, b in _synth_pairs():
        if pair_stats(invariant_judge(a), invariant_judge(b))["type_correct_flip"] or \
           pair_stats(invariant_judge(a), invariant_judge(b))["caught_any_flip"]:
            inv_flip += 1
        n_inv += 1
    if inv_flip != 0:
        failures.append(f"negative control: order-invariant judge flipped {inv_flip}/{n_inv}")

    # identity mapping back: reversed presentation's findings must map 1:1 onto orig
    for a, b in _synth_pairs():
        ka = sorted(f["_key"] for f in a["findings"])
        kb = sorted(f["_key"] for f in b["findings"])
        if ka != kb:
            failures.append("negative control: identity mapping back failed")

    # ---- positive control: known first-position selector -> detected ----
    def firstpos_judge(pres: dict) -> dict:
        req = set(pres["required_finding_types"])
        al = {x for v in pres.get("accepted_finding_aliases", {}).values() for x in v}
        first = pres["findings"][0]
        hit = first["type"] in (req | al)
        return {"caught": "yes" if hit else "no", "type_correct": hit, "false_positives": 0}

    pos_flips, n_pos, pref = 0, 0, 0
    for a, b in _synth_pairs():
        st = pair_stats(firstpos_judge(a), firstpos_judge(b))
        if st["caught_any_flip"]:
            pos_flips += 1
            ja, jb = firstpos_judge(a), firstpos_judge(b)
            ta, tb = _target_pos(a), _target_pos(b)
            if ta and tb and bool(ja["type_correct"]) == (ta <= tb):
                pref += 1
        n_pos += 1
    if pos_flips < n_pos * 0.5 or pref == 0:
        failures.append(
            f"positive control: first-position selector under-detected (flips {pos_flips}/{n_pos}, pref {pref})"
        )

    if failures:
        for f in failures:
            print("SELFTEST FAIL:", f)
        return 1
    print(f"SELFTEST PASS: negative control invariant {n_inv}/{n_inv}, "
          f"positive control detected {pos_flips}/{n_pos} flips, first-pos preference {pref}")
    return 0


def _target_pos(pres: dict) -> int:
    req = set(pres["required_finding_types"])
    al = {x for v in pres.get("accepted_finding_aliases", {}).values() for x in v}
    for i, f in enumerate(pres["findings"], start=1):
        if f["type"] in (req | al):
            return i
    return 0


def _synth_pairs():
    """Deterministic synthetic ORIG/REV pairs covering hit-early, hit-late, miss."""
    base = {
        "case_purpose": "detect the planted error",
        "required_finding_types": ["planted_error"],
        "accepted_finding_aliases": {"planted_error": ["error_alias"]},
        "input_text": "text",
    }
    def mk(types):
        return dict(base, findings=[
            {"pos": i + 1, "type": t, "finding": f"{t} note",
             "_key": finding_key(f"{t} note")}
            for i, t in enumerate(types)
        ])
    cases = [
        ["planted_error", "style_a", "style_b"],
        ["style_a", "planted_error", "style_b"],
        ["style_a", "style_b", "planted_error"],
        ["style_a", "style_b", "error_alias"],
        ["style_a", "style_b"],
    ]
    for types in cases:
        a = mk(types)
        b = mk(list(reversed(types)))
        b["findings"] = [dict(f, pos=i + 1) for i, f in enumerate(b["findings"])]
        yield a, b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["build", "analyze", "selftest"])
    ap.add_argument("--out-dir", default="evals/probes/position_pair_h5010")
    ap.add_argument("--judgments", default="evals/annotation/glm-h073gov-paired-2026-09-17.json")
    ap.add_argument("--mapping", default="evals/probes/position_pair_h5010/mapping.json")
    ap.add_argument("--out", default="evals/probes/position-pair-h5010-2026-09-17.json")
    a = ap.parse_args()
    if a.cmd == "build":
        build(Path(a.out_dir))
        return 0
    if a.cmd == "analyze":
        analyze(Path(a.judgments), Path(a.mapping), Path(a.out))
        return 0
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
