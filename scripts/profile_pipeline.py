"""Profile the full pipeline: warm per-stage timings, predict calls per document, peak RSS.

The model is loaded once (not timed). Every document is processed ``--repeat``
times; per-document stage times are the median over repeats, then summarised
as the median over documents. Results of the first repeat can be saved for
``scripts/compare_results.py``; all repeats are checked for run-to-run
determinism (value / status / review reasons).

Usage:
    python scripts/profile_pipeline.py --inputs "../Data Test" "../Data Test/test/example.jpg" \\
        --repeat 3 --save-results outputs/validation --label validation
"""

from __future__ import annotations

import argparse
import json
import resource
import statistics
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from qty_ocr.net import disable_model_source_check, force_ipv4  # noqa: E402

force_ipv4()
disable_model_source_check()


def collect_inputs(items: list[str]) -> list[Path]:
    from qty_ocr.image_loader import list_images

    out: list[Path] = []
    for item in items:
        p = Path(item)
        out += list_images(p) if p.is_dir() else [p]
    return out


def signature(doc: Any) -> list[tuple[Any, ...]]:
    return [(f.row_id, f.value, f.status.value, f.needs_review, tuple(f.review_reasons)) for f in doc.fields]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--config", default=str(ROOT / "configs" / "changhouse.yaml"))
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--save-results", type=Path, default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--cpu-threads", type=int, default=None)
    ap.add_argument("--engine", default=None, choices=["paddle_static", "onnxruntime"])
    ap.add_argument("--device", default=None, help="cpu | auto | gpu | gpu:N")
    ap.add_argument("--onnx-threads", type=int, default=None)
    ap.add_argument("--label", default="run")
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--prefetch", action="store_true", help="use process_many (next document prepared in a thread)")
    args = ap.parse_args()

    from qty_ocr.config import load_config
    from qty_ocr.exporter import export_document
    from qty_ocr.pipeline import process_document, process_many
    from qty_ocr.recognizer import PaddleV5Recognizer

    cfg = load_config(args.config)
    cfg = replace(cfg, output=replace(cfg.output, save_debug_images=False, save_crops=False,
                                      save_json=False, save_csv=False))
    if args.batch_size:
        cfg = replace(cfg, ocr=replace(cfg.ocr, batch_size=args.batch_size))
    if args.engine:
        cfg = replace(cfg, ocr=replace(cfg.ocr, engine=args.engine))
    if args.device:
        cfg = replace(cfg, hardware=replace(cfg.hardware, device=args.device))
    if args.onnx_threads:
        cfg = replace(cfg, ocr=replace(cfg.ocr, onnx_intra_op_threads=args.onnx_threads))
    if args.cpu_threads:
        cfg = replace(cfg, hardware=replace(cfg.hardware, cpu_threads=args.cpu_threads))

    t0 = time.perf_counter()
    rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)
    init_ms = (time.perf_counter() - t0) * 1000

    calls = {"n": 0, "images": 0}
    original_predict = rec._model.predict

    def counting_predict(*a: Any, **k: Any) -> Any:
        calls["n"] += 1
        inp = k.get("input", a[0] if a else None)
        calls["images"] += len(inp) if isinstance(inp, list) else 1
        return original_predict(*a, **k)

    rec._model.predict = counting_predict  # type: ignore[method-assign]

    paths = collect_inputs(args.inputs)
    stage_times: dict[str, dict[str, list[float]]] = {}
    sigs: dict[str, list[list[tuple[Any, ...]]]] = {}
    per_doc_calls: list[int] = []
    per_doc_images: list[int] = []
    wall: list[float] = []
    with tempfile.TemporaryDirectory() as tmp:
        for rep in range(args.repeat):
            t_rep = time.perf_counter()
            if args.prefetch:
                docs_iter = process_many(paths, cfg, Path(tmp), recognizer=rec, debug=False, prefetch=True)
            else:
                docs_iter = ((p, process_document(p, cfg, Path(tmp) / p.stem, recognizer=rec, debug=False))
                             for p in paths)
            calls["n"] = calls["images"] = 0
            for path, doc in docs_iter:
                if isinstance(doc, Exception):
                    raise doc
                if rep == 0:
                    per_doc_calls.append(calls["n"])
                    per_doc_images.append(calls["images"])
                    if args.save_results:
                        export_document(doc, args.save_results / doc.document_id, save_json=True, save_csv=False)
                calls["n"] = calls["images"] = 0
                d = stage_times.setdefault(doc.document_id, {})
                for k, v in doc.timings_ms.items():
                    d.setdefault(k, []).append(v)
                sigs.setdefault(doc.document_id, []).append(signature(doc))
            wall.append((time.perf_counter() - t_rep) * 1000)

    stages = sorted({k for d in stage_times.values() for k in d})
    summary = {
        k: round(statistics.median(statistics.median(d[k]) for d in stage_times.values() if k in d), 1)
        for k in stages
    }
    nondeterministic = [doc for doc, s in sigs.items() if any(x != s[0] for x in s[1:])]
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
    result = {
        "label": args.label,
        "prefetch": args.prefetch,
        "documents": len(paths),
        "repeat": args.repeat,
        "batch_size": cfg.ocr.batch_size,
        "cpu_threads": cfg.hardware.cpu_threads,
        "engine": cfg.ocr.engine,
        "device": rec.device,
        "providers": rec.providers,
        "onnx_intra_op_threads": cfg.ocr.onnx_intra_op_threads,
        "init_ms": round(init_ms),
        "median_stage_ms_per_doc": summary,
        "predict_calls_per_doc_median": statistics.median(per_doc_calls),
        "images_per_doc_median": statistics.median(per_doc_images),
        "batch_wall_ms_per_repeat": [round(w) for w in wall],
        "peak_rss_mb": round(peak_mb),
        "nondeterministic_documents": nondeterministic,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
