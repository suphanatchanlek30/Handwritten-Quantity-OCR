"""Measure end-to-end timing and peak RSS for batch sizes / CPU thread counts.

Each configuration runs in a fresh subprocess so peak memory is per-config.

Usage:
    python scripts/benchmark.py --input data/samples/order_form_01.jpg --repeat 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHILD = r"""
import json, resource, sys, tempfile, time
from dataclasses import replace
from qty_ocr.config import load_config
from qty_ocr.pipeline import process_document
from qty_ocr.recognizer import PaddleV5Recognizer
cfg_path, image, bs, threads, repeat = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
cfg = load_config(cfg_path)
cfg = replace(cfg, ocr=replace(cfg.ocr, batch_size=bs), hardware=replace(cfg.hardware, cpu_threads=threads),
              output=replace(cfg.output, save_debug_images=False, save_crops=False))
t0 = time.perf_counter(); rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network); init = (time.perf_counter() - t0) * 1000
runs = []
with tempfile.TemporaryDirectory() as d:
    for _ in range(repeat):
        doc = process_document(image, cfg, d, recognizer=rec, debug=False)
        runs.append(doc.timings_ms)
values = [f.value for f in doc.fields]
peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)  # macOS: bytes
print(json.dumps({"batch_size": bs, "cpu_threads": threads, "init_ms": init, "runs": runs,
                  "values": values, "peak_rss_mb": peak_mb}))
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT / "data" / "samples" / "order_form_01.jpg"))
    p.add_argument("--config", default=str(ROOT / "configs" / "changhouse.yaml"))
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--batch-sizes", default="1,2,4")
    p.add_argument("--threads", default="2,4,8")
    args = p.parse_args()

    combos = [(int(b), 4) for b in args.batch_sizes.split(",")]
    combos += [(1, int(t)) for t in args.threads.split(",") if int(t) != 4]
    print("| batch | threads | init ms | first run ms | warm OCR ms (mean) | warm total ms (mean) | peak RSS MB | values |")
    print("|---:|---:|---:|---:|---:|---:|---:|---|")
    for bs, th in combos:
        out = subprocess.run(
            [sys.executable, "-c", CHILD, args.config, args.input, str(bs), str(th), str(args.repeat)],
            capture_output=True, text=True, cwd=ROOT,
        )
        line = next((l for l in out.stdout.splitlines() if l.startswith("{")), None)
        if out.returncode != 0 or line is None:
            print(f"| {bs} | {th} | FAILED: {out.stderr.strip().splitlines()[-1] if out.stderr else '?'} |")
            continue
        r = json.loads(line)
        warm = r["runs"][1:] or r["runs"]
        ocr = sum(x.get("ocr_inference", 0) for x in warm) / len(warm)
        tot = sum(x["total"] for x in warm) / len(warm)
        print(f"| {bs} | {th} | {r['init_ms']:.0f} | {r['runs'][0]['total']:.0f} | {ocr:.0f} | {tot:.0f} | "
              f"{r['peak_rss_mb']:.0f} | {','.join(v or '-' for v in r['values'])} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
