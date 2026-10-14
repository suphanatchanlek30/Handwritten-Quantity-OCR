"""Command line interface.

    python -m qty_ocr.cli crop      --input IMG --config CFG --output DIR [--debug]
    python -m qty_ocr.cli run       --input IMG --config CFG --output DIR [--debug]
    python -m qty_ocr.cli batch     --input-dir DIR --config CFG --output DIR
    python -m qty_ocr.cli evaluate  --predictions results.json [...] --ground-truth GT.json
    python -m qty_ocr.cli experiment --input IMG [...] --config CFG --output DIR
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from .config import AppConfig, ConfigError, load_config
from .image_loader import ImageLoadError, list_images
from .recognizer import RecognizerInitError

logger = logging.getLogger("qty_ocr")

DEFAULT_CONFIG = "configs/changhouse.yaml"


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_recognizer(cfg: AppConfig):  # type: ignore[no-untyped-def]
    from .recognizer import PaddleV5Recognizer  # deferred: crop mode never imports paddle

    return PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)


def _print_doc(doc) -> None:  # type: ignore[no-untyped-def]
    print(f"\n{doc.document_id}: status={doc.status}  alignment={doc.alignment.get('method')}")
    for f in doc.fields:
        conf = f"{f.confidence:.3f}" if f.confidence is not None else "  -  "
        value = f.value if f.value is not None else ("(blank)" if f.is_blank else "-")
        reasons = "; ".join(f.review_reasons)
        print(f"  row {f.row_id:2d}  qty={value:<8} conf={conf}  {f.status.value:<14} {reasons}")
    print(f"  total {doc.timings_ms.get('total', 0):.0f} ms")


def cmd_crop(args: argparse.Namespace, cfg: AppConfig) -> int:
    from .pipeline import process_document

    doc = process_document(args.input, cfg, args.output, recognizer=None, debug=args.debug)
    _print_doc(doc)
    print(f"\nArtefacts: {Path(args.output).resolve()}")
    return 0 if doc.status != "alignment_failed" else 2


def cmd_run(args: argparse.Namespace, cfg: AppConfig) -> int:
    from .pipeline import process_document

    recognizer = _load_recognizer(cfg)
    doc = process_document(args.input, cfg, args.output, recognizer=recognizer, debug=args.debug)
    _print_doc(doc)
    print(f"\nArtefacts: {Path(args.output).resolve()}")
    return 0 if doc.status.startswith("completed") else 2


def cmd_batch(args: argparse.Namespace, cfg: AppConfig) -> int:
    from dataclasses import replace

    from .exporter import CSV_COLUMNS, csv_rows, write_csv
    from .pipeline import process_many, process_many_parallel

    images = list_images(args.input_dir)
    if not images:
        print(f"No .jpg/.jpeg/.png images in {args.input_dir}", file=sys.stderr)
        return 1
    if not args.debug:
        # batch default: no debug images and no per-cell crop files (enable with --debug)
        cfg = replace(cfg, output=replace(cfg.output, save_debug_images=False, save_crops=False))
    out_root = Path(args.output)
    all_rows, failures = [], 0
    t0 = time.perf_counter()
    if args.workers > 1:
        if args.workers > 2:
            logger.warning("%d workers ≈ %.1f GB RAM (each process loads its own model)",
                           args.workers, 0.75 * args.workers)
        results = process_many_parallel(images, cfg, out_root, args.workers,
                                        use_ocr=not args.crops_only, debug=args.debug)
    else:
        recognizer = None if args.crops_only else _load_recognizer(cfg)
        results = process_many(images, cfg, out_root, recognizer=recognizer, debug=args.debug,
                               prefetch=args.prefetch)
    for path, doc in results:
        if isinstance(doc, ImageLoadError):
            logger.error("Skipping %s: %s", path, doc)
            failures += 1
            continue
        if isinstance(doc, Exception):
            raise doc
        _print_doc(doc)
        all_rows.extend(csv_rows(doc))
        failures += doc.status == "alignment_failed"
    write_csv(out_root / "batch_results.csv", all_rows)
    print(f"\n{len(images)} documents in {time.perf_counter() - t0:.1f} s, failures={failures}")
    print(f"Combined CSV ({', '.join(CSV_COLUMNS[:4])}...): {(out_root / 'batch_results.csv').resolve()}")
    return 0 if failures == 0 else 2


def cmd_evaluate(args: argparse.Namespace, cfg: AppConfig | None) -> int:
    from .evaluation import UnverifiedGroundTruthError, evaluate, load_ground_truth

    try:
        gt = load_ground_truth(args.ground_truth)
    except UnverifiedGroundTruthError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3
    preds = []
    for p in args.predictions:
        preds.append(json.loads(Path(p).read_text(encoding="utf-8")))
    matched = sorted({p["document_id"] for p in preds} & set(gt))
    if not matched:
        print(
            "ERROR: none of the prediction document_ids "
            f"{sorted({p['document_id'] for p in preds})} appear in the ground truth "
            f"(has {len(gt)} documents, e.g. {sorted(gt)[:3]})",
            file=sys.stderr,
        )
        return 4
    report = evaluate(preds, gt).to_dict()
    report["documents_evaluated"] = matched
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_experiment(args: argparse.Namespace, cfg: AppConfig) -> int:
    from .experiments import experiment_markdown, run_experiment, save_experiment

    recognizer = _load_recognizer(cfg)
    rows = run_experiment([Path(p) for p in args.input], cfg, recognizer)
    save_experiment(rows, Path(args.output))
    print(experiment_markdown(rows))
    print(f"Saved: {Path(args.output).resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qty_ocr", description="Handwritten qty OCR (PP-OCRv5_server_rec)")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--config", default=DEFAULT_CONFIG)
        sp.add_argument("--debug", action="store_true", help="save debug images")
        sp.add_argument("--device", default=None,
                        help="override hardware.device: cpu | auto | gpu | gpu:N (GPU path untested)")

    sp = sub.add_parser("crop", help="align + crop qty cells (no OCR model)")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    common(sp)

    sp = sub.add_parser("run", help="full OCR pipeline on one image")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    common(sp)

    sp = sub.add_parser("batch", help="process every image in a folder")
    sp.add_argument("--input-dir", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument("--crops-only", action="store_true")
    sp.add_argument("--workers", type=int, default=1,
                    help="parallel processes, each with its own model (~0.75 GB each). "
                         "Measured on M5: 2 workers = ~25%% higher throughput for large batches")
    sp.add_argument("--prefetch", action="store_true",
                    help="prepare the next document in a thread while the current one is recognised "
                         "(measured: only 1-5%% faster on M5 because CPU is already saturated)")
    common(sp)

    sp = sub.add_parser("evaluate", help="score predictions against VERIFIED ground truth")
    sp.add_argument("--predictions", nargs="+", required=True)
    sp.add_argument("--ground-truth", required=True)

    sp = sub.add_parser("experiment", help="compare preprocessing variants E1-E7")
    sp.add_argument("--input", nargs="+", required=True)
    sp.add_argument("--output", required=True)
    common(sp)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(args.verbose)
    try:
        if args.command == "evaluate":
            return cmd_evaluate(args, None)
        cfg = load_config(args.config)
        if getattr(args, "device", None):
            from dataclasses import replace

            from .config import validate_config

            cfg = replace(cfg, hardware=replace(cfg.hardware, device=args.device))
            validate_config(cfg)
        handler = {"crop": cmd_crop, "run": cmd_run, "batch": cmd_batch, "experiment": cmd_experiment}[args.command]
        return handler(args, cfg)
    except (ConfigError, ImageLoadError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except RecognizerInitError as exc:  # e.g. GPU requested but CUDA unavailable, model download failed
        print(f"ERROR (model): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
