import sys
import os
import glob
sys.path.insert(0, os.path.abspath("."))

from datetime import datetime, timezone
import logging
logging.basicConfig(level=logging.INFO)

from app.database.session import SessionLocal
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.audio.buffer import AudioChunk
from app.audio.devices import AudioSource
from app.transcription.whisper_service import get_whisper_service
from app.transcription.pipeline import TranscriptPersistencePipeline
from app.services.transcript_service import TranscriptService
from app.repositories.transcript_repository import TranscriptRepository

# Find a wav file we generated in AppData/Local/Temp/meetingpilot/audio/
wav_files = sorted(glob.glob(os.path.join(os.environ["TEMP"], "meetingpilot", "audio", "**", "*.wav"), recursive=True), key=os.path.getmtime, reverse=True)
if not wav_files:
    print("No WAV files found. Run scratch/test_audio.py first.")
    sys.exit(1)

wav_path = wav_files[0]
print(f"Using WAV file: {wav_path}")

db = SessionLocal()
try:
    # Create mock meeting
    meeting = Meeting(
        title="Test Pipeline Meeting",
        status=MeetingStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    print(f"Created meeting ID: {meeting.id}")

    # Build AudioChunk object
    audio_chunk = AudioChunk(
        path=wav_path,
        source=AudioSource.MICROPHONE,
        sample_rate=16000,
        frame_count=160000, # 10s
        chunk_index=0,
        started_at=meeting.started_at,
        created_at=datetime.now(timezone.utc),
    )

    whisper_service = get_whisper_service()
    transcript_service = TranscriptService(TranscriptRepository(db))
    
    pipeline = TranscriptPersistencePipeline(
        meeting_id=meeting.id,
        meeting_started_at=meeting.started_at,
        whisper_service=whisper_service,
        transcript_service=transcript_service,
    )

    print("Running pipeline.handle_audio_chunk...")
    transcripts = pipeline.handle_audio_chunk(audio_chunk)
    print(f"Success! Generated {len(transcripts)} transcripts.")
    for t in transcripts:
        print(f"Transcript ID: {t.id}, text: {t.text}")
except Exception as e:
    print("Pipeline failed with exception:")
    import traceback
    traceback.print_exc()
finally:
    db.close()
