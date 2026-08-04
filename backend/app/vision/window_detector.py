"""Windows title-bar detection for common video-conferencing applications."""

from ctypes import WINFUNCTYPE, POINTER, byref, c_bool, c_int, create_unicode_buffer, windll
from ctypes.wintypes import HWND, LPARAM, RECT
import sys

from app.vision.models import BoundingBox, MeetingWindow


class MeetingWindowDetector:
    """Find the foremost visible Google Meet, Zoom, or Teams window by title."""

    _PLATFORM_TITLE_MARKERS = {
        "Google Meet": ("meet.google.com", "google meet", "meet -"),
        "Zoom": ("zoom meeting", "zoom workplace", "zoom"),
        "Microsoft Teams": ("microsoft teams", "teams"),
    }

    def find_meeting_window(self) -> MeetingWindow | None:
        """Return the largest visible matching Windows application window."""
        if sys.platform != "win32":
            raise RuntimeError("Meeting-window detection currently supports Windows only")
        candidates: list[tuple[int, MeetingWindow]] = []

        @WINFUNCTYPE(c_bool, HWND, LPARAM)
        def visit(hwnd: HWND, _lparam: LPARAM) -> bool:
            if not windll.user32.IsWindowVisible(hwnd):
                return True
            length = windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            title = create_unicode_buffer(length + 1)
            windll.user32.GetWindowTextW(hwnd, title, length + 1)
            platform = self._platform_for_title(title.value)
            if platform is None:
                return True
            rect = RECT()
            if not windll.user32.GetWindowRect(hwnd, byref(rect)):
                return True
            width, height = rect.right - rect.left, rect.bottom - rect.top
            if width <= 0 or height <= 0:
                return True
            window = MeetingWindow(
                bounding_box=BoundingBox(rect.left, rect.top, width, height),
                platform_name=platform,
            )
            candidates.append((width * height, window))
            return True

        windll.user32.EnumWindows(visit, 0)
        return max(candidates, key=lambda candidate: candidate[0])[1] if candidates else None

    def _platform_for_title(self, title: str) -> str | None:
        normalized_title = title.lower()
        for platform, markers in self._PLATFORM_TITLE_MARKERS.items():
            if any(marker in normalized_title for marker in markers):
                return platform
        return None
