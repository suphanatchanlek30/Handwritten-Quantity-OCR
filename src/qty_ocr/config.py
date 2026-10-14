"""Configuration loading and validation.

All tunable parameters live in YAML (see ``configs/changhouse.yaml``).
Every section maps to a frozen dataclass; unknown keys and invalid values
raise :class:`ConfigError` at startup instead of failing later in the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the YAML configuration is missing or invalid."""


@dataclass(frozen=True)
class ProjectConfig:
    name: str = "handwritten-qty-ocr"
    template_id: str = "CHANGHOUSE_V1"


@dataclass(frozen=True)
class HardwareConfig:
    device: str = "cpu"
    cpu_threads: int = 4


@dataclass(frozen=True)
class NetworkConfig:
    force_ipv4: bool = False
    disable_model_source_check: bool = False


@dataclass(frozen=True)
class OCRConfig:
    model_name: str = "PP-OCRv5_server_rec"
    engine: str = "paddle_static"
    batch_size: int = 1
    confidence_review_threshold: float = 0.85
    primary_variant: str = "tight_crop"
    digit_constrained_decoding: bool = True
    missing_digit_max_penalty: float = 0.03
    missing_digit_max_penalty_with_ink_groups: float = 0.06
    contradiction_min_score: float = 0.85
    model_dir: str | None = None
    enable_mkldnn: bool | None = None
    onnx_intra_op_threads: int | None = None   # onnxruntime only; None = ORT default (all cores)


@dataclass(frozen=True)
class FieldConfig:
    target_column: str = "qty"
    expected_rows: int = 10
    min_digits: int = 1
    max_digits: int = 3


@dataclass(frozen=True)
class TemplateConfig:
    width: int = 1667
    height: int = 1759
    vertical_lines: tuple[int, ...] = (144, 448, 1055, 1286, 1501)
    horizontal_lines: tuple[int, ...] = (
        382, 455, 543, 630, 718, 806, 893, 981, 1069, 1156, 1244, 1332,
    )
    qty_column_index: int = 2
    header_rows: int = 1

    @property
    def table_box(self) -> tuple[int, int, int, int]:
        """Outer table box ``[x_min, y_min, x_max, y_max]`` on the template."""
        return (
            self.vertical_lines[0],
            self.horizontal_lines[0],
            self.vertical_lines[-1],
            self.horizontal_lines[-1],
        )


@dataclass(frozen=True)
class AlignmentConfig:
    mode: str = "automatic_with_fallback"
    min_line_match_ratio: float = 0.85
    line_snap_tolerance_px: int = 12
    grid_max_gray: int = 210
    grid_max_saturation: int = 60
    horizontal_kernel_ratio: float = 0.08
    vertical_kernel_ratio: float = 0.04
    line_thickening_px: int = 3
    deskew: bool = True
    max_skew_deg: float = 15.0
    # "adaptive" = local threshold (robust to shadows / uneven light in photos); "global" = grid_max_gray
    grid_threshold: str = "adaptive"
    adaptive_block_px: int = 41
    adaptive_c: int = 12


@dataclass(frozen=True)
class LayoutConfig:
    # "auto": find table / columns / rows from the image itself; "template": fixed template coordinates
    mode: str = "auto"
    normalized_table_width: int = 1360
    margin_px: int = 12
    min_line_coverage: float = 0.5        # while searching / snapping the table box
    final_line_coverage: float = 0.8      # rules of the final table must span this much
    search_margin_ratio: float = 0.08     # extra border (x table width) searched for the true outer rules
    border_tolerance_px: int = 8
    coarse_kernel_scale: float = 1.0      # <1 = shorter line kernels for the first search (tested: worse)
    refine_iterations: int = 2
    candidate_dilate_ratio: float = 0.01  # extra candidates from a mask dilated by this x image size
    fit_border_lines: bool = True         # refine the table corners from Hough-fitted outer rules
    border_fit_scale: float = 0.75        # image scale used for that Hough fit (speed)
    min_column_width_px: int = 25
    min_row_height_px: int = 30
    min_columns: int = 3
    min_table_area_ratio: float = 0.03
    flatten_illumination: bool = True
    flatten_kernel_px: int = 31
    header_rows: int = 1
    qty_header_keywords: tuple[str, ...] = ("qty", "จำนวน")
    qty_column_from_right: int = 2


