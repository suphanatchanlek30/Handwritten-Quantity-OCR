"""End-to-end orchestration of all stages for one document.

``recognizer=None`` runs geometry + blank detection only (``crop`` command) and
never imports PaddleOCR.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any, Iterator

import cv2
import numpy as np

from .alignment import AlignmentResult, map_bbox
from .layout import locate_geometry, resolve_qty_column
from .blank_detector import detect_blank, ink_group_masks
from .digit_decoder import extra_digit_penalty
from .config import AppConfig, FieldConfig
from .exporter import export_document, write_json
from .image_loader import load_image
from .postprocessing import decide, make_candidate
from .preprocessing import build_variants, digit_segments
from .recognizer import PaddleV5Recognizer, RawRecognition
from .roi_extractor import QtyCell, extract_qty_cells
from .schemas import BlankLabel, DocumentResult, FieldResult, FieldStatus, OCRCandidate
from .visualization import contact_sheet, draw_detected_table, draw_qty_overlay, draw_table_lines

logger = logging.getLogger(__name__)


@contextmanager
def _timer(timings: dict[str, float], key: str) -> Iterator[None]:
    t0 = time.perf_counter()
    try:
        yield
    finally:
        timings[key] = timings.get(key, 0.0) + (time.perf_counter() - t0) * 1000


def _imwrite(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), img):
        raise OSError(f"Failed to write {path}")


def _save_alignment_debug(out: Path, bgr: np.ndarray, align: AlignmentResult) -> None:
    _imwrite(out / "original.png", bgr)
    _imwrite(out / "grayscale.png", cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    if align.source_masks is not None:
        m = align.source_masks
        _imwrite(out / "printed_mask.png", m.printed)
        _imwrite(out / "table_lines.png", draw_table_lines(bgr, m.horizontal, m.vertical))
    _imwrite(out / "detected_table.png", draw_detected_table(bgr, align.detected_quad))
    if align.aligned_bgr is not None:
        _imwrite(out / "aligned.png", align.aligned_bgr)
        if align.grid is not None:
            _imwrite(
                out / "aligned_grid.png",
                draw_detected_table(
                    align.aligned_bgr, None, align.grid.vertical_lines, align.grid.horizontal_lines
                ),
            )


def _empty_field(row_id: int, status: FieldStatus, reasons: list[str]) -> FieldResult:
    return FieldResult(
        row_id=row_id, field_type="qty", bbox_aligned=None, bbox_original=None, is_blank=None,
        raw_text=None, normalized_text=None, value=None, value_int=None, confidence=None,
        status=status, needs_review=True, review_reasons=reasons,
    )


@dataclass
class PreparedDocument:
    """Image + table geometry computed ahead of OCR (see :func:`prepare_document`)."""

    image: Any
    align: AlignmentResult
    timings: dict[str, float]


def prepare_document(image_path: str | Path, cfg: AppConfig) -> PreparedDocument:
    """Load the image and locate the table geometry — no model involved.

    OpenCV releases the GIL, so batch mode runs this for the *next* document in
    a worker thread while the current document is being recognised.
    """
    timings: dict[str, float] = {}
    with _timer(timings, "load"):
        image = load_image(image_path)
    with _timer(timings, "alignment"):
        align = locate_geometry(image.bgr, cfg)
    return PreparedDocument(image, align, timings)


def process_document(
    image_path: str | Path,
    cfg: AppConfig,
    out_dir: str | Path,
    recognizer: PaddleV5Recognizer | None = None,
    debug: bool = True,
    prepared: PreparedDocument | None = None,
) -> DocumentResult:
    """Run the pipeline on one image and write all artefacts into ``out_dir``.

    ``prepared`` (from :func:`prepare_document`) skips loading and table geometry.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    save_debug = debug and cfg.output.save_debug_images

    ahead_ms = 0.0  # load + geometry done ahead of time (e.g. in a batch worker thread)
    if prepared is None:
        prepared = prepare_document(image_path, cfg)
    else:
        ahead_ms = sum(prepared.timings.values())
    timings: dict[str, float] = dict(prepared.timings)
    image = prepared.image
    doc = DocumentResult(
        document_id=image.document_id,
        template_id=cfg.project.template_id,
        model=cfg.ocr.model_name if recognizer is not None else None,
        status="completed",
        image_width=image.width,
        image_height=image.height,
        source_path=str(image.path),
    )

    with _timer(timings, "qty_column"):
        loc = resolve_qty_column(prepared.align, cfg, recognizer)
    align = loc.align
    doc.alignment = align.to_dict()
    if save_debug:
        _save_alignment_debug(out, image.bgr, align)

    if not align.success or align.aligned_bgr is None or align.grid is None or loc.qty is None:
        doc.status = "alignment_failed"
        doc.errors.append("alignment_failed: " + "; ".join(align.reasons))
        doc.fields = [
            _empty_field(i + 1, FieldStatus.ALIGNMENT_FAILED, list(align.reasons))
            for i in range(cfg.field.expected_rows)
        ]
        _finish(doc, cfg, out, timings, t_start, image.metadata, ahead_ms)
        return doc

    with _timer(timings, "table_extraction"):
        cells = extract_qty_cells(align.aligned_bgr, align.grid, loc.qty.index, loc.header_rows, cfg.roi)
    if len(cells) != cfg.field.expected_rows:
        note = f"expected {cfg.field.expected_rows} qty rows, found {len(cells)}"
        if cfg.layout.mode == "template":
            doc.errors.append(note)
        else:  # auto layout reads however many rows the form has
            doc.alignment["row_count_note"] = note

    extra_reasons: list[str] = []
    if recognizer is not None and loc.qty.method == "position_fallback":
        extra_reasons.append("qty_column_by_position")
    if align.used_fallback:
        extra_reasons.append("alignment_fallback_used")
    if align.grid.missing_horizontal or align.grid.missing_vertical:
        extra_reasons.append("grid_lines_from_template")

    originals: dict[int, np.ndarray] = {}
    chosen_imgs: dict[int, np.ndarray] = {}
    # Phase 1: prepare every cell (blank detection, variants, segments) without OCR.
    prepared = [_prepare_cell(cell, cfg, out, recognizer, align, extra_reasons, timings) for cell in cells]
    # Phase 2: one recognition call for the whole document, results split back in the original order.
    pending = [pc for pc in prepared if pc.images]
    if recognizer is not None and pending:
        with _timer(timings, "ocr_inference"):
            raws = recognizer.recognize_batch([img for pc in pending for img in pc.images])
        pos = 0
        for pc in pending:
            _decide_cell(pc, raws[pos: pos + len(pc.images)], cfg)
            pos += len(pc.images)
    for pc, cell in zip(prepared, cells):
        doc.fields.append(pc.field)
        originals[cell.row_id] = cell.crop
        if pc.field.preprocessing_variant and pc.field.preprocessing_variant in pc.variants:
            chosen_imgs[cell.row_id] = pc.variants[pc.field.preprocessing_variant]

    if save_debug:
        with _timer(timings, "visualization"):
            _imwrite(out / "qty_overlay.png", draw_qty_overlay(image.bgr, doc.fields))
            _imwrite(out / "contact_sheet.png", contact_sheet(doc.fields, originals, chosen_imgs))

    if recognizer is None:
        doc.status = "crops_only"
    elif any(f.status in (FieldStatus.RECOGNITION_ERROR, FieldStatus.FIELD_NOT_FOUND) for f in doc.fields):
        doc.status = "completed_with_errors"
    _finish(doc, cfg, out, timings, t_start, image.metadata, ahead_ms)
    return doc


