import os
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path("c:/Users/Varshini/OneDrive/Desktop/MeetingPilot-AI")
print("Searching for modified log/txt files in project root...")

cutoff = datetime.now() - timedelta(hours=10)

for p in project_root.rglob("*"):
    try:
        if p.is_file() and p.suffix in (".log", ".txt", ".jsonl"):
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if mtime > cutoff:
                print(f"File: {p} (mtime: {mtime})")
    except Exception:
        pass
