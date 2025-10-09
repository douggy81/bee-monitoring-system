#!/usr/bin/env python3
"""Test fresh HEF model with Hailo backend."""
import sys
import logging
import cv2

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

sys.path.insert(0, ".")
from ai.hailo_backend import HailoBackend

print("\n🚀 Testing FRESH HEF (compiled today) with Hailo backend...")
print("="*70)

backend = HailoBackend()
if not backend.initialize():
    print("❌ Failed to initialize Hailo backend")
    sys.exit(1)

cap = cv2.VideoCapture("/tmp/your_bee_movie_120fps.mov")
ret, frame = cap.read()
cap.release()

if not ret:
    print("❌ Failed to read video frame")
    sys.exit(1)

print(f"\n📹 Testing on frame: {frame.shape}")
print("="*70)

detections = backend.infer_full(frame)

print("\n" + "="*70)
print(f"🎉 RESULT: {len(detections)} DETECTIONS!")
print("="*70 + "\n")

if len(detections) > 0:
    print("First 10 detections:")
    for i, det in enumerate(detections[:10]):
        cls_name = det.get('class_name', 'unknown')
        conf = det.get('confidence', 0)
        bbox = det.get('bbox', [])
        print(f"  {i+1:2d}. {cls_name:10s} conf={conf:.3f} bbox={bbox}")
else:
    print("⚠️  No detections found")

backend.close()
