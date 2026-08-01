"""Orchestration for isolated, local meeting-window vision."""

from datetime import datetime
from threading import Lock

from app.vision.config import VisionConfig
from app.vision.models import Participant, VisionResult
from app.vision.ocr_detector import OcrDetector
from app.vision.participant_detector import ParticipantDetector
from app.vision.screen_capture import ScreenCapture
from app.vision.window_detector import MeetingWindowDetector
from app.vision.active_speaker_detector import ActiveSpeakerDetector
from app.vision.speaker_tracker import SpeakerTracker


class VisionService:
    """Capture the desktop, isolate a meeting window, and detect tile contours with OCR."""

    def __init__(
        self,
        screen_capture: ScreenCapture | None = None,
        window_detector: MeetingWindowDetector | None = None,
        participant_detector: ParticipantDetector | None = None,
        ocr_detector: OcrDetector | None = None,
        active_speaker_detector: ActiveSpeakerDetector | None = None,
        speaker_tracker: SpeakerTracker | None = None,
        config: VisionConfig | None = None,
    ) -> None:
        self._config = config or VisionConfig()
        self._screen_capture = screen_capture or ScreenCapture()
        self._window_detector = window_detector or MeetingWindowDetector()
        self._participant_detector = participant_detector or ParticipantDetector(self._config)
        self._ocr_detector = ocr_detector or OcrDetector(gpu=False)
        self._active_speaker_detector = active_speaker_detector or ActiveSpeakerDetector()
        self._speaker_tracker = speaker_tracker or SpeakerTracker(
            rise_time=0.25,
            decay_time=self._config.speaker_smoothing_window,
            active_threshold=self._config.speaker_threshold,
        )

        # Cache mapping unique stable ID -> dict of details
        self._participant_cache: dict[str, dict] = {}
        self._last_ocr_run_time: datetime | None = None

    def _find_matching_cache_key(self, box) -> str | None:
        """Find the cached participant with the highest overlap above threshold."""
        best_key = None
        best_overlap = -1.0
        for key, cached in self._participant_cache.items():
            overlap = ParticipantDetector._overlap_ratio(box, cached["bounding_box"])
            if overlap >= self._config.ocr_overlap_threshold:
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_key = key
        return best_key

    def inspect_once(self) -> VisionResult:
        """Capture and analyze one meeting screen, executing OCR and caching names."""
        frame = self._screen_capture.capture_once()
        meeting_window = self._window_detector.find_meeting_window()
        if meeting_window is None:
            return VisionResult(frame=frame, meeting_window=None, participants=())

        box = meeting_window.bounding_box
        left = max(0, box.x - frame.origin_x)
        top = max(0, box.y - frame.origin_y)
        right = min(frame.image.shape[1], left + box.width)
        bottom = min(frame.image.shape[0], top + box.height)
        crop = frame.image[top:bottom, left:right]

        detected_tiles = self._participant_detector.detect(
            crop,
            origin_x=frame.origin_x + left,
            origin_y=frame.origin_y + top,
            timestamp=frame.timestamp,
        )

        # Determine if it's time to run OCR (every 5 seconds)
        run_ocr = False
        if self._last_ocr_run_time is None:
            run_ocr = True
        else:
            time_delta = (frame.timestamp - self._last_ocr_run_time).total_seconds()
            if time_delta >= self._config.ocr_interval_seconds:
                run_ocr = True

        # Pre-match all detected tiles to cached entries
        tile_to_cache_key = {}
        for idx, tile in enumerate(detected_tiles):
            key = self._find_matching_cache_key(tile.bounding_box)
            if key is not None:
                tile_to_cache_key[idx] = key

        if run_ocr:
            ocr_results = []
            for idx, tile in enumerate(detected_tiles):
                name, confidence = self._ocr_detector.detect_name(
                    frame.image,
                    tile.bounding_box,
                    frame.origin_x,
                    frame.origin_y,
                    meeting_window.platform_name,
                )
                ocr_results.append({
                    "index": idx,
                    "name": name,
                    "confidence": confidence,
                })

            # Ignore duplicate OCR: keep the one with the highest confidence
            final_ocr_results = {}
            for res in ocr_results:
                name = res["name"]
                if name == "UNKNOWN":
                    continue
                norm_name = name.lower()
                if norm_name not in final_ocr_results:
                    final_ocr_results[norm_name] = res
                else:
                    if res["confidence"] > final_ocr_results[norm_name]["confidence"]:
                        prev_res = final_ocr_results[norm_name]
                        prev_res["name"] = "UNKNOWN"
                        prev_res["confidence"] = 0.0
                        final_ocr_results[norm_name] = res
                    else:
                        res["name"] = "UNKNOWN"
                        res["confidence"] = 0.0

            # Update cache and build participant list
            final_participants = []
            for idx, tile in enumerate(detected_tiles):
                res = ocr_results[idx]
                name = res["name"]
                confidence = res["confidence"]
                cached_key = tile_to_cache_key.get(idx)

                if cached_key is not None:
                    if name != "UNKNOWN":
                        self._participant_cache[cached_key].update({
                            "display_name": name,
                            "confidence": confidence,
                            "bounding_box": tile.bounding_box,
                            "last_seen": frame.timestamp,
                        })
                    else:
                        self._participant_cache[cached_key].update({
                            "bounding_box": tile.bounding_box,
                            "last_seen": frame.timestamp,
                        })
                    p_id = cached_key
                    p_name = self._participant_cache[cached_key]["display_name"]
                    p_conf = self._participant_cache[cached_key]["confidence"]
                else:
                    if name != "UNKNOWN":
                        cached_key = f"participant-{len(self._participant_cache) + 1}"
                        self._participant_cache[cached_key] = {
                            "display_name": name,
                            "confidence": confidence,
                            "bounding_box": tile.bounding_box,
                            "last_seen": frame.timestamp,
                        }
                        p_id = cached_key
                        p_name = name
                        p_conf = confidence
                    else:
                        p_id = tile.id
                        p_name = "UNKNOWN"
                        p_conf = None

                is_speaking_instant, speak_conf = self._active_speaker_detector.detect(
                    frame.image,
                    tile.bounding_box,
                    frame.origin_x,
                    frame.origin_y,
                    meeting_window.platform_name,
                )
                
                is_active, _ = self._speaker_tracker.update(
                    p_id,
                    is_speaking_instant,
                    speak_conf,
                    frame.timestamp,
                )

                final_participants.append(
                    Participant(
                        id=p_id,
                        display_name=p_name,
                        bounding_box=tile.bounding_box,
                        is_active_speaker=tile.is_active_speaker,
                        last_seen=frame.timestamp,
                        confidence=p_conf,
                        is_active=is_active,
                    )
                )

            self._last_ocr_run_time = frame.timestamp
        else:
            # Reuse cached names and confidences
            final_participants = []
            for idx, tile in enumerate(detected_tiles):
                cached_key = tile_to_cache_key.get(idx)
                if cached_key is not None:
                    self._participant_cache[cached_key].update({
                        "bounding_box": tile.bounding_box,
                        "last_seen": frame.timestamp,
                    })
                    p_id = cached_key
                    p_name = self._participant_cache[cached_key]["display_name"]
                    p_conf = self._participant_cache[cached_key]["confidence"]
                else:
                    p_id = tile.id
                    p_name = "UNKNOWN"
                    p_conf = None

                is_speaking_instant, speak_conf = self._active_speaker_detector.detect(
                    frame.image,
                    tile.bounding_box,
                    frame.origin_x,
                    frame.origin_y,
                    meeting_window.platform_name,
                )
                
                is_active, _ = self._speaker_tracker.update(
                    p_id,
                    is_speaking_instant,
                    speak_conf,
                    frame.timestamp,
                )

                final_participants.append(
                    Participant(
                        id=p_id,
                        display_name=p_name,
                        bounding_box=tile.bounding_box,
                        is_active_speaker=tile.is_active_speaker,
                        last_seen=frame.timestamp,
                        confidence=p_conf,
                        is_active=is_active,
                    )
                )

        # Prune cache entries older than 30 seconds
        prune_keys = [
            key
            for key, cached in self._participant_cache.items()
            if (frame.timestamp - cached["last_seen"]).total_seconds() > 30.0
        ]
        for key in prune_keys:
            del self._participant_cache[key]
            
        # Update missing speakers and prune tracker
        seen_ids = {p.id for p in final_participants}
        for key in list(self._speaker_tracker._states.keys()):
            if key not in seen_ids:
                self._speaker_tracker.update_inactive_missing(key, frame.timestamp)
                
        self._speaker_tracker.prune(max_idle_seconds=30.0, current_time=frame.timestamp)

        return VisionResult(
            frame=frame,
            meeting_window=meeting_window,
            participants=tuple(final_participants),
        )


_vision_service: VisionService | None = None
_vision_service_lock = Lock()


def get_vision_service() -> VisionService:
    """Return the process-wide isolated vision service."""
    global _vision_service
    with _vision_service_lock:
        if _vision_service is None:
            _vision_service = VisionService()
        return _vision_service
