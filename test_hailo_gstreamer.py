#!/usr/bin/env python3
"""Test Hailo GStreamer backend - the CORRECT approach for RPi + Hailo-8L."""
import sys
import logging
import cv2

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

sys.path.insert(0, ".")
from ai.hailo_gstreamer_backend import HailoGStreamerBackend

print("\n" + "="*70)
print("🎯 TESTING HAILO GSTREAMER BACKEND")
print("="*70)
print("Approach: GStreamer integration (RPi + Hailo-8L optimized)")
print("No manual buffer allocation - GStreamer handles everything!")
print("="*70 + "\n")

backend = HailoGStreamerBackend()
if not backend.initialize():
    print("❌ Failed to initialize")
    sys.exit(1)

cap = cv2.VideoCapture("/tmp/your_bee_movie_120fps.mov")
ret, frame = cap.read()
cap.release()

if not ret:
    print("❌ Failed to read video frame")
    sys.exit(1)

print(f"\n🚀 Running inference on frame: {frame.shape}")
print("="*70)

import time
t0 = time.time()
detections = backend.infer_full(frame)
inference_time = (time.time() - t0) * 1000

print("\n" + "="*70)
print(f"🎉 RESULT: {len(detections)} DETECTIONS!")
print(f"⏱️  Inference time: {inference_time:.1f}ms")
print("="*70 + "\n")

if len(detections) > 0:
    print("✅ SUCCESS! Detections found:")
    for i, det in enumerate(detections[:10]):
        print(f"  {i+1:2d}. {det['class_name']:10s} conf={det['confidence']:.3f} bbox={det['bbox']}")
else:
    print("⚠️  No detections (check confidence threshold or model)")

backend.close()
print("\n✓ Test complete!")
