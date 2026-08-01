"""EasyOCR-based participant name recognition for meeting windows."""

import logging
from datetime import datetime
import numpy as np

from app.vision.models import BoundingBox

logger = logging.getLogger(__name__)

# Workaround for torchvision operator import compatibility issues on Python 3.14 / newer PyTorch
try:
    import torch
    if hasattr(torch, "library") and hasattr(torch.library, "register_fake"):
        original_register_fake = torch.library.register_fake
        def safe_register_fake(op_name, *args, **kwargs):
            try:
                decorator = original_register_fake(op_name, *args, **kwargs)
                def safe_decorator(func):
                    try:
                        return decorator(func)
                    except Exception as e:
                        logger.warning(f"Bypassing fake decorator execution for {op_name}: {e}")
                        return func
                return safe_decorator
            except Exception as e:
                logger.warning(f"Bypassing fake registration decorator creation for {op_name}: {e}")
                return lambda f: f
        torch.library.register_fake = safe_register_fake
        logger.info("Successfully patched torch.library.register_fake for compatibility")
except Exception as e:
    logger.warning(f"Failed to patch torch compatibility: {e}")


class OcrDetector:
    """Cropping and OCR orchestration for participant tiles using EasyOCR."""

    def __init__(self, gpu: bool = False) -> None:
        self._gpu = gpu
        self._reader = None

    def _get_reader(self):
        """Lazy load the EasyOCR reader to save startup time."""
        if self._reader is None:
            try:
                import easyocr
                import torch
                # Enable GPU if requested and CUDA is available
                use_cuda = self._gpu and torch.cuda.is_available()
                logger.info(f"Initializing EasyOCR reader (GPU={use_cuda})...")
                self._reader = easyocr.Reader(["en"], gpu=use_cuda)
            except ModuleNotFoundError as error:
                raise RuntimeError(
                    "EasyOCR and PyTorch are required for OCR detection: pip install easyocr torch torchvision"
                ) from error
        return self._reader

    def crop_name_region(
        self,
        image: np.ndarray,
        box: BoundingBox,
        origin_x: int,
        origin_y: int,
        platform_name: str | None = None,
    ) -> np.ndarray:
        """Crop the bottom-left region of a participant tile where names are displayed."""
        # Convert desktop coordinates to frame-relative coordinates
        left = box.x - origin_x
        top = box.y - origin_y
        width = box.width
        height = box.height

        # Default: Bottom-left crop
        h_ratio = 0.25
        w_ratio = 0.70

        # Adjust based on platform if needed
        if platform_name == "Google Meet":
            # Avoid the extreme bottom and left margins where capsules have rounding or padding
            h_ratio = 0.28
            w_ratio = 0.75
        elif platform_name == "Zoom":
            h_ratio = 0.25
            w_ratio = 0.70
        elif platform_name == "Microsoft Teams":
            h_ratio = 0.25
            w_ratio = 0.70

        h_crop = int(height * h_ratio)
        w_crop = int(width * w_ratio)

        # Apply safety constraints so we don't crop too small or larger than the tile
        h_crop = max(18, min(h_crop, 60))
        w_crop = max(80, min(w_crop, width))

        y1 = top + height - h_crop
        y2 = top + height
        x1 = left
        x2 = left + w_crop

        # Clip coordinates to frame image boundaries
        y1 = max(0, min(int(y1), image.shape[0]))
        y2 = max(0, min(int(y2), image.shape[0]))
        x1 = max(0, min(int(x1), image.shape[1]))
        x2 = max(0, min(int(x2), image.shape[1]))

        crop = image[y1:y2, x1:x2]

        # Upscale tiny name badges to improve OCR accuracy
        if crop.size > 0 and crop.shape[0] < 36:
            try:
                import cv2
                scale = 2.0
                crop = cv2.resize(
                    crop, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
                )
            except Exception as e:
                logger.warning(f"Could not resize crop: {e}")

        return crop

    def detect_name(
        self,
        image: np.ndarray,
        box: BoundingBox,
        origin_x: int,
        origin_y: int,
        platform_name: str | None = None,
    ) -> tuple[str, float]:
        """Perform OCR on the cropped name region and return (name, confidence)."""
        crop = self.crop_name_region(image, box, origin_x, origin_y, platform_name)
        if crop.size == 0:
            return "UNKNOWN", 0.0

        reader = self._get_reader()
        try:
            # Run OCR on the crop
            results = reader.readtext(crop)
            return self._parse_ocr_results(results)
        except Exception as error:
            logger.error(f"OCR detection failed: {error}")
            return "UNKNOWN", 0.0

    def _parse_ocr_results(self, results: list) -> tuple[str, float]:
        """Parse EasyOCR results list to extract name and confidence."""
        if not results:
            return "UNKNOWN", 0.0

        valid_segments = []
        for bbox, text, conf in results:
            cleaned_text = text.strip()
            if not cleaned_text:
                continue

            # Skip single-character junk symbols that are not letters/digits
            if len(cleaned_text) == 1 and not cleaned_text.isalnum():
                continue

            valid_segments.append((bbox, cleaned_text, float(conf)))

        if not valid_segments:
            return "UNKNOWN", 0.0

        # Sort segments left-to-right based on top-left x-coordinate of bounding box
        valid_segments.sort(key=lambda item: item[0][0][0])

        name = " ".join(item[1] for item in valid_segments)
        avg_confidence = sum(item[2] for item in valid_segments) / len(valid_segments)

        # Filter out empty or pure punctuation results
        name_filtered = "".join(c for c in name if c.isalnum() or c.isspace())
        if not name_filtered.strip():
            return "UNKNOWN", 0.0

        return name.strip(), avg_confidence
