"""Compare two result folders field by field (regression check for optimisations).

Each folder holds one sub-folder per document with a ``results.json`` (the
layout written by ``qty_ocr.cli batch`` / ``run``). A field matches when
``value``, ``status``, ``needs_review`` and ``review_reasons`` are identical and
``confidence`` differs by at most ``--score-tol``. Review reasons embed scores
rounded for display (e.g. ``low_confidence(0.649<0.85)``); those numbers are
compared numerically with ``score_tol`` plus one unit of the displayed precision,
because two scores 4e-5 apart can round to 0.833 / 0.834. ``--strict`` compares
the reason strings character by character instead.

Usage:
    python scripts/compare_results.py outputs/reference_scan outputs/candidate_scan
Exit code: 0 = identical, 1 = differences, 2 = missing documents / usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FIELD_KEYS = ("value", "status", "needs_review")
_NUM = re.compile(r"-?\d+\.\d+")


def load_folder(folder: Path) -> dict[str, dict[str, Any]]:
    docs: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("**/results.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        docs[data["document_id"]] = data
    return docs


def reasons_equal(a: list[str], b: list[str], tol: float, strict: bool = False) -> bool:
    if strict:
        return a == b
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if _NUM.sub("#", x) != _NUM.sub("#", y):
            return False
        for p, q in zip(_NUM.findall(x), _NUM.findall(y)):
            decimals = max(len(p.split(".")[1]), len(q.split(".")[1]))
            if abs(float(p) - float(q)) > tol + 10 ** (-decimals) + 1e-12:
                return False
    return True


def compare(base: dict[str, Any], cand: dict[str, Any], tol: float, strict: bool = False) -> list[str]:
    diffs: list[str] = []
    if base.get("status") != cand.get("status"):
        diffs.append(f"document status {base.get('status')!r} != {cand.get('status')!r}")
    bf = {f["row_id"]: f for f in base["fields"]}
    cf = {f["row_id"]: f for f in cand["fields"]}
    if set(bf) != set(cf):
        diffs.append(f"row sets differ: {sorted(bf)} vs {sorted(cf)}")
    for row in sorted(set(bf) & set(cf)):
        a, b = bf[row], cf[row]
        for k in FIELD_KEYS:
            if a.get(k) != b.get(k):
                diffs.append(f"row {row} {k}: {a.get(k)!r} != {b.get(k)!r}")
        if not reasons_equal(a.get("review_reasons", []), b.get("review_reasons", []), tol, strict):
            diffs.append(f"row {row} review_reasons: {a.get('review_reasons')} != {b.get('review_reasons')}")
        ca, cb = a.get("confidence"), b.get("confidence")
        if (ca is None) != (cb is None) or (ca is not None and abs(ca - cb) > tol):
            diffs.append(f"row {row} confidence: {ca} != {cb}")
    return diffs


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("baseline", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("--score-tol", type=float, default=1e-3)
    p.add_argument("--strict", action="store_true", help="compare review_reasons as exact strings")
    args = p.parse_args()

    base, cand = load_folder(args.baseline), load_folder(args.candidate)
    if not base:
        print(f"no results.json under {args.baseline}", file=sys.stderr)
        return 2
    missing = sorted(set(base) - set(cand))
    extra = sorted(set(cand) - set(base))
    n_fields = n_same = 0
    n_diff_docs = 0
    for doc_id in sorted(set(base) & set(cand)):
        diffs = compare(base[doc_id], cand[doc_id], args.score_tol, args.strict)
        fields = len(base[doc_id]["fields"])
        bad_rows = {d.split()[1] for d in diffs if d.startswith("row ")}
        n_fields += fields
        n_same += fields - len(bad_rows)
        if diffs:
            n_diff_docs += 1
            print(f"[DIFF] {doc_id}")
            for d in diffs:
                print(f"    {d}")
    print(f"\ndocuments: {len(set(base) & set(cand))} compared, {n_diff_docs} with differences, "
          f"{len(missing)} missing, {len(extra)} extra")
    print(f"fields identical: {n_same}/{n_fields}")
    if missing:
        print(f"missing in candidate: {missing}")
    if missing:
        return 2
    return 1 if n_diff_docs else 0


if __name__ == "__main__":
    sys.exit(main())
