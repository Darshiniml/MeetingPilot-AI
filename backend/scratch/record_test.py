import sys
import os
sys.path.insert(0, os.path.abspath("."))

import numpy as np
import soundcard as sc

print("=== Recording Diagnostic ===")
try:
    mic = sc.default_microphone()
    print(f"Using Microphone: {mic.name}")
    
    sample_rate = 16000
    duration = 3 # seconds
    num_frames = sample_rate * duration
    
    print(f"Recording for {duration} seconds...")
    with mic.recorder(samplerate=sample_rate) as recorder:
        data = recorder.record(numframes=num_frames)
        
    print(f"Recorded data shape: {data.shape}")
    
    # Calculate audio statistics
    max_val = np.max(np.abs(data))
    rms_val = np.sqrt(np.mean(data**2))
    
    print(f"Maximum amplitude: {max_val:.6f}")
    print(f"Audio RMS: {rms_val:.6f}")
    
    if max_val == 0.0:
        print("\n[ALERT] Audio is ABSOLUTELY SILENT (all zeros)! Python is receiving no sound.")
        print("Possible causes:")
        print("1. Windows microphone privacy settings are blocking Python.")
        print("2. The microphone is muted in OS sound control panel.")
        print("3. The microphone input level/gain is set to 0.")
    elif max_val < 0.0001:
        print("\n[WARNING] Audio amplitude is extremely low. It is practically silent.")
    else:
        print("\n[SUCCESS] Audio recorded successfully with non-zero sound waves!")
        
except Exception as e:
    print(f"Error during recording: {e}")
