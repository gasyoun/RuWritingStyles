"""Generic-check audit for style passports (prompt-fidelity review F3).

A passport's `checks` are its machine-readable signature. A check shared by many
passports carries little signal about *which* style raised a finding, and the
council weights by style — so a passport whose checks are mostly shared is hard
to tell apart from its neighbours.

This reports, objectively and repeatably:
  - the frequency of every check across all passports;
  - which checks are "shared" (appear in >= THRESHOLD passports);
  - per passport, the share of its checks that are shared, flagging any passport
    over the SHARED_RATIO_FLAG line as a candidate to sharpen with a signature check.

It does NOT decide what the new checks should be — that is the author's domain
call. Run: `python tools/audit_passport_checks.py`.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ruwritingstyles.config import load_passport_dicts  # noqa: E402

THRESHOLD = 3          # a check in >= THRESHOLD passports is "shared"
SHARED_RATIO_FLAG = 0.5  # flag passports whose checks are >= 50% shared


def _checks(passport: dict) -> list[str]:
    return [c for c in (passport.get("checks") or []) if isinstance(c, str)]


def main() -> int:
    per_passport = {
        p.get("id", "?"): _checks(p) for p in load_passport_dicts(ROOT)
    }

    freq: Counter[str] = Counter()
    for checks in per_passport.values():
        freq.update(set(checks))  # count each check once per passport

    shared = {c for c, n in freq.items() if n >= THRESHOLD}

    print(f"Passports: {len(per_passport)}   distinct checks: {len(freq)}   "
          f"shared (>= {THRESHOLD} passports): {len(shared)}\n")

    print("Most shared checks (carry the least style signal):")
    for check, n in freq.most_common():
        if n < THRESHOLD:
            break
        print(f"  {n:>2}x  {check}")

    print("\nPer-passport shared-check ratio (flagged if >= "
          f"{int(SHARED_RATIO_FLAG * 100)}% shared):")
    flagged = []
    for pid in sorted(per_passport):
        checks = per_passport[pid]
        if not checks:
            print(f"  [!] {pid}: no checks")
            continue
        n_shared = sum(1 for c in checks if c in shared)
        ratio = n_shared / len(checks)
        mark = "  <-- sharpen" if ratio >= SHARED_RATIO_FLAG else ""
        if ratio >= SHARED_RATIO_FLAG:
            flagged.append(pid)
        signature = [c for c in checks if c not in shared] or ["(none — fully shared)"]
        print(f"  {ratio:5.0%} shared  {pid}{mark}")
        print(f"           signature checks: {', '.join(signature)}")

    print(f"\nFlagged for sharpening ({len(flagged)}): {', '.join(flagged) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
