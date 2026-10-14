"""Generate phone-photo-like versions of scanned forms for robustness testing.

Each output applies, with a fixed seed per (image, variant): a desk background,
random perspective + rotation, uneven lighting with a soft shadow, colour cast,
blur, sensor noise, JPEG compression and a random output resolution.

These are *simulations* for testing table localisation and robustness — not a
substitute for real photographs.

Usage:
    python scripts/simulate_photos.py --input "../Data Test" --output data/simulated_photos --per-image 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def simulate(img: np.ndarray, rng: np.random.Generator, strength: float = 1.0) -> np.ndarray:
    h, w = img.shape[:2]
    # 1. page on a textured desk
    pad_x, pad_y = int(w * 0.18), int(h * 0.18)
    desk_color = np.array([rng.uniform(40, 110), rng.uniform(70, 130), rng.uniform(100, 170)])
    canvas = np.empty((h + 2 * pad_y, w + 2 * pad_x, 3), np.float32)
    canvas[:] = desk_color
    canvas += rng.normal(0, 10, canvas.shape[:2])[..., None]
    canvas = cv2.GaussianBlur(canvas, (0, 0), 3)
    canvas[pad_y:pad_y + h, pad_x:pad_x + w] = img
    H, W = canvas.shape[:2]

    # 2. perspective + rotation
    j = 0.07 * strength
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst = src + rng.uniform(-j, j, (4, 2)).astype(np.float32) * np.float32([W, H])
    M = cv2.getPerspectiveTransform(src, dst)
    R = cv2.getRotationMatrix2D((W / 2, H / 2), rng.uniform(-8, 8) * strength, 1.0)
    M = np.vstack([R, [0, 0, 1]]) @ M
    photo = cv2.warpPerspective(canvas, M, (W, H), borderMode=cv2.BORDER_REPLICATE)

    # 3. uneven light: linear gradient + soft shadow blob
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ang = rng.uniform(0, 2 * np.pi)
    g = (np.cos(ang) * xx / W + np.sin(ang) * yy / H)
    g = (g - g.min()) / (g.max() - g.min() + 1e-6)
    light = 1.0 - 0.35 * strength * g
    cx, cy = rng.uniform(0.2, 0.8) * W, rng.uniform(0.2, 0.8) * H
    r = rng.uniform(0.15, 0.35) * max(W, H)
    shadow = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
    light *= 1.0 - 0.3 * strength * shadow
    photo *= light[..., None]

    # 4. colour cast (warm/cool), blur, noise
    photo *= np.array([rng.uniform(0.85, 1.0), rng.uniform(0.93, 1.0), rng.uniform(0.97, 1.05)])
    photo = cv2.GaussianBlur(photo, (0, 0), rng.uniform(0.6, 1.3))
    photo += rng.normal(0, 4, photo.shape)
    photo = np.clip(photo, 0, 255).astype(np.uint8)

    # 5. random resolution + JPEG
    out_w = int(rng.uniform(1300, 3200))
    photo = cv2.resize(photo, (out_w, int(out_w * H / W)), interpolation=cv2.INTER_AREA)
    ok, enc = cv2.imencode(".jpg", photo, [cv2.IMWRITE_JPEG_QUALITY, int(rng.uniform(60, 85))])
    return cv2.imdecode(enc, cv2.IMREAD_COLOR)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", nargs="+", required=True, help="image files or folders")
    p.add_argument("--output", default=str(ROOT / "data" / "simulated_photos"))
    p.add_argument("--per-image", type=int, default=2)
    p.add_argument("--strength", type=float, default=1.0)
    args = p.parse_args()

    paths: list[Path] = []
    for item in args.input:
        q = Path(item)
        paths += sorted(x for x in q.iterdir() if x.suffix.lower() in {".jpg", ".jpeg", ".png"}) if q.is_dir() else [q]
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            print(f"skip unreadable {path}", file=sys.stderr)
            continue
        for k in range(args.per_image):
            seed = sum(map(ord, path.name)) * 1000 + k  # deterministic per file and variant
            photo = simulate(img.astype(np.float32), np.random.default_rng(seed), args.strength)
            cv2.imwrite(str(out / f"{path.stem}__photo{k + 1}.jpg"), photo)
    print(f"wrote {len(paths) * args.per_image} images to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
