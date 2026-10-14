"""Structured outputs: results.json, results.csv (Excel-friendly), summary.md."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .schemas import DocumentResult, FieldStatus

CSV_COLUMNS = [
    "document_id",
    "row_id",
    "qty",
    "raw_text",
    "confidence",
    "status",
    "needs_review",
    "review_reasons",
    "preprocessing_variant",
    "crop_path",
]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def csv_rows(doc: DocumentResult) -> list[dict[str, Any]]:
    return [
        {
            "document_id": doc.document_id,
            "row_id": f.row_id,
            "qty": f.value if f.value is not None else "",
            "raw_text": f.raw_text if f.raw_text is not None else "",
            "confidence": f"{f.confidence:.4f}" if f.confidence is not None else "",
            "status": f.status.value,
            "needs_review": "TRUE" if f.needs_review else "FALSE",
            "review_reasons": "; ".join(f.review_reasons),
            "preprocessing_variant": f.preprocessing_variant or "",
            "crop_path": f.crop_path or "",
        }
        for f in doc.fields
    ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """UTF-8 with BOM so Excel opens Thai text and leading zeros as text correctly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            # Excel strips leading zeros from numbers; keep "007" as text.
            if row["qty"] and row["qty"].startswith("0") and len(row["qty"]) > 1:
                row = {**row, "qty": f'="{row["qty"]}"'}
            writer.writerow(row)


def summary_markdown(doc: DocumentResult) -> str:
    counts: dict[str, int] = {}
    for f in doc.fields:
        counts[f.status.value] = counts.get(f.status.value, 0) + 1
    lines = [
        f"# OCR summary — {doc.document_id}",
        "",
        f"- Template: `{doc.template_id}`",
        f"- Model: `{doc.model}`",
        f"- Document status: **{doc.status}**",
        f"- Image: {doc.image_width} x {doc.image_height}",
        f"- Alignment: {doc.alignment.get('method')} "
        f"(success={doc.alignment.get('success')}, fallback={doc.alignment.get('used_fallback')})",
        f"- Field status counts: {', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}",
        "",
        "> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง",
        "",
        "| row | qty | confidence | status | variant | review reasons |",
        "|---:|---|---:|---|---|---|",
    ]
    for f in doc.fields:
        qty = f.value if f.value is not None else ("_blank_" if f.status == FieldStatus.BLANK else "—")
        conf = f"{f.confidence:.3f}" if f.confidence is not None else ""
        lines.append(
            f"| {f.row_id} | {qty} | {conf} | {f.status.value} | {f.preprocessing_variant or ''} | "
            f"{'; '.join(f.review_reasons)} |"
        )
    lines += ["", "## Timings (ms)", ""]
    lines += [f"- {k}: {v:.1f}" for k, v in doc.timings_ms.items()]
    if doc.errors:
        lines += ["", "## Errors", ""] + [f"- {e}" for e in doc.errors]
    return "\n".join(lines) + "\n"


def export_document(doc: DocumentResult, out_dir: Path, save_json: bool = True, save_csv: bool = True) -> None:
    if save_json:
        write_json(out_dir / "results.json", doc.to_dict())
    if save_csv:
        write_csv(out_dir / "results.csv", csv_rows(doc))
    (out_dir / "summary.md").write_text(summary_markdown(doc), encoding="utf-8")
