"""Controlled preprocessing experiment (E1-E7) on one or more documents.

Runs every preprocessing variant *individually* through the same recogniser on
each nonblank qty crop and records prediction, score and time. Without
verified labels this shows agreement/disagreement only — not accuracy.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from .layout import locate_table
from .blank_detector import detect_blank, ink_group_masks
from .config import AppConfig
from .exporter import write_json
from .image_loader import load_image
from .postprocessing import is_valid_quantity, normalize_text
from .preprocessing import build_variants, digit_segments
from .recognizer import PaddleV5Recognizer
from .roi_extractor import extract_qty_cells
from .schemas import BlankLabel

EXPERIMENTS = [
    ("E1", "original"),
    ("E2", "grayscale"),
    ("E3", "red_mask"),
    ("E4", "adaptive_threshold"),
    ("E5", "tight_crop"),
    ("E6", "ink_isolation"),
    ("E7", "digit_segments"),
]


def run_experiment(images: list[Path], cfg: AppConfig, recognizer: PaddleV5Recognizer) -> list[dict[str, Any]]:
    all_on = replace(
        cfg.preprocessing, original=True, grayscale=True, red_mask=True,
        adaptive_threshold=True, tight_crop=True, ink_isolation=True,
    )
    rows: list[dict[str, Any]] = []
    for path in images:
        image = load_image(path)
        loc = locate_table(image.bgr, cfg, recognizer)
        align = loc.align
        if not align.success or align.aligned_bgr is None or align.grid is None or loc.qty is None:
            rows.append({"document_id": image.document_id, "error": "alignment_failed"})
            continue
        for cell in extract_qty_cells(align.aligned_bgr, align.grid, loc.qty.index, loc.header_rows, cfg.roi):
            stats, mask = detect_blank(cell.crop, cfg.blank_detection)
            if stats.label == BlankLabel.BLANK:
                continue
            variants = build_variants(cell.crop, all_on, stats.ink_bbox)
            bd = cfg.blank_detection
            segs = digit_segments(cell.crop, ink_group_masks(mask, bd.group_min_area, bd.group_min_height_ratio),
                                  cfg.preprocessing.tight_crop_padding_ratio)
            for exp_id, name in EXPERIMENTS:
                images = segs if name == "digit_segments" else ([variants[name]] if name in variants else [])
                if not images:
                    rows.append({"document_id": image.document_id, "row_id": cell.row_id,
                                 "experiment": exp_id, "variant": name, "skipped": "variant_not_applicable"})
                    continue
                t0 = time.perf_counter()
                rs = recognizer.recognize_batch(images)
                raw = "".join((r.raw_text or "").strip() for r in rs)
                digits = "".join(r.digit_text or "" for r in rs) if all(r.digit_text is not None for r in rs) else None
                norm, _ = normalize_text(raw)
                scores = [r.rec_score for r in rs if r.rec_score is not None]
                dscores = [r.digit_score for r in rs if r.digit_score is not None]
                rows.append({
                    "document_id": image.document_id,
                    "row_id": cell.row_id,
                    "experiment": exp_id,
                    "variant": name,
                    "raw_text": raw,
                    "rec_score": round(min(scores), 4) if scores else None,
                    "valid_numeric": is_valid_quantity(norm, cfg.field.min_digits, cfg.field.max_digits),
                    "digit_text": digits,
                    "digit_score": round(min(dscores), 4) if dscores else None,
                    "digit_valid": is_valid_quantity(digits, cfg.field.min_digits, cfg.field.max_digits),
                    "time_ms": round((time.perf_counter() - t0) * 1000, 1),
                    "error": "; ".join(r.error for r in rs if r.error) or None,
                })
    return rows


def experiment_markdown(rows: list[dict[str, Any]]) -> str:
    """Pivot: one line per (document, row), one column per experiment."""
    keys = sorted({(r["document_id"], r["row_id"]) for r in rows if "row_id" in r},
                  key=lambda k: (k[0], k[1]))
    exps = [e for e, _ in EXPERIMENTS]
    head = "| document | row | " + " | ".join(f"{e} {n}" for e, n in EXPERIMENTS) + " | agree |"
    lines = [head, "|" + "---|" * (len(EXPERIMENTS) + 3)]
    lookup = {(r["document_id"], r.get("row_id"), r.get("experiment")): r for r in rows}
    for doc_id, row_id in keys:
        cells, texts = [], set()
        for e in exps:
            r = lookup.get((doc_id, row_id, e))
            if r is None or r.get("skipped"):
                cells.append("n/a")
                continue
            mark = "" if r["valid_numeric"] else " ✗"
            dig = f" → `{r['digit_text']}`" if r.get("digit_text") is not None and r["digit_text"] != r["raw_text"] else ""
            cells.append(f"`{r['raw_text']}` {(r['rec_score'] or 0):.2f}{mark}{dig}")
            final = r.get("digit_text") if r.get("digit_text") is not None else r["raw_text"]
            if r.get("digit_valid", r["valid_numeric"]):
                texts.add(final)
        lines.append(f"| {doc_id} | {row_id} | " + " | ".join(cells) + f" | {'yes' if len(texts) == 1 else 'NO'} |")
    return "\n".join(lines) + "\n"


def save_experiment(rows: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "experiment.json", {"rows": rows})
    (out_dir / "experiment.md").write_text(experiment_markdown(rows), encoding="utf-8")
