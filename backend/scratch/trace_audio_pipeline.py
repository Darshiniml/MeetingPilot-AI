"""Capture and inspect audio using the exact settings used by AudioService.

Run from the repository root with the Python environment that has SoundCard installed.
"""

from __future__ import annotations

import os
import wave
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import soundcard as sc

SAMPLE_RATE = 16_000
CHANNELS = 1
DURATION_SECONDS = 5
FRAME_COUNT = SAMPLE_RATE * DURATION_SECONDS
OUTPUT_DIRECTORY = Path(__file__).parent


def write_wav(path: Path, samples: np.ndarray) -> None:
    """Write SoundCard float PCM as the int16 PCM WAV used by AudioService."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(pcm.shape[1])
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())


def inspect_wav(path: Path) -> tuple[float, float, np.ndarray]:
    """Reopen the persisted raw WAV and calculate its actual PCM metrics."""
    with wave.open(str(path), "rb") as wav_file:
        pcm = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype="<i2")
        channels = wav_file.getnchannels()
    normalized = pcm.astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(np.square(normalized))))
    maximum = float(np.max(np.abs(normalized)))
    print(f"WAV: {path.resolve()}")
    print(f"Audio RMS: {rms:.6f}")
    print(f"Maximum amplitude: {maximum:.6f}")
    print("First 100 PCM samples (int16):")
    print(pcm[:100].tolist())
    return rms, maximum, pcm.reshape(-1, channels)


def plot_waveform(path: Path, samples: np.ndarray, device_name: str) -> Path:
    plot_path = path.with_suffix(".png")
    times = np.arange(samples.shape[0]) / SAMPLE_RATE
    plt.figure(figsize=(12, 4))
    plt.plot(times, samples[:, 0] / 32768.0, linewidth=0.5, color="royalblue")
    plt.title(f"Waveform — {device_name}")
    plt.xlabel("Seconds")
    plt.ylabel("Amplitude")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Waveform: {plot_path.resolve()}")
    return plot_path


def capture(device: object, suffix: str) -> tuple[float, float, Path]:
    name = str(getattr(device, "name"))
    output = OUTPUT_DIRECTORY / f"diagnostic_{suffix}_5s.wav"
    print(f"\nCapturing {DURATION_SECONDS}s from: {name}")
    # These are AudioCaptureConfig's production values, rather than SoundCard defaults.
    with device.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS, blocksize=1600) as recorder:
        samples = recorder.record(numframes=FRAME_COUNT)
    write_wav(output, samples)
    rms, maximum, persisted_samples = inspect_wav(output)
    plot_waveform(output, persisted_samples, name)
    return rms, maximum, output


print("=== Audio pipeline ===")
print("Library: soundcard (WASAPI on Windows)")
print(f"SoundCard module: {sc.__file__}")
print(f"AudioService configuration: sample rate={SAMPLE_RATE} Hz, channels={CHANNELS}, block size=1600")

default_microphone = sc.default_microphone()
microphones = sc.all_microphones(include_loopback=False)
print("\n=== Selected device (AudioService without an identifier) ===")
print(f"Name: {default_microphone.name}")
print(f"ID: {default_microphone.id}")
print(f"Endpoint channels: {default_microphone.channels}")
print(f"Requested sample rate: {SAMPLE_RATE} Hz")
print(f"Requested channels: {CHANNELS}")

print("\n=== All recording devices ===")
for index, microphone in enumerate(microphones):
    print(
        f"[{index}] name={microphone.name}; id={microphone.id}; "
        f"endpoint_channels={microphone.channels}; loopback={microphone.isloopback}"
    )

print("\n=== Browser comparison ===")
print("AudioService selection:", default_microphone.name)
print("Physical recording endpoints found:", len(microphones))
print(
    "Chrome/Edge can either use Windows Default (which resolves to the selected device above) "
    "or a per-site device chosen in browser settings; this process cannot read the browser's active WebRTC choice."
)

results: list[tuple[str, float, float, Path]] = []
for index, microphone in enumerate(microphones):
    rms, maximum, wav_path = capture(microphone, f"mic_{index}")
    results.append((str(microphone.name), rms, maximum, wav_path))

print("\n=== Verdict ===")
for name, rms, maximum, wav_path in results:
    state = "DIGITAL SILENCE" if maximum == 0.0 else "signal detected"
    print(f"{name}: {state}; rms={rms:.6f}; max={maximum:.6f}; wav={wav_path.resolve()}")
if results and all(maximum == 0.0 for _, _, maximum, _ in results):
    print(
        "Every physical endpoint returned all-zero PCM through the same WASAPI stream AudioService uses. "
        "There is no alternate microphone endpoint for AudioService to select."
    )
