"""Stage 1 — image loading and validation.

Images are decoded with Pillow (to honour EXIF orientation) and returned as
OpenCV-style **BGR** ``uint8`` arrays. Every downstream module expects BGR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class ImageLoadError(RuntimeError):
    """Raised when an input image cannot be used."""


@dataclass
class LoadedImage:
    path: Path
    bgr: np.ndarray
    width: int
    height: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def document_id(self) -> str:
        return self.path.stem


def load_image(path: str | Path) -> LoadedImage:
    """Load ``path`` as a BGR array, applying EXIF orientation if present."""
    path = Path(path)
    if not path.exists():
        raise ImageLoadError(f"Image not found: {path}")
    if not path.is_file():
        raise ImageLoadError(f"Not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ImageLoadError(
            f"Unsupported format '{path.suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    if path.stat().st_size == 0:
        raise ImageLoadError(f"Empty file: {path}")

    try:
        with Image.open(path) as pil:  # header only; pixels are decoded below
            raw_size = pil.size
            exif_orientation = pil.getexif().get(0x0112)
            mode = pil.mode
            fast = pil.format == "JPEG" and mode == "RGB" and exif_orientation in (None, 1)
            bgr = None
            if fast:
                # Plain RGB JPEG without rotation: OpenCV decodes the same pixels ~3x faster
                # (verified identical on all 63 test images); anything else goes through Pillow.
                bgr = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
                if bgr is None or (bgr.shape[1], bgr.shape[0]) != raw_size:
                    bgr = None
            if bgr is None:
                pil.load()
                pil = ImageOps.exif_transpose(pil)
                rgb = np.asarray(pil.convert("RGB"), dtype=np.uint8)
                bgr = np.ascontiguousarray(rgb[:, :, ::-1])  # explicit RGB -> BGR
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageLoadError(f"Cannot decode image {path}: {exc}") from exc

    if bgr.ndim != 3 or bgr.shape[0] < 50 or bgr.shape[1] < 50:
        raise ImageLoadError(f"Image too small or malformed: shape={bgr.shape}")

    h, w = bgr.shape[:2]
    return LoadedImage(
        path=path,
        bgr=bgr,
        width=w,
        height=h,
        metadata={
            "source_mode": mode,
            "raw_size": list(raw_size),
            "exif_orientation": exif_orientation,
            "exif_rotated": tuple(raw_size) != (w, h),
            "file_size_bytes": path.stat().st_size,
        },
    )


def list_images(directory: str | Path) -> list[Path]:
    """Return supported images in ``directory`` sorted naturally by name."""
    import re

    directory = Path(directory)
    if not directory.is_dir():
        raise ImageLoadError(f"Not a directory: {directory}")

    def natural_key(p: Path) -> list[Any]:
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]

    return sorted(
        (p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=natural_key,
    )
