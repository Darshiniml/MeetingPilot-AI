"""Contour and grid-layout participant-tile detection without AI."""

from datetime import datetime

import numpy as np

from app.vision.config import VisionConfig
from app.vision.models import BoundingBox, Participant


class ParticipantDetector:
    """Find likely rectangular participant tiles in a cropped meeting window."""

    def __init__(self, config: VisionConfig | None = None) -> None:
        self._config = config or VisionConfig()

    def detect(self, image: np.ndarray, *, origin_x: int, origin_y: int, timestamp: datetime) -> list[Participant]:
        """Return large, non-overlapping rectangular tiles with UNKNOWN names."""
        try:
            import cv2
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "OpenCV is required for participant detection: pip install opencv-python"
            ) from error
        if image.size == 0:
            return []
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(grayscale, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        minimum_area = image.shape[0] * image.shape[1] * self._config.minimum_tile_area_ratio
        boxes: list[BoundingBox] = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = width * height
            aspect_ratio = width / height if height else 0
            if (
                width < self._config.minimum_tile_width
                or height < self._config.minimum_tile_height
                or area < minimum_area
                or not 0.5 <= aspect_ratio <= 2.5
            ):
                continue
            candidate = BoundingBox(origin_x + x, origin_y + y, width, height)
            if not any(self._overlap_ratio(candidate, existing) > 0.8 for existing in boxes):
                boxes.append(candidate)
        boxes.sort(key=lambda box: (box.y, box.x))
        return [
            Participant(
                id=f"tile-{index + 1}",
                display_name="UNKNOWN",
                bounding_box=box,
                is_active_speaker=False,
                last_seen=timestamp,
            )
            for index, box in enumerate(boxes)
        ]

    @staticmethod
    def _overlap_ratio(left: BoundingBox, right: BoundingBox) -> float:
        overlap_width = max(0, min(left.x + left.width, right.x + right.width) - max(left.x, right.x))
        overlap_height = max(0, min(left.y + left.height, right.y + right.height) - max(left.y, right.y))
        overlap_area = overlap_width * overlap_height
        return overlap_area / min(left.width * left.height, right.width * right.height)
