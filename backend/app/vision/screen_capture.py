"""MSS-backed desktop capture for Windows and other supported platforms."""

from collections.abc import Iterator
from datetime import datetime, timezone
from time import sleep

import numpy as np

from app.vision.models import CaptureFrame


class ScreenCapture:
    """Capture the virtual desktop without using PyAutoGUI."""

    def capture_once(self) -> CaptureFrame:
        """Capture the full virtual desktop and return it with a UTC timestamp."""
        try:
            import mss
        except ModuleNotFoundError as error:
            raise RuntimeError("MSS is required for vision capture: pip install mss") from error
        try:
            with mss.mss() as screen:
                monitor = screen.monitors[0]
                grabbed = screen.grab(monitor)
        except Exception as error:
            raise RuntimeError(
                "MSS could not capture the desktop. Run this from the interactive "
                "Windows user session and verify that screen capture is permitted."
            ) from error
        image = np.asarray(grabbed)[:, :, :3].copy()
        return CaptureFrame(
            image=image,
            timestamp=datetime.now(timezone.utc),
            origin_x=int(monitor["left"]),
            origin_y=int(monitor["top"]),
        )

    def capture_forever(self, *, interval_seconds: float = 1.0) -> Iterator[CaptureFrame]:
        """Yield one desktop frame per interval for consumers that need polling."""
        while True:
            yield self.capture_once()
            sleep(interval_seconds)
