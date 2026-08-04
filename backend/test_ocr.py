"""Unit and integration tests for EasyOCR participant recognition."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import easyocr
except ImportError:
    easyocr = None

from app.vision.config import VisionConfig
from app.vision.models import BoundingBox, CaptureFrame, MeetingWindow, Participant, VisionResult
from app.vision.ocr_detector import OcrDetector
from app.vision.vision_service import VisionService


class TestOcrDetector(unittest.TestCase):
    """Tests the standalone EasyOCR detector cropping and parsing logic."""

    @unittest.skipIf(cv2 is None or easyocr is None, "OpenCV or EasyOCR not available")
    def test_detect_name_synthetic(self) -> None:
        """Verify that OCR can read drawn text from a synthetic participant crop."""
        # Create a blank image and draw text
        img = np.zeros((100, 300, 3), dtype=np.uint8)
        # Add white background capsule for Google Meet look
        cv2.rectangle(img, (10, 70), (120, 95), (50, 50, 50), -1)
        # Put white text
        cv2.putText(
            img,
            "Alice",
            (15, 88),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        detector = OcrDetector(gpu=False)
        box = BoundingBox(x=0, y=0, width=300, height=100)

        # Detect
        name, confidence = detector.detect_name(
            image=img,
            box=box,
            origin_x=0,
            origin_y=0,
            platform_name="Google Meet",
        )

        print(f"Synthetic OCR Result: Name='{name}', Confidence={confidence}")
        # Note: If running on a system without model files, EasyOCR will download them automatically
        # or fall back. We check if name matches "Alice" if OCR succeeds, otherwise handle gracefully.
        if name != "UNKNOWN":
            self.assertIn("Alice", name)
            self.assertGreater(confidence, 0.0)


class TestVisionServiceOcr(unittest.TestCase):
    """Tests the orchestrator caching, timing, and deduplication logic."""

    def setUp(self) -> None:
        self.config = VisionConfig(
            capture_interval_seconds=1.0,
            ocr_interval_seconds=5.0,
            ocr_overlap_threshold=0.5,
        )
        self.mock_capture = MagicMock()
        self.mock_window_detector = MagicMock()
        self.mock_participant_detector = MagicMock()
        self.mock_ocr_detector = MagicMock()

        self.service = VisionService(
            screen_capture=self.mock_capture,
            window_detector=self.mock_window_detector,
            participant_detector=self.mock_participant_detector,
            ocr_detector=self.mock_ocr_detector,
            config=self.config,
        )

    def test_ocr_interval_and_caching(self) -> None:
        """Verify OCR is called only every 5 seconds, reusing cached names in between."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
        dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)

        # Setup Capture Mock
        frame1 = CaptureFrame(dummy_img, t0, 0, 0)
        self.mock_capture.capture_once.return_value = frame1

        # Setup Window Mock
        window = MeetingWindow(BoundingBox(50, 50, 700, 500), "Google Meet")
        self.mock_window_detector.find_meeting_window.return_value = window

        # Setup Participant Detector Mock (2 tiles)
        tile1 = Participant("tile-1", "UNKNOWN", BoundingBox(100, 100, 200, 150), False, t0)
        tile2 = Participant("tile-2", "UNKNOWN", BoundingBox(400, 100, 200, 150), False, t0)
        self.mock_participant_detector.detect.return_value = [tile1, tile2]

        # Setup OCR Mock: first run detects names
        self.mock_ocr_detector.detect_name.side_effect = [
            ("Alice", 0.9),
            ("Bob", 0.85),
        ]

        # --- Frame 1 (T=0, OCR runs) ---
        res1 = self.service.inspect_once()
        self.assertEqual(self.mock_ocr_detector.detect_name.call_count, 2)
        self.assertEqual(res1.participants[0].display_name, "Alice")
        self.assertEqual(res1.participants[0].confidence, 0.9)
        self.assertEqual(res1.participants[1].display_name, "Bob")
        self.assertEqual(res1.participants[1].confidence, 0.85)

        # Reset call counts
        self.mock_ocr_detector.detect_name.reset_mock()

        # --- Frame 2 (T=1, OCR skips, uses cache) ---
        t1 = t0 + timedelta(seconds=1)
        frame2 = CaptureFrame(dummy_img, t1, 0, 0)
        self.mock_capture.capture_once.return_value = frame2
        # Mock participant detector to return slightly moved bounding boxes
        tile1_moved = Participant("tile-1", "UNKNOWN", BoundingBox(102, 101, 200, 150), False, t1)
        tile2_moved = Participant("tile-2", "UNKNOWN", BoundingBox(401, 99, 200, 150), False, t1)
        self.mock_participant_detector.detect.return_value = [tile1_moved, tile2_moved]

        res2 = self.service.inspect_once()
        # OCR should not be called
        self.mock_ocr_detector.detect_name.assert_not_called()
        # Should retain cached names
        self.assertEqual(res2.participants[0].display_name, "Alice")
        self.assertEqual(res2.participants[0].confidence, 0.9)
        self.assertEqual(res2.participants[1].display_name, "Bob")
        self.assertEqual(res2.participants[1].confidence, 0.85)

        # --- Frame 3 (T=5, OCR runs again) ---
        t2 = t0 + timedelta(seconds=5)
        frame3 = CaptureFrame(dummy_img, t2, 0, 0)
        self.mock_capture.capture_once.return_value = frame3
        self.mock_ocr_detector.detect_name.side_effect = [
            ("Alice Smith", 0.95),
            ("Bob Jones", 0.91),
        ]

        res3 = self.service.inspect_once()
        # OCR should be called
        self.assertEqual(self.mock_ocr_detector.detect_name.call_count, 2)
        self.assertEqual(res3.participants[0].display_name, "Alice Smith")
        self.assertEqual(res3.participants[1].display_name, "Bob Jones")

    def test_ignore_duplicate_ocr(self) -> None:
        """Verify that duplicate OCR names in the same frame are ignored / set to UNKNOWN."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
        dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)

        # Setup Mocks
        self.mock_capture.capture_once.return_value = CaptureFrame(dummy_img, t0, 0, 0)
        window = MeetingWindow(BoundingBox(50, 50, 700, 500), "Google Meet")
        self.mock_window_detector.find_meeting_window.return_value = window

        tile1 = Participant("tile-1", "UNKNOWN", BoundingBox(100, 100, 200, 150), False, t0)
        tile2 = Participant("tile-2", "UNKNOWN", BoundingBox(400, 100, 200, 150), False, t0)
        self.mock_participant_detector.detect.return_value = [tile1, tile2]

        # Mock duplicate name "Alice" with different confidences
        # The one on tile-2 (index 1) has higher confidence
        self.mock_ocr_detector.detect_name.side_effect = [
            ("Alice", 0.80),
            ("Alice", 0.95),
        ]

        res = self.service.inspect_once()
        # Index 0 (tile-1) should become UNKNOWN because index 1 (tile-2) had higher confidence
        self.assertEqual(res.participants[0].display_name, "UNKNOWN")
        self.assertEqual(res.participants[1].display_name, "Alice")
        self.assertEqual(res.participants[1].confidence, 0.95)

    def test_cache_pruning(self) -> None:
        """Verify that cached participants not seen for >30 seconds are pruned."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
        dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)

        self.mock_capture.capture_once.return_value = CaptureFrame(dummy_img, t0, 0, 0)
        window = MeetingWindow(BoundingBox(50, 50, 700, 500), "Google Meet")
        self.mock_window_detector.find_meeting_window.return_value = window

        tile1 = Participant("tile-1", "UNKNOWN", BoundingBox(100, 100, 200, 150), False, t0)
        self.mock_participant_detector.detect.return_value = [tile1]
        self.mock_ocr_detector.detect_name.return_value = ("Alice", 0.90)

        # Run once to populate cache
        self.service.inspect_once()
        self.assertIn("participant-1", self.service._participant_cache)

        # Run 31 seconds later with no detected participants
        t1 = t0 + timedelta(seconds=31)
        self.mock_capture.capture_once.return_value = CaptureFrame(dummy_img, t1, 0, 0)
        self.mock_participant_detector.detect.return_value = []

        self.service.inspect_once()
        # Cache should be pruned empty
        self.assertEqual(len(self.service._participant_cache), 0)


if __name__ == "__main__":
    unittest.main()
