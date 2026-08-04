import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.database.session import SessionLocal
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus, utc_now

db = SessionLocal()
try:
    running_meetings = db.query(Meeting).filter(Meeting.status == MeetingStatus.RUNNING).all()
    print(f"Found {len(running_meetings)} running meetings in database.")
    for m in running_meetings:
        print(f" -> Setting Meeting ID {m.id} status to COMPLETED.")
        m.status = MeetingStatus.COMPLETED
        m.ended_at = utc_now()
    db.commit()
    print("Database updated successfully.")
finally:
    db.close()
