#!/usr/bin/env python3
"""
Bee Detection using Official Hailo Framework
Based on hailo-rpi5-examples/basic_pipelines/detection.py

This uses the OFFICIAL recommended approach, NOT manual tensor extraction.
"""
from pathlib import Path
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import sys
import numpy as np
import cv2
import hailo

from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad, get_numpy_from_buffer
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.detection.detection_pipeline import GStreamerDetectionApp


class BeeDetectionCallback(app_callback_class):
    """Custom callback class for bee detection"""
    def __init__(self):
        super().__init__()
        self.bee_count = 0
        self.pollen_count = 0
        self.total_bees_seen = 0


def bee_detection_callback(pad, info, user_data):
    """
    Callback function for bee detection using official Hailo framework.
    
    This function receives PROCESSED detections, not raw tensors!
    The framework handles all the complexity:
    - GStreamer pipeline
    - hailofilter configuration
    - Tensor post-processing
    - Detection extraction
    """
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Increment frame counter
    user_data.increment()
    frame_num = user_data.get_count()

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # Get video frame if needed
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    # Get the detections from the buffer (ALREADY PROCESSED!)
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Count bees and pollen
    bee_count = 0
    pollen_count = 0
    
    detection_info = []
    
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        
        # Count by type
        if label == "bee":
            bee_count += 1
        elif label == "pollen":
            pollen_count += 1
        
        # Store detection info
        detection_info.append({
            'label': label,
            'confidence': confidence,
            'bbox': (bbox.xmin(), bbox.ymin(), bbox.width(), bbox.height())
        })
        
        # Draw on frame if available
        if frame is not None:
            x, y, w, h = int(bbox.xmin() * width), int(bbox.ymin() * height), int(bbox.width() * width), int(bbox.height() * height)
            
            # Color based on type
            if label == "bee":
                color = (0, 255, 0)  # Green for bees
            elif label == "pollen":
                color = (0, 255, 255)  # Yellow for pollen
            else:
                color = (255, 0, 0)  # Blue for other
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label_text = f"{label}: {confidence:.2f}"
            cv2.putText(frame, label_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Update counters
    user_data.bee_count = bee_count
    user_data.pollen_count = pollen_count
    user_data.total_bees_seen += bee_count
    
    # Print summary
    print(f"Frame {frame_num}: {bee_count} bees, {pollen_count} pollen (Total bees seen: {user_data.total_bees_seen})")
    
    # Draw summary on frame
    if frame is not None:
        cv2.putText(frame, f"Bees: {bee_count} | Pollen: {pollen_count}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Total: {user_data.total_bees_seen}", 
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Convert to BGR for OpenCV
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)
    
    return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    print("="*70)
    print("🐝 BEE DETECTION - Official Hailo Framework")
    print("="*70)
    print("Using official Hailo approach:")
    print("  - GStreamerDetectionApp framework")
    print("  - Automatic hailofilter configuration")
    print("  - Pre-processed detections (no manual tensor extraction!)")
    print("="*70)
    print()
    
    # Set up environment
    project_root = Path("/tmp/hailo-rpi5-examples")
    env_file = project_root / ".env"
    os.environ["HAILO_ENV_FILE"] = str(env_file)
    
    # Override model path for bee detection
    # The framework will read this from command line args or config
    os.environ["HAILO_MODEL_PATH"] = "/opt/bee-monitoring/src/api/models/bee_test2--640x640_quant_hailort_multidevice_1/bee_test2--640x640_quant_hailort_multidevice_1.hef"
    
    # Create callback instance
    user_data = BeeDetectionCallback()
    
    # Create and run the official detection app
    print("🚀 Starting official GStreamerDetectionApp...")
    app = GStreamerDetectionApp(bee_detection_callback, user_data)
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
