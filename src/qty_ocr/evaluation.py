"""Evaluation against ground truth.

Ground-truth format (``data/ground_truth/annotations.example.json``)::

    {
      "verified": true,
      "documents": {
        "order_form_01": {"1": "15", "2": "23", "7": null}
      }
    }

``null`` means the cell is truly blank. Metrics are refused unless the file
declares ``"verified": true`` — draft labels must never be reported as accuracy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class UnverifiedGroundTruthError(ValueError):
    """Ground truth is a draft; accuracy must not be reported."""


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@dataclass
class EvalReport:
    n_fields: int = 0
    n_gt_nonblank: int = 0
    exact_match: int = 0
    char_errors: int = 0
    gt_chars: int = 0
    blank_confusion: dict[str, int] = field(
        default_factory=lambda: {"tp_blank": 0, "fp_blank": 0, "fn_blank": 0, "tn_blank": 0}
    )
    mismatches: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        bc = self.blank_confusion
        nonblank_total = bc["tn_blank"] + bc["fp_blank"]
        blank_total = bc["tp_blank"] + bc["fn_blank"]
        return {
            "n_fields": self.n_fields,
            "exact_match_accuracy": round(self.exact_match / self.n_fields, 4) if self.n_fields else None,
            "cer_nonblank": round(self.char_errors / self.gt_chars, 4) if self.gt_chars else None,
            "blank_confusion": bc,
            # GT nonblank predicted blank (handwriting lost)
            "nonblank_predicted_blank_rate": round(bc["fp_blank"] / nonblank_total, 4) if nonblank_total else None,
            # GT blank predicted with text (hallucination)
            "blank_predicted_nonblank_rate": round(bc["fn_blank"] / blank_total, 4) if blank_total else None,
            "mismatches": self.mismatches,
        }


def load_ground_truth(path: str | Path, allow_unverified: bool = False) -> dict[str, dict[int, str | None]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not data.get("verified", False) and not allow_unverified:
        raise UnverifiedGroundTruthError(
            f"{path} is not marked \"verified\": true — refusing to report accuracy on draft labels"
        )
    return {
        doc_id: {int(k): (None if v is None else str(v)) for k, v in rows.items()}
        for doc_id, rows in data["documents"].items()
    }


def evaluate(predictions: list[dict[str, Any]], gt: dict[str, dict[int, str | None]]) -> EvalReport:
    """Compare ``results.json`` payloads with ground truth (only documents present in both)."""
    rep = EvalReport()
    for pred in predictions:
        doc_gt = gt.get(pred["document_id"])
        if doc_gt is None:
            continue
        by_row = {f["row_id"]: f for f in pred["fields"]}
        for row_id, truth in doc_gt.items():
            f = by_row.get(row_id)
            value = f.get("value") if f else None
            pred_blank = bool(f and f.get("is_blank"))
            rep.n_fields += 1
            if truth is None:
                rep.blank_confusion["tp_blank" if pred_blank else "fn_blank"] += 1
            else:
                rep.n_gt_nonblank += 1
                rep.blank_confusion["fp_blank" if pred_blank else "tn_blank"] += 1
                rep.gt_chars += len(truth)
                rep.char_errors += levenshtein(value or "", truth)
            if value == truth:
                rep.exact_match += 1
            else:
                rep.mismatches.append(
                    {"document_id": pred["document_id"], "row_id": row_id, "truth": truth,
                     "prediction": value, "status": f.get("status") if f else "missing"}
                )
    return rep
