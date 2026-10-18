"""Read handwritten numbers arranged in a free-form grid with PP-OCRv5.

This utility is for pages without printed table rules. It finds ink groups, orders
them into a grid, then applies the main pipeline's per-cell OCR and review policy.

Usage:
    python scripts/grid_page_ocr.py --input page.jpg --output outputs/page --cols 10 --rows 15

    # with verified labels (one row per number, numbered left->right, top->bottom):
    python scripts/grid_page_ocr.py ... --gt-csv data/ground_truth/real_verified-2.csv --gt-writer data1

Outputs (in --output):
    overlay.jpg            whole page, each number boxed with the system's answer beside it
    overlay_gt.jpg         (--gt-csv) green = correct, red = wrong with the true value beside it
    accuracy.md            (--gt-csv) accuracy, wrong-but-ok cells, breakdowns
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
# Normalize page width so pixel-based thresholds are resolution-independent.
WORK_WIDTH = 2160

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
    gt: str = ""  # verified label from --gt-csv ("" = not given)

    @property
    def differs_from_reading(self) -> bool:
        return bool(self.reading) and self.reading.rstrip("?") != self.value

    @property
    def correct(self) -> bool | None:
        return None if not self.gt else self.value == self.gt


# Segmentation
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


def find_numbers(ink: np.ndarray, min_area: int,
                 min_height_ratio: float = 0.4) -> list[tuple[tuple[int, int, int, int], tuple[int, int, int, int]]]:
    """Merge digits of one number (wide, short kernel); return (group bbox, tight ink bbox).

    Blobs whose ink is much shorter than the typical number (pen dots, specks) are dropped.
    """
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
    if out:
        med_h = float(np.median([t[3] - t[1] for _, t in out]))
        out = [(g, t) for g, t in out if t[3] - t[1] >= min_height_ratio * med_h]
        med_w = float(np.median([t[2] - t[0] for _, t in out]))
        out = [p for g, t in out for p in split_wide(ink, g, t, med_w, med_h, min_height_ratio)]
        out = drop_isolated(out)
    return out


def split_wide(ink: np.ndarray, group: tuple[int, int, int, int], tight: tuple[int, int, int, int],
               med_w: float, med_h: float, min_height_ratio: float,
               width_ratio: float = 3.0, gap_ratio: float = 0.5) -> list:
    """Split an unusually wide merged blob at its widest ink-free column gap."""
    x0, y0, x1, y1 = tight
    if x1 - x0 <= width_ratio * med_w:
        return [(group, tight)]
    empty = ink[y0:y1, x0:x1].max(axis=0) == 0
    best_len, best_mid, run = 0, 0, 0
    for i, e in enumerate(empty):
        run = run + 1 if e else 0
        if run > best_len:
            best_len, best_mid = run, i - run // 2
    if best_len < gap_ratio * med_h:
        return [(group, tight)]
    parts = []
    for a, b in ((x0, x0 + best_mid), (x0 + best_mid, x1)):
        ys, xs = np.nonzero(ink[y0:y1, a:b])
        t = (a + int(xs.min()), y0 + int(ys.min()), a + int(xs.max()) + 1, y0 + int(ys.max()) + 1)
        if t[3] - t[1] < min_height_ratio * med_h:
            return [(group, tight)]  # Keep the original when a split creates noise.
        g = (t[0], group[1], t[2] - t[0], group[3])
        parts.append((g, t))
    return [p for g, t in parts for p in split_wide(ink, g, t, med_w, med_h, min_height_ratio,
                                                    width_ratio, gap_ratio)]


def drop_isolated(found: list, ratio: float = 4.0) -> list:
    """Drop blobs isolated from the number grid, such as marks at the page edge."""
    if len(found) < 3:
        return found
    ctr = np.array([((t[0] + t[2]) / 2, (t[1] + t[3]) / 2) for _, t in found])
    d = np.sqrt(((ctr[:, None] - ctr[None]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    nn = d.min(axis=1)
    keep = nn <= ratio * float(np.median(nn))
    for (_, t), k, v in zip(found, keep, nn):
        if not k:
            print(f"drop isolated blob at x{t[0]}-{t[2]} y{t[1]}-{t[3]} "
                  f"(nearest number {v:.0f}px, {v / np.median(nn):.1f}x median)")
    return [f for f, k in zip(found, keep) if k]


def to_grid(found: list, tol_ratio: float = 1.0) -> list[Cell]:
    """Group numbers into rows by walking left/right from neighbour to neighbour.

    Hand-written rows are tilted, some are squeezed against the next row, and the
    columns drift sideways down the page, so neither a global y sort nor x clustering
    is reliable. Each step predicts where the next number should be from the row's
    own tilt so far (page-wide tilt at the start) and takes the nearest number to the
    left/right whose centre is within ``tol_ratio x median ink height`` of that line.
    """
    items = [(g, t, (t[0] + t[2]) / 2, (t[1] + t[3]) / 2) for g, t in found]
    med_h = float(np.median([t[3] - t[1] for _, t, _, _ in items]))
    tol = tol_ratio * med_h

    def nearest_right(i: int) -> int | None:
        cands = [j for j in range(len(items)) if items[j][2] > items[i][2] and abs(items[j][3] - items[i][3]) <= 0.7 * med_h]
        return min(cands, key=lambda j: items[j][2] - items[i][2]) if cands else None

    slopes = []
    for i in range(len(items)):
        j = nearest_right(i)
        if j is not None:
            slopes.append((items[j][3] - items[i][3]) / (items[j][2] - items[i][2]))
    page_slope = float(np.median(slopes)) if slopes else 0.0
    left = set(range(len(items)))

    def step(row: list[int], cur: int, direction: int) -> int | None:
        xs = [items[j][2] for j in row]
        ys = [items[j][3] for j in row]
        slope = float(np.polyfit(xs, ys, 1)[0]) if len(row) >= 3 else page_slope
        cx, cy = items[cur][2], items[cur][3]
        best, best_cost = None, None
        for j in left:
            dx = items[j][2] - cx
            if dx * direction <= 0:
                continue
            resid = abs(items[j][3] - (cy + slope * dx))
            if resid > tol:
                continue
            cost = abs(dx) + 3 * resid
            if best_cost is None or cost < best_cost:
                best, best_cost = j, cost
        return best

    rows: list[list[int]] = []
    while left:
        seed = min(left, key=lambda j: items[j][2])  # leftmost remaining number starts a row
        seed = min((j for j in left if abs(items[j][2] - items[seed][2]) <= 2 * med_h), key=lambda j: items[j][3])
        left.discard(seed)
        row = [seed]
        for direction in (1, -1):
            cur = seed
            while (nxt := step(row, cur, direction)) is not None:
                left.discard(nxt)
                row.append(nxt)
                cur = nxt
        rows.append(sorted(row, key=lambda j: items[j][2]))
    rows.sort(key=lambda r: float(np.mean([items[j][3] for j in r])))
    return [Cell(ri + 1, ci + 1, items[j][0], items[j][1]) for ri, r in enumerate(rows) for ci, j in enumerate(r)]


# Per-cell OCR
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


# Rendering
def font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def status_color(cell: Cell) -> tuple[int, int, int]:
    if not cell.value:
        return RED
    return GREEN if cell.status == "ok" else ORANGE


def gt_color(cell: Cell) -> tuple[int, int, int]:
    return GREEN if cell.correct else RED


def draw_overlay(page_bgr: np.ndarray, cells: list[Cell], path: Path, use_gt: bool = False,
                 draft_gt: bool = False) -> None:
    """Status colours (default) or, with use_gt, correct/wrong colours with the true value under wrong cells.

    Label size follows the handwriting (median ink height and row spacing) so labels on a
    tightly written page do not cover the row above; the legend sits in a band above the page.
    """
    med_h = float(np.median([c.ink_bbox[3] - c.ink_bbox[1] for c in cells]))
    row_y = [float(np.mean([(c.ink_bbox[1] + c.ink_bbox[3]) / 2 for c in cells if c.row == r]))
             for r in sorted({c.row for c in cells})]
    row_gap = float(np.median(np.diff(row_y))) if len(row_y) > 1 else 3 * med_h
    fs = int(max(18, min(36, 0.8 * med_h, 0.38 * row_gap)))
    f_big, f_small, f_gt = font(fs), font(max(14, int(fs * 0.55))), font(max(16, int(fs * 0.8)))

    page = Image.fromarray(cv2.cvtColor(page_bgr, cv2.COLOR_BGR2RGB))
    if use_gt:
        n_ok = sum(bool(c.correct) for c in cells)
        legend = (f"GREEN = correct ({n_ok})   RED = wrong ({len(cells) - n_ok}): answer above box, GT = true value "
                  f"below   accuracy {n_ok}/{len(cells)} = {100 * n_ok / len(cells):.1f}%"
                  + ("   [DRAFT GT by Claude - not verified]" if draft_gt else ""))
    else:
        n_ok = sum(c.status == "ok" for c in cells)
        legend = f"GREEN = ok ({n_ok})   ORANGE = needs review ({len(cells) - n_ok})   number above box = model answer"
    # Wrap legend entries before they exceed the page width.
    f_leg, lines = font(30), [""]
    measure = ImageDraw.Draw(page)
    for part in legend.split("   "):
        trial = f"{lines[-1]}   {part}" if lines[-1] else part
        if lines[-1] and measure.textlength(trial, font=f_leg) > page.width - 32:
            lines.append(part)
        else:
            lines[-1] = trial
    band = 20 + 40 * len(lines)
    img = Image.new("RGB", (page.width, page.height + band), (255, 255, 255))
    img.paste(page, (0, band))
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((16, 10 + 40 * i), line, fill=(20, 20, 20), font=f_leg)
    for c in cells:
        x0, y0, x1, y1 = c.ink_bbox
        y0, y1 = y0 + band, y1 + band
        col = gt_color(c) if use_gt else status_color(c)
        d.rectangle([x0 - 5, y0 - 5, x1 + 5, y1 + 5], outline=col, width=4)
        label = c.value or "-"
        tw = d.textlength(label, font=f_big)
        tx, ty = x0 - 5, y0 - fs - 14
        d.rectangle([tx, ty, tx + tw + 10, ty + fs + 8], fill=(255, 255, 255), outline=col, width=3)
        d.text((tx + 5, ty + 1), label, fill=col, font=f_big)
        if not (use_gt and not c.correct):
            d.text((x0 - 4, y1 + 7), f"r{c.row}c{c.col}", fill=GREY, font=f_small)
    for c in cells if use_gt else []:  # true values last, so no other label covers them
        if c.correct:
            continue
        x0, y1 = c.ink_bbox[0], c.ink_bbox[3] + band
        gt_label = f"GT {c.gt}"
        gw = d.textlength(gt_label, font=f_gt)
        gh = int(fs * 0.8) + 6
        d.rectangle([x0 - 5, y1 + 7, x0 + gw + 5, y1 + 7 + gh], fill=(255, 235, 235), outline=RED, width=2)
        d.text((x0, y1 + 8), gt_label, fill=(150, 0, 0), font=f_gt)
    img.save(path, quality=92)


def _fit(img_bgr: np.ndarray, max_w: int, max_h: int) -> Image.Image:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    s = min(max_h / h, max_w / w)  # fit, never clip
    return Image.fromarray(rgb).resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)


def draw_sheets(cells: list[Cell], preps: dict[tuple[int, int], Prepared], out_dir: Path,
                n_cols: int, rows_per_sheet: int, threshold: float, use_gt: bool = False) -> list[Path]:
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
        if use_gt:
            d.text((gap, 50), f"Big number = system answer (score).  GREEN border = correct, RED = wrong.  "
                   f"GT = verified true value.  status: ok / REVIEW (system asks a human to check: score < "
                   f"{threshold}, digits disagree, ...)", fill=(30, 30, 30), font=f_small)
        else:
            d.text((gap, 50), f"Big number = system answer (score).  GREEN = ok, ORANGE = needs review "
                   f"(score < {threshold}, digits disagree, ...).  Claude = Claude's UNVERIFIED reading, red when "
                   f"it differs.", fill=(30, 30, 30), font=f_small)
        for ri, r in enumerate(chunk):
            for c in sorted(by_row[r], key=lambda k: k.col):
                p = preps[(c.row, c.col)]
                x = gap + (c.col - 1) * (tile_w + gap)
                y = 100 + ri * (tile_h + gap)
                col = gt_color(c) if use_gt else status_color(c)
                d.rectangle([x, y, x + tile_w, y + tile_h], fill=(255, 255, 255), outline=col,
                            width=6 if use_gt and not c.correct else 4)
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
                if use_gt:
                    d.text((x + 10, ty + 112), f"GT: {c.gt}", font=f_small, fill=(30, 30, 30))
                    d.text((x + 120, ty + 112), "correct" if c.correct else "WRONG", font=f_small, fill=col)
                    d.text((x + 230, ty + 112), "ok" if c.status == "ok" else "REVIEW", font=f_small,
                           fill=GREEN if c.status == "ok" else ORANGE)
                elif c.reading:
                    d.text((x + 10, ty + 112), f"Claude: {c.reading}", font=f_small,
                           fill=RED if c.differs_from_reading else (30, 30, 30))
        path = out_dir / f"sheet_{s // rows_per_sheet + 1}.png"
        sheet.save(path)
        paths.append(path)
    return paths


# Ground truth
def load_gt_csv(path: Path, writer: str | None, n_cols: int,
                allow_draft: bool = False) -> tuple[dict[tuple[int, int], str], bool]:
    """Labels numbered 1..N left->right, top->bottom -> ({(row, col): label}, is_draft).

    Only 'verified' rows unless allow_draft; is_draft tells the caller to mark every output.
    """
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    writers = sorted({r.get("writer_id", "") for r in rows})
    if writer is None and len(writers) > 1:
        raise SystemExit(f"--gt-csv holds several pages {writers}; pick one with --gt-writer")
    rows = [r for r in rows if writer is None or r.get("writer_id") == writer]
    if not rows:
        raise SystemExit(f"no rows for writer {writer!r} in {path} (have {writers})")
    bad = [r["row"] for r in rows if r.get("status", "verified") != "verified"]
    if bad and not allow_draft:
        raise SystemExit(f"unverified labels in {path}: rows {bad[:10]} — accuracy needs verified labels "
                         "(--allow-draft-gt to measure against a draft, clearly marked)")
    out = {}
    for r in rows:
        k = int(r["row"]) - 1
        out[(k // n_cols + 1, k % n_cols + 1)] = r["label"].strip()
    return out, bool(bad)


def accuracy_report(cells: list[Cell], image: str, gt_path: str, writer: str | None, threshold: float,
                    draft: bool = False) -> str:
    from qty_ocr.evaluation import levenshtein

    n = len(cells)
    right = [c for c in cells if c.correct]
    ok = [c for c in cells if c.status == "ok"]
    ok_right = [c for c in ok if c.correct]
    rev = [c for c in cells if c.status != "ok"]
    wrong_ok = [c for c in ok if not c.correct]
    chars = sum(len(c.gt) for c in cells)
    edits = sum(levenshtein(c.value, c.gt) for c in cells)
    tight_right = sum(c.tight_text == c.gt for c in cells)
    noflat_right = sum(c.no_flatten_text == c.gt for c in cells)
    pct = lambda a, b: f"{a}/{b} = {100 * a / b:.1f}%" if b else "-"  # noqa: E731
    mean = lambda xs: f"{np.mean(xs):.3f}" if xs else "-"  # noqa: E731
    lines = [f"# Accuracy — {image}", "",
             f"Ground truth: `{gt_path}`" + (f" (writer_id = {writer})" if writer else "") +
             (" — **DRAFT labels (not verified by the owner) — not a confirmed accuracy**" if draft else
              " — verified labels") + ", numbered left->right, top->bottom", "",
             "| metric | value |", "|---|---|",
             f"| **exact-match accuracy (whole number)** | **{pct(len(right), n)}** |",
             f"| digit-level accuracy (1 - CER) | {pct(chars - edits, chars)} |",
             f"| status ok | {len(ok)} — of which correct {pct(len(ok_right), len(ok))} |",
             f"| status needs_review | {len(rev)} — of which correct {pct(sum(bool(c.correct) for c in rev), len(rev))} |",
             f"| **wrong but status ok (not flagged)** | **{len(wrong_ok)}** |",
             f"| accuracy if a human fixes every flagged cell | {pct(n - len(wrong_ok), n)} |",
             f"| mean confidence: correct / wrong | {mean([c.confidence for c in right])} / "
             f"{mean([c.confidence for c in cells if not c.correct])} |", "",
             "Same crops, simpler settings (to show what each step adds):", "",
             "| setting | exact-match |", "|---|---|",
             f"| tight crop from the photo, no flattening | {pct(noflat_right, n)} |",
             f"| tight crop, lighting flattened | {pct(tight_right, n)} |",
             f"| + digit_segments + decide (= system answer) | {pct(len(right), n)} |", "",
             "By number of digits:", "", "| digits | correct |", "|---|---|"]
    for k in sorted({len(c.gt) for c in cells}):
        grp = [c for c in cells if len(c.gt) == k]
        lines.append(f"| {k} | {pct(sum(bool(c.correct) for c in grp), len(grp))} |")
    lines += ["", f"## Wrong but status ok ({len(wrong_ok)}) — the system did not ask for review", "",
              "| cell | answer | GT | conf | reasons |", "|---|---|---|---|---|"]
    lines += [f"| r{c.row}c{c.col} | {c.value} | {c.gt} | {c.confidence:.2f} | {'; '.join(c.reasons)} |"
              for c in wrong_ok]
    wrong = [c for c in cells if not c.correct]
    lines += ["", f"## Wrong ({len(wrong)})", "", "| cell | answer | GT | status | conf | tight | segments |",
              "|---|---|---|---|---|---|---|"]
    lines += [f"| r{c.row}c{c.col} | {c.value or '-'} | {c.gt} | {c.status} | {c.confidence:.2f} | "
              f"{c.tight_text} | {c.segments_text} |" for c in wrong]
    return "\n".join(lines) + "\n"


# CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--config", default=str(ROOT / "configs" / "changhouse.yaml"))
    ap.add_argument("--rotate", choices=sorted(ROTATIONS), default="cw",
                    help="rotation that makes the page upright (default: cw)")
    ap.add_argument("--cols", type=int, default=10, help="numbers per row (used to check the grid and number --gt-csv)")
    ap.add_argument("--rows", type=int, default=0, help="expected rows (0 = don't check)")
    ap.add_argument("--min-area", type=int, default=800, help="smallest merged blob kept (px, at --work-width)")
    ap.add_argument("--work-width", type=int, default=WORK_WIDTH,
                    help="resize the upright page to this width before processing (0 = keep size)")
    ap.add_argument("--reading", help="optional JSON with {'rows': [[...], ...]} readings to compare")
    ap.add_argument("--gt-csv", help="verified labels CSV (columns row, label, writer_id); row k = k-th number "
                    "counted left->right, top->bottom")
    ap.add_argument("--gt-writer", help="writer_id to take from --gt-csv when it holds several pages")
    ap.add_argument("--allow-draft-gt", action="store_true",
                    help="accept labels whose status is not 'verified' (e.g. claude_draft); every report "
                         "and overlay is then marked DRAFT GT")
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
    if args.work_width and bgr.shape[1] != args.work_width:
        s = args.work_width / bgr.shape[1]
        print(f"resize page {bgr.shape[1]}x{bgr.shape[0]} -> x{s:.3f}")
        bgr = cv2.resize(bgr, (args.work_width, round(bgr.shape[0] * s)),
                         interpolation=cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA)

    flat = flatten_illumination(bgr)
    cells = to_grid(find_numbers(ink_mask(flat, page_mask(bgr)), args.min_area))
    n_rows = max(c.row for c in cells)
    per_row = [sum(c.row == r + 1 for c in cells) for r in range(n_rows)]
    print(f"found {len(cells)} numbers in {n_rows} rows; per row: {per_row}")
    if any(n != args.cols for n in per_row) or (args.rows and n_rows != args.rows):
        print(f"WARNING: expected {args.rows or '?'} rows x {args.cols} numbers — check overlay.jpg", file=sys.stderr)

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
    gts: dict[tuple[int, int], str] = {}
    draft_gt = False
    if args.gt_csv:
        gts, draft_gt = load_gt_csv(Path(args.gt_csv), args.gt_writer, args.cols, args.allow_draft_gt)
        missing = [f"r{c.row}c{c.col}" for c in cells if (c.row, c.col) not in gts]
        if missing or len(gts) != len(cells):
            print(f"ERROR: {len(gts)} labels for {len(cells)} numbers; unlabeled: {missing[:10]}", file=sys.stderr)
            return 1
    for c, rf in zip(cells, ref):
        k = (c.row, c.col)
        a, b = spans[k]
        decide_cell(c, preps[k], raws[a:b], cfg)
        c.no_flatten_text, c.no_flatten_score = rf.digit_text or "", float(rf.digit_score or 0.0)
        c.reading = readings.get(k, "")
        c.gt = gts.get(k, "")

    threshold = cfg.ocr.confidence_review_threshold
    draw_overlay(bgr, cells, out / "overlay.jpg")
    if gts:
        draw_overlay(bgr, cells, out / "overlay_gt.jpg", use_gt=True, draft_gt=draft_gt)
    sheets = draw_sheets(cells, preps, out, max(c.col for c in cells), args.rows_per_sheet, threshold,
                         use_gt=bool(gts))

    with (out / "results.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "col", "value", "status", "confidence", "review_reasons", "tight_text", "tight_score",
                    "tight_raw", "segments_text", "ink_groups", "no_flatten_text", "no_flatten_score",
                    "claude_reading_unverified", "ink_bbox_x0y0x1y1", "crop", "gt", "correct"])
        for c in cells:
            w.writerow([c.row, c.col, c.value, c.status, f"{c.confidence:.4f}", " | ".join(c.reasons),
                        c.tight_text, f"{c.tight_score:.4f}", c.tight_raw, c.segments_text, c.ink_groups,
                        c.no_flatten_text, f"{c.no_flatten_score:.4f}", c.reading,
                        " ".join(map(str, c.ink_bbox)), f"crops/r{c.row:02d}_c{c.col:02d}.png", c.gt,
                        "" if c.correct is None else int(c.correct)])
    (out / "results.json").write_text(json.dumps(
        {"image": str(args.input), "rotate": args.rotate, "model": cfg.ocr.model_name, "engine": cfg.ocr.engine,
         "confidence_review_threshold": threshold, "cells": [asdict(c) for c in cells]},
        ensure_ascii=False, indent=2), encoding="utf-8")

    review = [c for c in cells if c.status != "ok"]
    differ = [c for c in cells if c.differs_from_reading]
    lines = [f"# {Path(args.input).name}", "",
             f"- numbers found: {len(cells)} in {n_rows} rows (per row {per_row})",
             f"- model: {cfg.ocr.model_name} / {cfg.ocr.engine}, digit-constrained decoding + postprocessing.decide",
             f"- status ok: {len(cells) - len(review)}, needs review / invalid: {len(review)}",
             f"- mean tight-crop score: {np.mean([c.tight_score for c in cells]):.3f} "
             f"(same crops without flattening: {np.mean([c.no_flatten_score for c in cells]):.3f})",
             f"- differs from Claude's unverified reading: {len(differ)} "
             f"(of which status ok: {sum(c.status == 'ok' for c in differ)})" if readings else
             "- Claude's reading: not given (--reading)", "",
             "## Cells to check (status != ok, or differs from Claude's reading)", "",
             "| cell | answer | status | conf | tight | segments | Claude (unverified) | reasons |",
             "|---|---|---|---|---|---|---|---|"]
    lines += [f"| r{c.row}c{c.col} | {c.value} | {c.status} | {c.confidence:.2f} | {c.tight_text} | "
              f"{c.segments_text} | {c.reading} | {'; '.join(c.reasons)} |"
              for c in cells if c.status != "ok" or c.differs_from_reading]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:7]))
    if gts:
        acc = accuracy_report(cells, Path(args.input).name, args.gt_csv, args.gt_writer, threshold, draft_gt)
        (out / "accuracy.md").write_text(acc, encoding="utf-8")
        print(acc.split("## Wrong")[0])
    print(f"wrote {out / 'overlay.jpg'}, {len(sheets)} sheets, results.csv/json, summary.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
