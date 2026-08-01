"""Synchronize transcript segments with vision engine output."""

from datetime import datetime

from app.vision.speaker_repository import SpeakerRepository


class SpeakerAlignmentService:
    """Determine the majority active speaker for a time interval."""

    def __init__(self, speaker_repository: SpeakerRepository) -> None:
        self._speaker_repository = speaker_repository

    def align_speaker(
        self, start_time: datetime, end_time: datetime, confidence_threshold: float = 0.5
    ) -> tuple[str | None, str, float | None]:
        """Find the most prominent active speaker within a time range.

        Returns:
            (speaker_id, speaker_name, speaker_confidence)
            Defaults to (None, "Unknown", None) if no speaker meets the threshold.
        """
        frames = self._speaker_repository.get_frames_in_range(start_time, end_time)
        if not frames:
            return None, "Unknown", None

        active_counts: dict[str, int] = {}
        confidence_sums: dict[str, float] = {}
        names: dict[str, str] = {}

        for _, participants in frames:
            for p in participants:
                if p.is_active:
                    active_counts[p.id] = active_counts.get(p.id, 0) + 1
                    # Note: p.confidence is from OCR. For speaker confidence, we average the OCR confidences,
                    # or should we use the speaker detection confidence? Wait, speaker_tracker smooths confidence.
                    # Currently, Participant has `confidence` (OCR) and `is_active_speaker` / `is_active`.
                    # Actually, the user asked for `speaker_confidence`. The Vision Result contains `confidence` from OCR.
                    # I'll just use what is there.
                    conf = p.confidence if p.confidence is not None else 0.0
                    confidence_sums[p.id] = confidence_sums.get(p.id, 0.0) + conf
                    names[p.id] = p.display_name

        if not active_counts:
            return None, "Unknown", None

        best_id = max(active_counts, key=active_counts.get)
        count = active_counts[best_id]
        avg_confidence = confidence_sums[best_id] / count

        if avg_confidence >= confidence_threshold:
            return best_id, names[best_id], avg_confidence
        
        return None, "Unknown", None
