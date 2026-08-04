import shutil
import os

src_img = "scratch/waveform_trace.png"
dst_dir = r"C:\Users\Varshini\.gemini\antigravity\brain\72befde9-cc90-4e79-ab5c-4f6fbf223ff1"
dst_img = os.path.join(dst_dir, "waveform_trace.png")

if os.path.exists(src_img):
    shutil.copy(src_img, dst_img)
    print(f"Copied waveform image to artifacts: {dst_img}")
else:
    print("Source image not found.")