@dataclass
class PreparedCell:
    """A cell after preprocessing, waiting for (or not needing) recognition."""

    field: FieldResult
    variants: dict[str, np.ndarray] = dc_field(default_factory=dict)
    names: list[str] = dc_field(default_factory=list)       # single-image variants, in order
    segments: list[np.ndarray] = dc_field(default_factory=list)
    label: BlankLabel = BlankLabel.NONBLANK
    ink_groups: int | None = None
    extra_reasons: list[str] = dc_field(default_factory=list)

    @property
    def images(self) -> list[np.ndarray]:
        """Images to recognise: variants first, then digit segments (empty = no OCR needed)."""
        return [self.variants[n] for n in self.names] + self.segments


def _prepare_cell(
    cell: QtyCell,
    cfg: AppConfig,
    out: Path,
    recognizer: PaddleV5Recognizer | None,
    align: AlignmentResult,
    extra_reasons: list[str],
    timings: dict[str, float],
) -> PreparedCell:
    assert align.H_inv is not None
    bbox_original = map_bbox(cell.crop_bbox, align.H_inv, *_orig_size(align))
    tag = f"row_{cell.row_id:02d}"
    if not cell.valid:
        f = _empty_field(cell.row_id, FieldStatus.FIELD_NOT_FOUND, list(cell.problems))
        f.bbox_aligned, f.bbox_original = cell.crop_bbox, bbox_original
        return PreparedCell(f)

    crop_rel = f"crops/{tag}_original.png"
    if cfg.output.save_crops:
        _imwrite(out / crop_rel, cell.crop)

    with _timer(timings, "blank_detection"):
        if cfg.blank_detection.enabled:
            stats, mask = detect_blank(cell.crop, cfg.blank_detection)
        else:
            stats, mask = None, None
    if mask is not None and cfg.output.save_crops:
        _imwrite(out / "masks" / f"{tag}_foreground.png", mask)

    base = FieldResult(
        row_id=cell.row_id, field_type="qty", bbox_aligned=cell.crop_bbox, bbox_original=bbox_original,
        is_blank=None, raw_text=None, normalized_text=None, value=None, value_int=None,
        confidence=None, status=FieldStatus.NEEDS_REVIEW, needs_review=True,
        crop_path=crop_rel if cfg.output.save_crops else None, blank_stats=stats,
    )
    label = stats.label if stats is not None else BlankLabel.NONBLANK
    if label == BlankLabel.BLANK:
        base.is_blank, base.status, base.needs_review = True, FieldStatus.BLANK, False
        return PreparedCell(base)
    base.is_blank = False

    bd = cfg.blank_detection
    with _timer(timings, "preprocessing"):
        variants = build_variants(cell.crop, cfg.preprocessing, stats.ink_bbox if stats else None)
        segments: list[np.ndarray] = []
        if cfg.preprocessing.digit_segments and mask is not None:
            groups = ink_group_masks(mask, bd.group_min_area, bd.group_min_height_ratio)
            # One ink group = the segment would be the tight crop again; skip the duplicate inference.
            if len(groups) >= 2:
                segments = digit_segments(cell.crop, groups, cfg.preprocessing.tight_crop_padding_ratio)
    if cfg.output.save_crops:
        for name, img in variants.items():
            if name != "original":
                _imwrite(out / "crops" / f"{tag}_{name}.png", img)
        for k, seg in enumerate(segments, start=1):
            _imwrite(out / "crops" / f"{tag}_seg_{k}.png", seg)
    if segments:
        variants["digit_segments"] = _hstack_white(segments)  # for the contact sheet only

    if recognizer is None:
        base.review_reasons = ["ocr_not_run"] + extra_reasons
        if label == BlankLabel.UNCERTAIN:
            base.review_reasons.append("blank_detection_uncertain")
        return PreparedCell(base, variants)

    names = [n for n in variants if n != "digit_segments"]
    return PreparedCell(base, variants, names, segments, label,
                        stats.ink_groups if stats else None, extra_reasons)


