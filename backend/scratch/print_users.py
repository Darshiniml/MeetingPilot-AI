from app.database.session import SessionLocal
from app.models.user import User

db = SessionLocal()
try:
    users = db.query(User).all()
    print("=== Users ===")
    for u in users:
        print(f"ID: {u.id}, Name: {u.name}, Email: {u.email}")
finally:
    db.close()
