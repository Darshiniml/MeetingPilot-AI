import sys
import os
sys.path.insert(0, os.path.abspath("."))

import subprocess
import time
import json
from urllib.request import Request, urlopen
from app.core.security import create_access_token

log_file_path = "scratch/uvicorn_test.log"

print("=== Starting Test Uvicorn Server on Port 8001 ===")
# Clear old log file
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# Launch uvicorn
proc = subprocess.Popen(
    [
        "C:\\Users\\Varshini\\OneDrive\\Desktop\\MeetingPilot-AI\\.venv\\Scripts\\python.exe",
        "-m", "uvicorn", "app.main:create_app",
        "--host", "127.0.0.1",
        "--port", "8001",
        "--factory"
    ],
    stdout=open(log_file_path, "w"),
    stderr=subprocess.STDOUT,
    env={**os.environ, "PYTHONUNBUFFERED": "1"},
    text=True
)

try:
    print("Waiting 20 seconds for server to start (loading Whisper model)...")
    time.sleep(20)
    
    # Generate token for User 1
    token = create_access_token(subject=1)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n1. Posting to /meeting/start ...")
    req_start = Request(
        "http://127.0.0.1:8001/meeting/start",
        headers=headers,
        method="POST"
    )
    with urlopen(req_start, timeout=10) as resp:
        print("Response:", json.loads(resp.read().decode()))
        
    print("\nRecording for 25 seconds...")
    for i in range(25):
        time.sleep(1)
        if (i+1) % 5 == 0:
            print(f" -> Recorded {i+1}s / 25s")
            
    print("\n2. Posting to /meeting/stop ...")
    req_stop = Request(
        "http://127.0.0.1:8001/meeting/stop",
        headers=headers,
        method="POST"
    )
    with urlopen(req_stop, timeout=10) as resp:
        print("Response:", json.loads(resp.read().decode()))
        
    print("\nWaiting 3 seconds for async pipeline tasks to finish...")
    time.sleep(3)

finally:
    print("\nTerminating uvicorn server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    print("Server terminated.")

# Print logs
print("\n=== Uvicorn Server Logs ===")
if os.path.exists(log_file_path):
    with open(log_file_path, "r") as f:
        print(f.read())
else:
    print("No log file found.")
