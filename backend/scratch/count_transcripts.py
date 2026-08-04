import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.database.session import SessionLocal
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.vector_embedding import VectorEmbedding
from app.models.action_item import ActionItem
from app.models.summary import Summary

db = SessionLocal()
try:
    print("--- Database Count ---")
    print("Users:", db.query(User).count())
    print("Meetings:", db.query(Meeting).count())
    print("Transcripts:", db.query(Transcript).count())
    print("VectorEmbeddings:", db.query(VectorEmbedding).count())
    print("ActionItems:", db.query(ActionItem).count())
    print("Summaries:", db.query(Summary).count())
    
    print("\n--- Last 10 Meetings ---")
    for m in db.query(Meeting).order_by(Meeting.id.desc()).limit(10):
        t_count = db.query(Transcript).filter(Transcript.meeting_id == m.id).count()
        print(f"ID: {m.id}, Title: {m.title}, Status: {m.status}, Started: {m.started_at}, Ended: {m.ended_at}, Transcripts: {t_count}")
        
    print("\n--- Last 5 Transcripts ---")
    for t in db.query(Transcript).order_by(Transcript.id.desc()).limit(5):
        print(f"ID: {t.id}, Meeting ID: {t.meeting_id}, Chunk: {t.chunk_index}, Seg: {t.segment_index}, Text: {t.text[:50]}")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
