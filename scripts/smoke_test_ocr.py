"""Smoke test: run the real PP-OCRv5_server_rec model on one cropped image.

Usage:
    python scripts/smoke_test_ocr.py --input data/samples/qty_sample.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(ROOT / "data" / "samples" / "qty_sample.png"))
    parser.add_argument("--config", default=str(ROOT / "configs" / "changhouse.yaml"))
    args = parser.parse_args()

    from qty_ocr.config import load_config
    from qty_ocr.recognizer import PaddleV5Recognizer

    img = cv2.imread(args.input, cv2.IMREAD_COLOR)  # BGR, as the recognizer expects
    if img is None:
        print(f"ERROR: cannot read {args.input}", file=sys.stderr)
        return 1
    cfg = load_config(args.config)
    rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)
    print(f"model={rec.model_name} init={rec.init_time_ms:.0f} ms input={args.input} shape={img.shape}")
    for i in range(2):  # 2nd call shows warm inference time
        r = rec.recognize(img)
        if r.error:
            print(f"ERROR: {r.error}", file=sys.stderr)
            return 2
        print(f"run {i + 1}: rec_text={r.raw_text!r} rec_score={r.rec_score:.4f} time={r.inference_time_ms:.1f} ms")
    print("NOTE: rec_score is the model's confidence, not measured accuracy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