def _decide_cell(pc: PreparedCell, raws: list[RawRecognition], cfg: AppConfig) -> None:
    """Turn the recognition results of one prepared cell into its final field values."""
    fd = cfg.field
    n = len(pc.names)
    candidates = [_candidate(name, [r], fd) for name, r in zip(pc.names, raws[:n])]
    if pc.segments:
        candidates.append(_candidate("digit_segments", raws[n:], fd))
    d = decide(
        candidates,
        min_digits=fd.min_digits,
        max_digits=fd.max_digits,
        review_threshold=cfg.ocr.confidence_review_threshold,
        primary_variant=cfg.ocr.primary_variant,
        contradiction_min_score=cfg.ocr.contradiction_min_score,
        missing_digit_max_penalty=cfg.ocr.missing_digit_max_penalty,
        missing_digit_max_penalty_with_ink_groups=cfg.ocr.missing_digit_max_penalty_with_ink_groups,
        blank_label=pc.label,
        ink_groups=pc.ink_groups,
        extra_reasons=pc.extra_reasons,
    )
    base = pc.field
    base.candidates = candidates
    base.raw_text, base.normalized_text = d.raw_text, d.normalized_text
    base.value, base.value_int, base.confidence = d.value, d.value_int, d.confidence
    base.status, base.needs_review, base.review_reasons = d.status, d.needs_review, d.review_reasons
    base.preprocessing_variant = d.variant


def _candidate(name: str, raws: list[RawRecognition], fd: FieldConfig) -> OCRCandidate:
    """One candidate from one image, or from per-digit segments concatenated left to right."""
    errors = [r.error for r in raws if r.error]
    has_digits = all(r.digit_text is not None for r in raws)
    seg_scores = [r.digit_score for r in raws if r.digit_score is not None]
    longer_text, longer_penalty = None, None
    if len(raws) == 1 and raws[0].digit_q is not None and not errors:
        longer_text, longer_penalty = extra_digit_penalty(raws[0].digit_q, len(raws[0].digit_text or ""))
    cand = make_candidate(
        name,
        "".join((r.raw_text or "").strip() for r in raws) if not errors else None,
        min((r.rec_score for r in raws if r.rec_score is not None), default=None),
        sum(r.inference_time_ms for r in raws),
        raws[0].model_name,
        min_digits=fd.min_digits,
        max_digits=fd.max_digits,
        error="; ".join(errors) if errors else None,
        digit_text="".join(r.digit_text or "" for r in raws) if has_digits and not errors else None,
        # segments: weakest segment bounds the reading's confidence
        digit_score=min(seg_scores) if has_digits and seg_scores and not errors else None,
        digit_char_scores=[s for r in raws for s in r.digit_char_scores],
        digit_substituted=sum(r.digit_substituted for r in raws),
        n_images=len(raws),
    )
    cand.longer_text = longer_text or None
    cand.longer_penalty = None if longer_penalty is None else round(longer_penalty, 5)
    return cand


