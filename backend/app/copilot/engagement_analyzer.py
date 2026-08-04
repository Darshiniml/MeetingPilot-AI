"""Analyzes conversational balance, participant speaking durations, and group engagement."""

from typing import Any


class EngagementAnalyzer:
    """Measures speaker dominance, conversational balance, silent participants, and interruptions."""

    def analyze(
        self,
        speaking_times: dict[str, float],
        participants: list[str],
        interruptions_count: int = 0
    ) -> dict[str, Any]:
        """Compute participation stats and return a formatted engagement report."""
        if not speaking_times:
            return {
                "dominant_speaker": None,
                "silent_participants": participants,
                "average_speaking_time": 0.0,
                "meeting_balance": 1.0,
                "interruptions": interruptions_count,
                "participation_shares": {}
            }

        total_time = sum(speaking_times.values())
        
        # 1. Dominant speaker
        dominant_speaker = max(speaking_times, key=speaking_times.get) if speaking_times else None

        # 2. Silent participants (members present in list but with 0 or <1s speaking time)
        silent_participants = [
            p for p in participants
            if speaking_times.get(p, 0.0) < 1.0
        ]

        # 3. Average speaking time
        active_speakers = [t for t in speaking_times.values() if t > 0.0]
        avg_speaking_time = (total_time / len(active_speakers)) if active_speakers else 0.0

        # 4. Speaking share percentages
        shares = {
            speaker: (time_spent / total_time)
            for speaker, time_spent in speaking_times.items()
        }

        # 5. Meeting Balance (1.0 = perfect uniform share, 0.0 = one dominant speaker)
        n = len(speaking_times)
        if n <= 1:
            meeting_balance = 1.0
        else:
            uniform_share = 1.0 / n
            variance = sum((share - uniform_share) ** 2 for share in shares.values()) / n
            max_variance = (n - 1) / (n ** 2)
            meeting_balance = max(0.0, 1.0 - (variance / max_variance) if max_variance > 0 else 1.0)

        return {
            "dominant_speaker": dominant_speaker,
            "silent_participants": silent_participants,
            "average_speaking_time": round(avg_speaking_time, 2),
            "meeting_balance": round(meeting_balance, 3),
            "interruptions": interruptions_count,
            "participation_shares": {k: round(v, 3) for k, v in shares.items()}
        }
