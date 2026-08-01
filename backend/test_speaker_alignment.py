import datetime
import pytest

from app.vision.models import Participant, BoundingBox
from app.vision.speaker_repository import SpeakerRepository
from app.vision.speaker_alignment_service import SpeakerAlignmentService

def _make_participant(p_id, is_active, conf, name):
    return Participant(
        id=p_id,
        display_name=name,
        bounding_box=BoundingBox(0,0,10,10),
        is_active_speaker=is_active,
        is_active=is_active,
        last_seen=datetime.datetime.now(),
        confidence=conf
    )

def test_speaker_alignment_single_speaker():
    repo = SpeakerRepository()
    svc = SpeakerAlignmentService(repo)
    
    start_time = datetime.datetime(2026, 1, 1, 10, 0, 0)
    
    repo.add_frame(start_time + datetime.timedelta(seconds=1), (_make_participant("p1", True, 0.9, "Alice"), _make_participant("p2", False, 0.9, "Bob")))
    repo.add_frame(start_time + datetime.timedelta(seconds=2), (_make_participant("p1", True, 0.9, "Alice"), _make_participant("p2", False, 0.9, "Bob")))
    repo.add_frame(start_time + datetime.timedelta(seconds=3), (_make_participant("p1", False, 0.9, "Alice"), _make_participant("p2", True, 0.8, "Bob")))
    repo.add_frame(start_time + datetime.timedelta(seconds=4), (_make_participant("p1", True, 0.8, "Alice"), _make_participant("p2", False, 0.8, "Bob")))
    repo.add_frame(start_time + datetime.timedelta(seconds=5), (_make_participant("p1", False, 0.8, "Alice"), _make_participant("p2", False, 0.8, "Bob")))
    
    spk_id, name, conf = svc.align_speaker(start_time, start_time + datetime.timedelta(seconds=6))
    
    assert spk_id == "p1"
    assert name == "Alice"
    assert round(conf, 2) == 0.87

def test_speaker_alignment_unknown_fallback():
    repo = SpeakerRepository()
    svc = SpeakerAlignmentService(repo)
    
    start_time = datetime.datetime(2026, 1, 1, 10, 0, 0)
    
    repo.add_frame(start_time + datetime.timedelta(seconds=1), (_make_participant("p1", True, 0.2, "Alice"),))
    repo.add_frame(start_time + datetime.timedelta(seconds=2), (_make_participant("p1", True, 0.2, "Alice"),))
    
    spk_id, name, conf = svc.align_speaker(start_time, start_time + datetime.timedelta(seconds=3), confidence_threshold=0.5)
    
    assert spk_id is None
    assert name == "Unknown"
    assert conf is None

def test_speaker_alignment_no_frames():
    repo = SpeakerRepository()
    svc = SpeakerAlignmentService(repo)
    start_time = datetime.datetime(2026, 1, 1, 10, 0, 0)
    spk_id, name, conf = svc.align_speaker(start_time, start_time + datetime.timedelta(seconds=3))
    assert spk_id is None
    assert name == "Unknown"
    assert conf is None