def _hstack_white(images: list[np.ndarray]) -> np.ndarray:
    h = max(i.shape[0] for i in images)
    padded = [cv2.copyMakeBorder(i, 0, h - i.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for i in images]
    return np.hstack(padded)


def _orig_size(align: AlignmentResult) -> tuple[int, int]:
    w, h = align.diagnostics["input_size"]
    return int(w), int(h)


def _finish(
    doc: DocumentResult,
    cfg: AppConfig,
    out: Path,
    timings: dict[str, float],
    t_start: float,
    image_meta: dict,
    ahead_ms: float = 0.0,
) -> None:
    # compute time for this document, wherever its stages ran (wall time of a batch is reported separately)
    timings["total"] = (time.perf_counter() - t_start) * 1000 + ahead_ms
    doc.timings_ms = timings
    export_document(doc, out, cfg.output.save_json, cfg.output.save_csv)
    write_json(
        out / "diagnostics.json",
        {
            "document_id": doc.document_id,
            "image_metadata": image_meta,
            "alignment": doc.alignment,
            "timings_ms": {k: round(v, 2) for k, v in timings.items()},
            "blank_stats": {
                f.row_id: f.blank_stats.to_dict() if f.blank_stats else None for f in doc.fields
            },
            "errors": doc.errors,
        },
    )


def process_many(
    paths: list[Path],
    cfg: AppConfig,
    out_root: Path,
    recognizer: PaddleV5Recognizer | None = None,
    debug: bool = False,
    prefetch: bool = False,
) -> Iterator[tuple[Path, DocumentResult | Exception]]:
    """Process documents in order, yielding ``(path, result_or_error)``.

    With ``prefetch`` the next document's load + table geometry runs in one
    worker thread while the current document is recognised (OpenCV and ONNX
    Runtime both release the GIL). The recogniser itself is only used from the
    calling thread, and every document is computed exactly as in
    :func:`process_document`, so results are identical either way.
    """
    from concurrent.futures import Future, ThreadPoolExecutor

    def prep(p: Path) -> PreparedDocument:
        return prepare_document(p, cfg)

    if not prefetch or len(paths) < 2:
        for p in paths:
            try:
                yield p, process_document(p, cfg, out_root / p.stem, recognizer=recognizer, debug=debug)
            except Exception as exc:  # noqa: BLE001 - reported per document by the caller
                yield p, exc
        return

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="qty-prefetch") as pool:
        nxt: Future[PreparedDocument] = pool.submit(prep, paths[0])
        for i, p in enumerate(paths):
            current = nxt
            if i + 1 < len(paths):
                nxt = pool.submit(prep, paths[i + 1])
            try:
                prepared = current.result()
                yield p, process_document(p, cfg, out_root / p.stem, recognizer=recognizer,
                                          debug=debug, prepared=prepared)
            except Exception as exc:  # noqa: BLE001 - reported per document by the caller
                yield p, exc


_WORKER_RECOGNIZER: PaddleV5Recognizer | None = None


def _worker_init(cfg: AppConfig, use_ocr: bool) -> None:
    """Runs once per worker process: load the model there (never shared across processes)."""
    global _WORKER_RECOGNIZER
    if use_ocr:
        _WORKER_RECOGNIZER = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)


def _worker_process(job: tuple[Path, AppConfig, Path, bool]) -> DocumentResult | Exception:
    path, cfg, out_root, debug = job
    try:
        return process_document(path, cfg, out_root / path.stem, recognizer=_WORKER_RECOGNIZER, debug=debug)
    except Exception as exc:  # noqa: BLE001 - reported per document by the caller
        return exc


def process_many_parallel(
    paths: list[Path],
    cfg: AppConfig,
    out_root: Path,
    workers: int,
    use_ocr: bool = True,
    debug: bool = False,
) -> Iterator[tuple[Path, DocumentResult | Exception]]:
    """Process documents in ``workers`` separate processes, yielding results in input order.

    Each process loads its own model (~0.75 GB RSS with onnxruntime), so memory
    grows linearly with ``workers``. Documents are independent, so every result
    is identical to sequential processing.
    """
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor

    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                             initializer=_worker_init, initargs=(cfg, use_ocr)) as pool:
        jobs = [(p, cfg, out_root, debug) for p in paths]
        for p, res in zip(paths, pool.map(_worker_process, jobs, chunksize=1)):
            yield p, res
