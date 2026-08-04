import soundcard as sc

print("--- Microphones ---")
for i, m in enumerate(sc.all_microphones()):
    print(f"Index {i}: {m.name} (Loopback: {getattr(m, 'isloopback', False)})")
    
print("\n--- Default Microphone ---")
try:
    print(sc.default_microphone().name)
except Exception as e:
    print("Error getting default microphone:", e)
    
print("\n--- Speakers ---")
for i, s in enumerate(sc.all_speakers()):
    print(f"Index {i}: {s.name}")
    
print("\n--- Default Speaker ---")
try:
    print(sc.default_speaker().name)
except Exception as e:
    print("Error getting default speaker:", e)
