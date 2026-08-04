import sys
import os
import time
sys.path.insert(0, os.path.abspath("."))

from datetime import datetime, timezone
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from app.database.session import SessionLocal
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import Transcript
from app.models.vector_embedding import VectorEmbedding
from app.core.dependencies import get_audio_service, get_whisper_service, build_chunk_processor
from app.services.meeting_service import MeetingService
from app.repositories.meeting_repository import MeetingRepository
from app.services.summary_service import SummaryService
from app.services.action_item_service import ActionItemService
from app.repositories.transcript_repository import TranscriptRepository
from app.repositories.summary_repository import SummaryRepository
from app.repositories.action_item_repository import ActionItemRepository
from app.ai.providers import get_llm_provider
from app.transcription.models import TranscriptionResult, TranscriptionSegment

# Mock Whisper transcribing to simulate actual speech
def mock_transcribe_chunk(wav_path):
    print(f"\n[MOCK WHISPER] Transcribing chunk: {wav_path}")
    return TranscriptionResult(
        text="Hello, this is a test transcription segment for MeetingPilot AI.",
        language="en",
        language_probability=0.99,
        segments=(
            TranscriptionSegment(
                start_seconds=0.0,
                end_seconds=5.0,
                text="Hello, this is a test transcription segment",
                confidence=0.95,
                no_speech_probability=0.01
            ),
            TranscriptionSegment(
                start_seconds=5.0,
                end_seconds=10.0,
                text="for MeetingPilot AI.",
                confidence=0.98,
                no_speech_probability=0.01
            )
        ),
        processing_seconds=0.1,
        average_processing_seconds=0.1
    )

db = SessionLocal()
try:
    user = db.query(User).first()
    if not user:
        print("No user found in database. Run debug_register.py first.")
        sys.exit(1)
    print(f"Using User: ID={user.id}, Name={user.name}")

    # Build MeetingService
    meeting_repo = MeetingRepository(db, user_id=user.id)
    summary_service = SummaryService(
        TranscriptRepository(db),
        SummaryRepository(db),
        get_llm_provider()
    )
    action_item_service = ActionItemService(
        TranscriptRepository(db),
        ActionItemRepository(db),
        get_llm_provider()
    )
    
    whisper = get_whisper_service()
    # Inject monkeypatched transcriber
    whisper.transcribe_chunk = mock_transcribe_chunk

    service = MeetingService(
        meeting_repo,
        audio_service=get_audio_service(),
        whisper_service=whisper,
        chunk_processor_factory=build_chunk_processor,
        summary_service=summary_service,
        action_item_service=action_item_service
    )

    print("\n--- Starting E2E Meeting (35 seconds recording) ---")
    state = service.start_meeting()
    meeting_id = state.meeting_id
    print(f"Meeting started! ID: {meeting_id}")
    
    # Wait for 35 seconds
    for i in range(35):
        time.sleep(1)
        # Check for any exceptions from the background audio worker
        get_audio_service().raise_if_failed()
        if (i+1) % 5 == 0:
            # Query transcript count
            db.commit() # Commit session to read latest database updates from other threads
            t_count = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).count()
            print(f"Time: {i+1}s / 35s. Transcripts stored in DB: {t_count}")

    print("\n--- Stopping E2E Meeting ---")
    service.stop_meeting()
    print("Meeting stopped.")

    # Refresh DB session to see committed changes
    db.commit()
    db.expire_all()
    
    # Wait a moment for any last async handler jobs to commit
    time.sleep(2)
    db.commit()

    t_count = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).count()
    
    print("\n--- Final E2E Summary ---")
    print(f"Meeting ID: {meeting_id}")
    print(f"Transcripts stored: {t_count}")
    
    if t_count > 0:
        print("Transcripts:")
        for t in db.query(Transcript).filter(Transcript.meeting_id == meeting_id).all():
            print(f" - Chunk {t.chunk_index}, Seg {t.segment_index} ({t.start_seconds:.1f}s - {t.end_seconds:.1f}s): {t.text}")
            
        # Test ChatService RAG
        from app.services.chat_service import ChatService
        from app.repositories.vector_repository import VectorRepository
        from app.services.embedding_service import get_embedding_service
        
        chat_service = ChatService(
            TranscriptRepository(db),
            VectorRepository(db),
            get_embedding_service(),
            get_llm_provider()
        )
        
        print("\n--- Testing AI Chat RAG retrieves and answers ---")
        try:
            answer = chat_service.answer_question(meeting_id=meeting_id, question="What is this meeting about?")
            print(f"AI Answer: {answer}")
            
            # Print embedding count
            v_count = db.query(VectorEmbedding).filter(VectorEmbedding.meeting_id == meeting_id).count()
            print(f"Embeddings stored in vector table: {v_count}")
        except Exception as chat_err:
            print("Chat failed:")
            import traceback
            traceback.print_exc()
    else:
        print("WARNING: No transcripts were stored!")

except Exception as e:
    print("E2E recording failed with exception:")
    import traceback
    traceback.print_exc()
finally:
    db.close()
