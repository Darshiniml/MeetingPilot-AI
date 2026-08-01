import datetime
import numpy as np
import pytest

from app.vision.active_speaker_detector import ActiveSpeakerDetector
from app.vision.speaker_tracker import SpeakerTracker
from app.vision.models import BoundingBox

def test_active_speaker_detector_no_color():
    detector = ActiveSpeakerDetector()
    # 100x100 black image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    box = BoundingBox(x=10, y=10, width=80, height=80)
    
    is_speaking, confidence = detector.detect(img, box, 0, 0, platform_name="Google Meet")
    assert not is_speaking
    assert confidence == 0.0

def test_active_speaker_detector_with_color():
    detector = ActiveSpeakerDetector()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Create a green border
    # Google Meet green range in HSV: 35-85 for Hue. 
    # BGR for pure green is (0, 255, 0). Let's use (0, 255, 0)
    # BGR (0, 255, 0) -> HSV (60, 255, 255)
    img[10:13, 10:90] = [0, 255, 0] # Top edge
    img[87:90, 10:90] = [0, 255, 0] # Bottom edge
    img[10:90, 10:13] = [0, 255, 0] # Left edge
    img[10:90, 87:90] = [0, 255, 0] # Right edge
    
    box = BoundingBox(x=10, y=10, width=80, height=80)
    is_speaking, confidence = detector.detect(img, box, 0, 0, platform_name="Google Meet")
    
    assert is_speaking
    assert confidence > 0.0

def test_speaker_tracker_smoothing_and_switching():
    tracker = SpeakerTracker(rise_time=0.25, decay_time=1.0, active_threshold=0.5)
    start_time = datetime.datetime(2026, 1, 1, 12, 0, 0)
    
    p_id = "p1"
    
    # 1. Initial state (not active)
    is_active, conf = tracker.update(p_id, False, 0.0, start_time)
    assert not is_active
    assert conf == 0.0
    
    # 2. Brief flash (less than rise_time)
    flash_time = start_time + datetime.timedelta(seconds=0.1)
    is_active, conf = tracker.update(p_id, True, 1.0, flash_time)
    assert not is_active, "Should not be active yet due to smoothing"
    
    # 3. Sustained speaking (crosses threshold)
    sustained_time = start_time + datetime.timedelta(seconds=0.3)
    is_active, conf = tracker.update(p_id, True, 1.0, sustained_time)
    assert is_active, "Should be active after sustained speaking"
    
    # 4. Stop speaking (should remain active during decay)
    stop_time = sustained_time + datetime.timedelta(seconds=0.3)
    is_active, conf = tracker.update(p_id, False, 0.0, stop_time)
    assert is_active, "Should remain active during decay period"
    
    # 5. Long silence (should drop active state)
    silence_time = stop_time + datetime.timedelta(seconds=1.2)
    is_active, conf = tracker.update(p_id, False, 0.0, silence_time)
    assert not is_active, "Should drop active state after decay_time"

def test_speaker_tracker_missing_decay():
    tracker = SpeakerTracker(rise_time=0.2, decay_time=1.0, active_threshold=0.5)
    start_time = datetime.datetime(2026, 1, 1, 12, 0, 0)
    p_id = "p2"
    
    # Make active
    is_active, _ = tracker.update(p_id, True, 1.0, start_time)
    is_active, _ = tracker.update(p_id, True, 1.0, start_time + datetime.timedelta(seconds=0.5))
    assert is_active
    
    # Missing decay
    tracker.update_inactive_missing(p_id, start_time + datetime.timedelta(seconds=0.8))
    assert tracker._states[p_id]["score"] < 1.0 # Score should have dropped
    
    tracker.update_inactive_missing(p_id, start_time + datetime.timedelta(seconds=2.0))
    assert tracker._states[p_id]["score"] == 0.0

def test_speaker_tracker_pruning():
    tracker = SpeakerTracker()
    start_time = datetime.datetime(2026, 1, 1, 12, 0, 0)
    
    tracker.update("p_stale", True, 1.0, start_time)
    tracker.update("p_fresh", True, 1.0, start_time + datetime.timedelta(seconds=25))
    
    # Prune at +35 seconds
    tracker.prune(max_idle_seconds=30.0, current_time=start_time + datetime.timedelta(seconds=35))
    
    assert "p_stale" not in tracker._states
    assert "p_fresh" in tracker._states