@dataclass(frozen=True)
class ROIConfig:
    crop_margin_px: int = 4
    min_crop_width: int = 40
    min_crop_height: int = 30


@dataclass(frozen=True)
class BlankDetectionConfig:
    enabled: bool = True
    # "relative" = contrast against the cell's own paper colour; "absolute" = fixed thresholds below
    ink_threshold: str = "relative"
    dark_min_contrast: int = 45
    color_min_contrast: int = 30
    inspect_margin_px: int = 3
    color_min_saturation: int = 40
    color_min_value: int = 50
    dark_max_gray: int = 170
    min_component_area: int = 6
    nonblank_min_pixels: int = 40
    uncertain_min_pixels: int = 12
    min_stroke_height_px: int = 18
    group_min_area: int = 15
    group_min_height_ratio: float = 0.3


@dataclass(frozen=True)
class PreprocessingConfig:
    original: bool = False
    grayscale: bool = False
    red_mask: bool = False
    ink_isolation: bool = False
    adaptive_threshold: bool = False
    tight_crop: bool = True
    digit_segments: bool = True
    tight_crop_padding_ratio: float = 0.35
    clahe: bool = False
    red_hue_ranges: tuple[tuple[int, int], ...] = ((0, 12), (160, 180))
    red_min_saturation: int = 40
    red_min_value: int = 40

    def enabled_variants(self) -> list[str]:
        """Variant names in evaluation order (``original`` first when enabled)."""
        order = [
            "original",
            "grayscale",
            "red_mask",
            "ink_isolation",
            "adaptive_threshold",
            "tight_crop",
            "digit_segments",
        ]
        return [name for name in order if getattr(self, name)]


@dataclass(frozen=True)
class OutputConfig:
    save_crops: bool = True
    save_debug_images: bool = True
    save_json: bool = True
    save_csv: bool = True


@dataclass(frozen=True)
class AppConfig:
    project: ProjectConfig = dc_field(default_factory=ProjectConfig)
    hardware: HardwareConfig = dc_field(default_factory=HardwareConfig)
    network: NetworkConfig = dc_field(default_factory=NetworkConfig)
    ocr: OCRConfig = dc_field(default_factory=OCRConfig)
    field: FieldConfig = dc_field(default_factory=FieldConfig)
    template: TemplateConfig = dc_field(default_factory=TemplateConfig)
    layout: LayoutConfig = dc_field(default_factory=LayoutConfig)
    alignment: AlignmentConfig = dc_field(default_factory=AlignmentConfig)
    roi: ROIConfig = dc_field(default_factory=ROIConfig)
    blank_detection: BlankDetectionConfig = dc_field(default_factory=BlankDetectionConfig)
    preprocessing: PreprocessingConfig = dc_field(default_factory=PreprocessingConfig)
    output: OutputConfig = dc_field(default_factory=OutputConfig)


_SECTION_CLASSES: dict[str, type] = {
    "project": ProjectConfig,
    "hardware": HardwareConfig,
    "network": NetworkConfig,
    "ocr": OCRConfig,
    "field": FieldConfig,
    "template": TemplateConfig,
    "layout": LayoutConfig,
    "alignment": AlignmentConfig,
    "roi": ROIConfig,
    "blank_detection": BlankDetectionConfig,
    "preprocessing": PreprocessingConfig,
    "output": OutputConfig,
}

_ALIGNMENT_MODES = {"automatic_with_fallback", "automatic", "static"}
_ENGINES = {"paddle_static", "onnxruntime"}


def _to_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_to_tuple(v) for v in value)
    return value


def _build_section(name: str, raw: Any) -> Any:
    cls = _SECTION_CLASSES[name]
    if raw is None:
        return cls()
    if not isinstance(raw, dict):
        raise ConfigError(f"Section '{name}' must be a mapping, got {type(raw).__name__}")
    known = {f.name for f in fields(cls)}
    unknown = set(raw) - known
    if unknown:
        raise ConfigError(f"Unknown keys in section '{name}': {sorted(unknown)}")
    return cls(**{k: _to_tuple(v) for k, v in raw.items()})


