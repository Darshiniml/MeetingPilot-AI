import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.database.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
try:
    print("Testing get_password_hash...")
    h = get_password_hash("testpassword123")
    print("Hash success:", h)
    
    print("Creating User object...")
    user = User(
        name="Test User",
        email="testuser@example.com",
        password_hash=h
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print("User created successfully! ID:", user.id)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
