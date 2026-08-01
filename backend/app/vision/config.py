"""Configuration for local screen-based meeting vision."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisionConfig:
    """Tune capture cadence and conservative tile contour filtering."""

    capture_interval_seconds: float = 1.0
    minimum_tile_width: int = 100
    minimum_tile_height: int = 80
    minimum_tile_area_ratio: float = 0.02
    ocr_interval_seconds: float = 5.0
    ocr_overlap_threshold: float = 0.5
    speaker_smoothing_window: float = 1.5
    speaker_threshold: float = 0.5
