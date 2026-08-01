"""Visual indicator active speaker detection based on border highlighting."""

import logging
import numpy as np

from app.vision.models import BoundingBox

logger = logging.getLogger(__name__)


class ActiveSpeakerDetector:
    """Detects active speakers by analyzing colored border outlines of participant tiles."""

    # HSV Color Ranges for active speaker borders
    # OpenCV HSV: Hue [0-180], Saturation [0-255], Value [0-255]
    _PLATFORM_HSV_RANGES = {
        "Google Meet": [
            # Green border / active speaker capsule highlight
            {"low": np.array([35, 50, 50]), "high": np.array([85, 255, 255])}
        ],
        "Microsoft Teams": [
            # Purple/Blue outline
            {"low": np.array([100, 50, 50]), "high": np.array([140, 255, 255])}
        ],
        "Zoom": [
            # Green / Yellow-Green highlighted border
            {"low": np.array([20, 40, 50]), "high": np.array([90, 255, 255])}
        ],
    }

    def detect(
        self,
        image: np.ndarray,
        box: BoundingBox,
        origin_x: int,
        origin_y: int,
        platform_name: str | None = None,
    ) -> tuple[bool, float]:
        """Analyze the border pixels of a participant tile to determine speaking status.

        Returns:
            (is_speaking: bool, confidence: float)
        """
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError(
                "OpenCV is required for active speaker detection: pip install opencv-python"
            ) from error

        if image.size == 0:
            return False, 0.0

        # Translate absolute desktop coordinates to frame-relative coordinates
        left = box.x - origin_x
        top = box.y - origin_y
        width = box.width
        height = box.height
        right = left + width
        bottom = top + height

        # Extract border pixels (outer 3 pixels boundary of the tile)
        border_pixels = self._get_border_pixels(image, left, top, right, bottom, thickness=3)
        if border_pixels.size == 0:
            return False, 0.0

        # Convert border pixels to HSV
        # reshape to (1, N, 3) to use cvtColor
        border_hsv = cv2.cvtColor(border_pixels.reshape(1, -1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)

        # Get color ranges for the platform or check all if platform is unknown
        ranges = []
        if platform_name in self._PLATFORM_HSV_RANGES:
            ranges = self._PLATFORM_HSV_RANGES[platform_name]
        else:
            # Check all ranges if platform is unknown
            for r_list in self._PLATFORM_HSV_RANGES.values():
                ranges.extend(r_list)

        # Count matching pixels
        matching_count = 0
        for r in ranges:
            mask = cv2.inRange(
                border_hsv.reshape(1, -1, 3), r["low"].reshape(1, 1, 3), r["high"].reshape(1, 1, 3)
            )
            matching_count += np.sum(mask > 0)

        total_pixels = border_hsv.shape[0]
        matching_ratio = matching_count / total_pixels

        # Determine speaking status and calculate confidence
        # Standard threshold: 10% of border pixels matching the speaker color
        is_speaking = matching_ratio >= 0.10
        # Scale confidence between 0.0 and 1.0 based on matching ratio
        confidence = min(1.0, matching_ratio / 0.30) if is_speaking else 0.0

        return is_speaking, confidence

    def _get_border_pixels(
        self, image: np.ndarray, left: int, top: int, right: int, bottom: int, thickness: int
    ) -> np.ndarray:
        """Extract a 1D array of pixels lying along the borders of the bounding box."""
        h, w, _ = image.shape

        # Clip values to image size
        left = max(0, min(left, w))
        right = max(0, min(right, w))
        top = max(0, min(top, h))
        bottom = max(0, min(bottom, h))

        if right <= left or bottom <= top:
            return np.empty((0, 3), dtype=np.uint8)

        # Retrieve boundary slices
        top_slice = image[top : min(top + thickness, bottom), left:right]
        bottom_slice = image[max(top, bottom - thickness) : bottom, left:right]
        left_slice = image[top:bottom, left : min(left + thickness, right)]
        right_slice = image[top:bottom, max(left, right - thickness) : right]

        slices = []
        for s in [top_slice, bottom_slice, left_slice, right_slice]:
            if s.size > 0:
                slices.append(s.reshape(-1, 3))

        if slices:
            return np.concatenate(slices, axis=0)
        return np.empty((0, 3), dtype=np.uint8)