def validate_config(cfg: AppConfig) -> None:
    """Check cross-field invariants. Raises :class:`ConfigError`."""
    errors: list[str] = []
    if cfg.layout.mode not in ("auto", "template"):
        errors.append("layout.mode must be 'auto' or 'template'")
    lay = cfg.layout
    if lay.qty_column_from_right < 1 or lay.min_columns < 2 or lay.normalized_table_width < 400:
        errors.append("layout: qty_column_from_right >= 1, min_columns >= 2, normalized_table_width >= 400")
    if cfg.alignment.grid_threshold not in ("adaptive", "global"):
        errors.append("alignment.grid_threshold must be 'adaptive' or 'global'")
    if cfg.layout.mode == "template":
        t = cfg.template
        if list(t.vertical_lines) != sorted(t.vertical_lines) or len(t.vertical_lines) < 2:
            errors.append("template.vertical_lines must be ascending with >= 2 entries")
        if list(t.horizontal_lines) != sorted(t.horizontal_lines) or len(t.horizontal_lines) < 2:
            errors.append("template.horizontal_lines must be ascending with >= 2 entries")
        if not 0 <= t.qty_column_index < len(t.vertical_lines) - 1:
            errors.append("template.qty_column_index out of range")
        n_data_rows = len(t.horizontal_lines) - 1 - t.header_rows
        if n_data_rows != cfg.field.expected_rows:
            errors.append(
                f"template defines {n_data_rows} data rows but field.expected_rows="
                f"{cfg.field.expected_rows}"
            )
        if any(v < 0 or v > t.width for v in t.vertical_lines):
            errors.append("template.vertical_lines outside template width")
        if any(v < 0 or v > t.height for v in t.horizontal_lines):
            errors.append("template.horizontal_lines outside template height")
    if cfg.alignment.mode not in _ALIGNMENT_MODES:
        errors.append(f"alignment.mode must be one of {sorted(_ALIGNMENT_MODES)}")
    if cfg.ocr.engine not in _ENGINES:
        errors.append(f"ocr.engine must be one of {sorted(_ENGINES)}")
    if cfg.ocr.batch_size not in (1, 2, 4, 8, 16, 32):
        errors.append("ocr.batch_size must be 1, 2, 4, 8, 16 or 32")
    if not 0.0 <= cfg.ocr.confidence_review_threshold <= 1.0:
        errors.append("ocr.confidence_review_threshold must be within [0, 1]")
    from .device import is_valid_device

    if not is_valid_device(cfg.hardware.device):
        errors.append("hardware.device must be cpu, auto, gpu or gpu:N")
    if not 1 <= cfg.hardware.cpu_threads <= 32:
        errors.append("hardware.cpu_threads must be within [1, 32]")
    if not 1 <= cfg.field.min_digits <= cfg.field.max_digits:
        errors.append("field.min_digits must be >= 1 and <= field.max_digits")
    b = cfg.blank_detection
    if not 0 < b.uncertain_min_pixels <= b.nonblank_min_pixels:
        errors.append("blank_detection: need 0 < uncertain_min_pixels <= nonblank_min_pixels")
    if cfg.ocr.primary_variant not in cfg.preprocessing.enabled_variants():
        errors.append(f"ocr.primary_variant '{cfg.ocr.primary_variant}' must be an enabled preprocessing variant")
    if not cfg.preprocessing.enabled_variants():
        errors.append("preprocessing: at least one variant must be enabled")
    for lo, hi in cfg.preprocessing.red_hue_ranges:
        if not 0 <= lo <= hi <= 180:
            errors.append(f"preprocessing.red_hue_ranges entry [{lo}, {hi}] invalid (OpenCV hue 0-180)")
    if errors:
        raise ConfigError("Invalid configuration:\n  - " + "\n  - ".join(errors))


def load_config(path: str | Path) -> AppConfig:
    """Load and validate a YAML configuration file."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ConfigError("Top-level YAML must be a mapping")
    unknown = set(raw) - set(_SECTION_CLASSES)
    if unknown:
        raise ConfigError(f"Unknown config sections: {sorted(unknown)}")
    cfg = AppConfig(**{name: _build_section(name, raw.get(name)) for name in _SECTION_CLASSES})
    validate_config(cfg)
    return cfg
