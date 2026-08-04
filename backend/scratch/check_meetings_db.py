import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.database.session import SessionLocal
import app.models
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus

db = SessionLocal()
try:
    meetings = db.query(Meeting).order_by(Meeting.id.desc()).limit(10).all()
    print("=== Last 10 Meetings in DB ===")
    for m in meetings:
        print(f"ID: {m.id}, Title: {m.title}, Status: {m.status}, Started: {m.started_at}, Ended: {m.ended_at}")
finally:
    db.close()
