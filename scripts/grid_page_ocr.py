"""Cut every handwritten number off a free-form grid page and read each one with PP-OCRv5.

The page is plain paper (no table lines): numbers are found as ink blobs, grouped
into one box per number, sorted into columns (x) then rows (y). Each number then goes
through the same per-cell steps as the main pipeline (``configs/changhouse.yaml``):

    detect_blank -> tight_crop (+ digit_segments when >= 2 ink groups)
    -> PP-OCRv5_server_rec (ONNX Runtime, digit-constrained decoding)
    -> postprocessing.decide (merged-digit recovery, segment cross-check, review reasons)

Crops are taken from a lighting-flattened page: on a phone photo the paper is grey
(~170), and tight_crop's white border around a grey patch looks like a box that the
model reads as "□", "口" or "日". Measured on IMG_9328 (150 numbers, tight_crop only):
mean digit score 0.48 -> 0.71 with flattening.

Usage:
    python scripts/grid_page_ocr.py --input "../Data Test/test-1-page/IMG_9328.jpg" \
        --output outputs/IMG_9328_grid --cols 10 --rows 15 \
        --reading data/ground_truth/IMG_9328.claude_reading_unverified.json

Outputs (in --output):
    overlay.jpg            whole page, each number boxed with the system's answer beside it
    sheet_1..N.png         every model input image, large, with answer / score / reading
    crops/rRR_cCC*.png     the exact images given to the model (tight crop, digit segments)
    results.csv / .json    one row per number (an empty ``gt`` column is left for a human)
    summary.md             counts and the list of cells to check
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ROTATIONS = {
    "none": None,
    "cw": cv2.ROTATE_90_CLOCKWISE,
    "ccw": cv2.ROTATE_90_COUNTERCLOCKWISE,
    "180": cv2.ROTATE_180,
}
FONT_PATHS = ["/System/Library/Fonts/Supplemental/Thonburi.ttc", "/System/Library/Fonts/Helvetica.ttc"]
CROP_MARGIN_PX = 16  # context kept around each number's ink before detect_blank

GREEN, ORANGE, RED, GREY = (22, 140, 60), (215, 120, 0), (200, 30, 30), (90, 90, 90)


@dataclass
class Cell:
    row: int
    col: int
    group_bbox: tuple[int, int, int, int]  # x, y, w, h of the merged number blob (rotated page coords)
    ink_bbox: tuple[int, int, int, int]  # x0, y0, x1, y1 of the ink itself
    value: str = ""  # system answer after postprocessing.decide ("" = no valid number)
    status: str = ""  # ok / needs_review / invalid_text / ...
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    chosen_variant: str = ""
    tight_text: str = ""  # tight_crop alone, digit-constrained
    tight_score: float = 0.0
    tight_raw: str = ""  # tight_crop alone, unconstrained (any character)
    segments_text: str = ""  # digit_segments read one by one and joined ("" = < 2 ink groups)
    ink_groups: int | None = None
    no_flatten_text: str = ""  # reference only: tight crop from the unflattened photo
    no_flatten_score: float = 0.0
    reading: str = ""  # Claude's unverified reading ("?" = unsure); not ground truth

    @property
    def differs_from_reading(self) -> bool:
        return bool(self.reading) and self.reading.rstrip("?") != self.value


# ---------------------------------------------------------------- segmentation
def page_mask(bgr: np.ndarray) -> np.ndarray:
    """Convex hull of the bright, unsaturated paper (keeps shadowed paper, drops the desk)."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    paper = ((hsv[..., 1] < 30) & (gray > 100)).astype(np.uint8) * 255
    paper = cv2.morphologyEx(paper, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(paper)
    if n < 2:
        raise RuntimeError("Cannot find the paper in the image")
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    cnts, _ = cv2.findContours((lab == big).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(gray)
    cv2.fillPoly(mask, [cv2.convexHull(max(cnts, key=cv2.contourArea))], 255)
    return cv2.erode(mask, np.ones((41, 41), np.uint8))  # stay clear of the paper edge


def flatten_illumination(bgr: np.ndarray) -> np.ndarray:
    """Divide each channel by its blurred background: paper -> white, shadows removed."""
    h, w = bgr.shape[:2]
    out = np.empty_like(bgr)
    for ch in range(3):
        c = bgr[..., ch]
        bg = cv2.resize(cv2.medianBlur(cv2.resize(c, (w // 4, h // 4)), 31), (w, h))
        out[..., ch] = np.clip(c.astype(np.float32) / np.maximum(bg, 1) * 255, 0, 255)
    return out


def ink_mask(flat_bgr: np.ndarray, page: np.ndarray) -> np.ndarray:
    """Pen strokes on the lighting-flattened page (hand shadow, glare removed)."""
    norm = cv2.cvtColor(flat_bgr, cv2.COLOR_BGR2GRAY)
    ink = ((norm < 170) & (page > 0)).astype(np.uint8) * 255
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink)
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= 25  # drop dust / paper texture
    return np.where(keep[lab], 255, 0).astype(np.uint8)


def find_numbers(ink: np.ndarray, min_area: int) -> list[tuple[tuple[int, int, int, int], tuple[int, int, int, int]]]:
    """Merge digits of one number (wide, short kernel); return (group bbox, tight ink bbox)."""
    grp = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_RECT, (41, 15)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(grp)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < min_area:
            continue
        ys, xs = np.nonzero((lab == i) & (ink > 0))
        if len(xs) == 0:
            continue
        group = tuple(int(v) for v in st[i, :4])
        tight = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        out.append((group, tight))
    return out


def to_grid(found: list, n_cols: int) -> list[Cell]:
    """Columns by 1-D k-means on x-centre, then rows by y inside each column.

    Rows on this kind of page are not straight (some rows are squeezed and tilted),
    so sorting by y globally mixes neighbouring rows; columns are well separated.
    """
    cx = np.array([[g[0] + g[2] / 2] for g, _ in found], np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.1)
    _, lbl, cent = cv2.kmeans(cx, n_cols, None, crit, 10, cv2.KMEANS_PP_CENTERS)
    rank = {int(c): i for i, c in enumerate(np.argsort(cent[:, 0]))}
    cols: list[list] = [[] for _ in range(n_cols)]
    for item, l in zip(found, lbl[:, 0]):
        cols[rank[int(l)]].append(item)
    cells = []
    for c, items in enumerate(cols):
        items.sort(key=lambda it: it[0][1] + it[0][3] / 2)
        cells += [Cell(r + 1, c + 1, g, t) for r, (g, t) in enumerate(items)]
    return sorted(cells, key=lambda k: (k.row, k.col))


# ---------------------------------------------------------------- per-cell system steps
@dataclass
class Prepared:
    crop: np.ndarray
    tight: np.ndarray | None
    segments: list[np.ndarray]
    stats: object


def prepare(flat: np.ndarray, cell: Cell, cfg) -> Prepared:
    """detect_blank + tight_crop + digit_segments on a crop around one number (as pipeline._prepare_cell)."""
    from qty_ocr.blank_detector import detect_blank, ink_group_masks
    from qty_ocr.preprocessing import build_variants, digit_segments

    h, w = flat.shape[:2]
    x0, y0, x1, y1 = cell.ink_bbox
    m = CROP_MARGIN_PX
    crop = flat[max(0, y0 - m) : min(h, y1 + m), max(0, x0 - m) : min(w, x1 + m)].copy()
    stats, mask = detect_blank(crop, cfg.blank_detection)
    variants = build_variants(crop, cfg.preprocessing, stats.ink_bbox)
    segments: list[np.ndarray] = []
    if cfg.preprocessing.digit_segments:
        bd = cfg.blank_detection
        groups = ink_group_masks(mask, bd.group_min_area, bd.group_min_height_ratio)
        if len(groups) >= 2:  # one group = the tight crop again
            segments = digit_segments(crop, groups, cfg.preprocessing.tight_crop_padding_ratio)
    return Prepared(crop, variants.get("tight_crop"), segments, stats)


def decide_cell(cell: Cell, prep: Prepared, raws: list, cfg) -> None:
    """Same decision as pipeline._decide_cell: tight_crop candidate + digit_segments candidate."""
    from qty_ocr.pipeline import _candidate
    from qty_ocr.postprocessing import decide

    fd = cfg.field
    cands = [_candidate("tight_crop", raws[:1], fd)]
    if prep.segments:
        cands.append(_candidate("digit_segments", raws[1:], fd))
    d = decide(
        cands, min_digits=fd.min_digits, max_digits=fd.max_digits,
        review_threshold=cfg.ocr.confidence_review_threshold, primary_variant=cfg.ocr.primary_variant,
        contradiction_min_score=cfg.ocr.contradiction_min_score,
        missing_digit_max_penalty=cfg.ocr.missing_digit_max_penalty,
        missing_digit_max_penalty_with_ink_groups=cfg.ocr.missing_digit_max_penalty_with_ink_groups,
        blank_label=prep.stats.label, ink_groups=prep.stats.ink_groups,
    )
    cell.value = d.value or ""
    cell.status = d.status.value if hasattr(d.status, "value") else str(d.status)
    cell.confidence = float(d.confidence or 0.0)
    cell.reasons = list(d.review_reasons)
    cell.chosen_variant = d.variant or ""
    cell.ink_groups = prep.stats.ink_groups
    t = raws[0]
    cell.tight_text, cell.tight_score, cell.tight_raw = t.digit_text or "", float(t.digit_score or 0), t.raw_text or ""
    if prep.segments:
        cell.segments_text = "".join(r.digit_text or "?" for r in raws[1:])


# ---------------------------------------------------------------- drawing
def font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def status_color(cell: Cell) -> tuple[int, int, int]:
    if not cell.value:
        return RED
    return GREEN if cell.status == "ok" else ORANGE


def draw_overlay(page_bgr: np.ndarray, cells: list[Cell], path: Path) -> None:
    img = Image.fromarray(cv2.cvtColor(page_bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)
    f_big, f_small = font(36), font(20)
    for c in cells:
        x0, y0, x1, y1 = c.ink_bbox
        col = status_color(c)
        d.rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 6], outline=col, width=5)
        label = c.value or "-"
        tw = d.textlength(label, font=f_big)
        tx, ty = x0 - 6, y0 - 52
        d.rectangle([tx, ty, tx + tw + 12, ty + 44], fill=(255, 255, 255), outline=col, width=3)
        d.text((tx + 6, ty + 1), label, fill=col, font=f_big)
        d.text((x0 - 4, y1 + 8), f"r{c.row}c{c.col}", fill=GREY, font=f_small)
    img.save(path, quality=92)


def _fit(img_bgr: np.ndarray, max_w: int, max_h: int) -> Image.Image:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    s = min(max_h / h, max_w / w)  # fit, never clip
    return Image.fromarray(rgb).resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)


def draw_sheets(cells: list[Cell], preps: dict[tuple[int, int], Prepared], out_dir: Path,
                n_cols: int, rows_per_sheet: int, threshold: float) -> list[Path]:
    tile_w, img_h, seg_h, text_h, gap = 340, 140, 56, 160, 14
    tile_h = img_h + seg_h + text_h
    f_head, f_pred, f_small, f_tiny = font(24), font(46), font(23), font(20)
    by_row: dict[int, list[Cell]] = {}
    for c in cells:
        by_row.setdefault(c.row, []).append(c)
    rows = sorted(by_row)
    paths = []
    for s in range(0, len(rows), rows_per_sheet):
        chunk = rows[s : s + rows_per_sheet]
        W = n_cols * (tile_w + gap) + gap
        H = 100 + len(chunk) * (tile_h + gap) + gap
        sheet = Image.new("RGB", (W, H), (245, 245, 245))
        d = ImageDraw.Draw(sheet)
        d.text((gap, 12), f"Rows {chunk[0]}-{chunk[-1]}.  Top image = tight crop fed to the model; small strip = "
               f"digit segments fed one by one (only when >= 2 ink groups).", fill=(30, 30, 30), font=f_small)
        d.text((gap, 50), f"Big number = system answer (score).  GREEN = ok, ORANGE = needs review "
               f"(score < {threshold}, digits disagree, ...).  Claude = Claude's UNVERIFIED reading, red when it "
               f"differs.", fill=(30, 30, 30), font=f_small)
        for ri, r in enumerate(chunk):
            for c in sorted(by_row[r], key=lambda k: k.col):
                p = preps[(c.row, c.col)]
                x = gap + (c.col - 1) * (tile_w + gap)
                y = 100 + ri * (tile_h + gap)
                col = status_color(c)
                d.rectangle([x, y, x + tile_w, y + tile_h], fill=(255, 255, 255), outline=col, width=4)
                if p.tight is not None:
                    pil = _fit(p.tight, tile_w - 12, img_h - 10)
                    sheet.paste(pil, (x + (tile_w - pil.width) // 2, y + 5 + (img_h - 10 - pil.height) // 2))
                if p.segments:
                    pils = [_fit(sg, (tile_w - 20) // len(p.segments) - 6, seg_h - 8) for sg in p.segments]
                    sx = x + (tile_w - sum(q.width + 8 for q in pils)) // 2
                    for q in pils:
                        sheet.paste(q, (sx, y + img_h + 4))
                        d.rectangle([sx - 1, y + img_h + 3, sx + q.width, y + img_h + 4 + q.height],
                                    outline=(170, 170, 210), width=1)
                        sx += q.width + 8
                ty = y + img_h + seg_h
                d.line([x + 4, ty, x + tile_w - 4, ty], fill=(220, 220, 220), width=2)
                d.text((x + 10, ty + 4), f"r{c.row} c{c.col}", fill=GREY, font=f_head)
                ans = c.value or "-"
                d.text((x + 10, ty + 28), ans, fill=col, font=f_pred)
                d.text((x + 18 + d.textlength(ans, font=f_pred), ty + 44), f"({c.confidence:.2f})", fill=col,
                       font=f_small)
                detail = f"tight {c.tight_text or '-'}"
                if c.segments_text:
                    detail += f" | seg {c.segments_text}"
                d.text((x + 10, ty + 84), detail, fill=GREY, font=f_tiny)
                if c.reading:
                    d.text((x + 10, ty + 112), f"Claude: {c.reading}", font=f_small,
                           fill=RED if c.differs_from_reading else (30, 30, 30))
        path = out_dir / f"sheet_{s // rows_per_sheet + 1}.png"
        sheet.save(path)
        paths.append(path)
    return paths


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--config", default=str(ROOT / "configs" / "changhouse.yaml"))
    ap.add_argument("--rotate", choices=sorted(ROTATIONS), default="cw",
                    help="rotation that makes the page upright (default: cw)")
    ap.add_argument("--cols", type=int, default=10, help="number of number-columns on the page")
    ap.add_argument("--rows", type=int, default=0, help="expected rows (0 = don't check)")
    ap.add_argument("--min-area", type=int, default=800, help="smallest merged blob kept (px)")
    ap.add_argument("--reading", help="optional JSON with {'rows': [[...], ...]} readings to compare")
    ap.add_argument("--rows-per-sheet", type=int, default=5)
    args = ap.parse_args()

    from qty_ocr.config import load_config
    from qty_ocr.preprocessing import tight_crop
    from qty_ocr.recognizer import PaddleV5Recognizer

    cfg = load_config(args.config)
    out = Path(args.output)
    (out / "crops").mkdir(parents=True, exist_ok=True)

    bgr = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if bgr is None:
        print(f"ERROR: cannot read {args.input}", file=sys.stderr)
        return 1
    if ROTATIONS[args.rotate] is not None:
        bgr = cv2.rotate(bgr, ROTATIONS[args.rotate])

    flat = flatten_illumination(bgr)
    cells = to_grid(find_numbers(ink_mask(flat, page_mask(bgr)), args.min_area), args.cols)
    per_col = [sum(c.col == k + 1 for c in cells) for k in range(args.cols)]
    print(f"found {len(cells)} numbers; per column: {per_col}")
    if args.rows and any(n != args.rows for n in per_col):
        print(f"WARNING: expected {args.rows} rows in every column — check overlay.jpg", file=sys.stderr)

    preps = {(c.row, c.col): prepare(flat, c, cfg) for c in cells}
    images, spans = [], {}
    for c in cells:
        p = preps[(c.row, c.col)]
        tag = f"r{c.row:02d}_c{c.col:02d}"
        if p.tight is None:
            raise RuntimeError(f"{tag}: detect_blank found no ink (segmentation said there was)")
        cv2.imwrite(str(out / "crops" / f"{tag}.png"), p.tight)
        for k, sg in enumerate(p.segments, 1):
            cv2.imwrite(str(out / "crops" / f"{tag}_seg{k}.png"), sg)
        spans[(c.row, c.col)] = (len(images), len(images) + 1 + len(p.segments))
        images += [p.tight, *p.segments]

    rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)
    raws = rec.recognize_batch(images)
    pad = cfg.preprocessing.tight_crop_padding_ratio
    ref = rec.recognize_batch([tight_crop(bgr, c.ink_bbox, pad) for c in cells])

    readings: dict[tuple[int, int], str] = {}
    if args.reading:
        data = json.loads(Path(args.reading).read_text(encoding="utf-8"))
        readings = {(r + 1, c + 1): v for r, row in enumerate(data["rows"]) for c, v in enumerate(row)}
    for c, rf in zip(cells, ref):
        k = (c.row, c.col)
        a, b = spans[k]
        decide_cell(c, preps[k], raws[a:b], cfg)
        c.no_flatten_text, c.no_flatten_score = rf.digit_text or "", float(rf.digit_score or 0.0)
        c.reading = readings.get(k, "")

    threshold = cfg.ocr.confidence_review_threshold
    draw_overlay(bgr, cells, out / "overlay.jpg")
    sheets = draw_sheets(cells, preps, out, args.cols, args.rows_per_sheet, threshold)

    with (out / "results.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "col", "value", "status", "confidence", "review_reasons", "tight_text", "tight_score",
                    "tight_raw", "segments_text", "ink_groups", "no_flatten_text", "no_flatten_score",
                    "claude_reading_unverified", "ink_bbox_x0y0x1y1", "crop", "gt"])
        for c in cells:
            w.writerow([c.row, c.col, c.value, c.status, f"{c.confidence:.4f}", " | ".join(c.reasons),
                        c.tight_text, f"{c.tight_score:.4f}", c.tight_raw, c.segments_text, c.ink_groups,
                        c.no_flatten_text, f"{c.no_flatten_score:.4f}", c.reading,
                        " ".join(map(str, c.ink_bbox)), f"crops/r{c.row:02d}_c{c.col:02d}.png", ""])
    (out / "results.json").write_text(json.dumps(
        {"image": str(args.input), "rotate": args.rotate, "model": cfg.ocr.model_name, "engine": cfg.ocr.engine,
         "confidence_review_threshold": threshold, "cells": [asdict(c) for c in cells]},
        ensure_ascii=False, indent=2), encoding="utf-8")

    review = [c for c in cells if c.status != "ok"]
    differ = [c for c in cells if c.differs_from_reading]
    lines = [f"# {Path(args.input).name}", "",
             f"- numbers found: {len(cells)} (per column {per_col})",
             f"- model: {cfg.ocr.model_name} / {cfg.ocr.engine}, digit-constrained decoding + postprocessing.decide",
             f"- status ok: {len(cells) - len(review)}, needs review / invalid: {len(review)}",
             f"- mean tight-crop score: {np.mean([c.tight_score for c in cells]):.3f} "
             f"(same crops without flattening: {np.mean([c.no_flatten_score for c in cells]):.3f})",
             f"- differs from Claude's unverified reading: {len(differ)} "
             f"(of which status ok: {sum(c.status == 'ok' for c in differ)})", "",
             "## Cells to check (status != ok, or differs from Claude's reading)", "",
             "| cell | answer | status | conf | tight | segments | Claude (unverified) | reasons |",
             "|---|---|---|---|---|---|---|---|"]
    lines += [f"| r{c.row}c{c.col} | {c.value} | {c.status} | {c.confidence:.2f} | {c.tight_text} | "
              f"{c.segments_text} | {c.reading} | {'; '.join(c.reasons)} |"
              for c in cells if c.status != "ok" or c.differs_from_reading]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:7]))
    print(f"wrote {out / 'overlay.jpg'}, {len(sheets)} sheets, results.csv/json, summary.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
