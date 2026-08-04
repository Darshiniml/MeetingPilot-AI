import sys
import os
import time
sys.path.insert(0, os.path.abspath("."))

import logging
logging.basicConfig(level=logging.INFO)

from app.audio.audio_service import AudioService
from app.audio.devices import AudioSource

def handler(chunk):
    print(f"--- Chunk handler callback received chunk: {chunk.chunk_index} ---")

service = AudioService(chunk_handler=handler)
print("Starting recording...")
try:
    service.start_recording(AudioSource.MICROPHONE)
    print("Recording started. Sleeping for 15 seconds...")
    for i in range(15):
        time.sleep(1)
        service.raise_if_failed()
        print(f"Seconds passed: {i+1}")
except Exception as e:
    print("Exception during recording run:")
    import traceback
    traceback.print_exc()
finally:
    print("Stopping recording...")
    chunks = service.stop_recording()
    print(f"Recording stopped. Total chunks drained: {len(chunks)}")
    for c in chunks:
        print(f"Chunk index: {c.chunk_index}, path: {c.path}, duration: {c.frame_count / c.sample_rate}s")
