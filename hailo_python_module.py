#!/usr/bin/env python3
"""
Hailo Python module for GStreamer hailopython element.

This module receives inference results from hailonet and processes them.
"""
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import numpy as np
import sys
import logging

# Add project to path
sys.path.insert(0, "/opt/bee-monitoring/src")

try:
    import hailo
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False
    print("⚠️  hailo module not available")

from ai.hailo_yolo_postprocess import BeeYOLOPostProcessor

# Initialize YOLO post-processor globally
# Using VERY LOW threshold to see if we get any detections at all
yolo_processor = BeeYOLOPostProcessor(
    img_dims=(640, 640),
    nms_iou_thresh=0.45,
    score_threshold=0.01,  # ← MUCH LOWER (was 0.25) to debug NMS issue
    num_classes=3,
    meta_arch="yolo_v5"
)

# Global counters
frame_count = 0
total_detections = 0

def run(video_frame):
    """
    Main processing function called by hailopython element.
    
    This receives the video frame WITH inference results attached.
    
    Args:
        video_frame: hailo.VideoFrame object with inference results
    
    Returns:
        Gst.FlowReturn.OK
    """
    global frame_count, total_detections
    
    frame_count += 1
    
    try:
        if not HAILO_AVAILABLE:
            print(f"Frame {frame_count}: Hailo not available")
            return Gst.FlowReturn.OK
        
        # Get ROI from video frame
        roi = video_frame.roi
        
        if roi is None:
            print(f"Frame {frame_count}: No ROI available")
            return Gst.FlowReturn.OK
        
        # Get PROCESSED detections (already through NMS!)
        detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
        
        # ALSO check raw tensors to see what's happening
        raw_tensors = roi.get_tensors()
        
        # CRITICAL: Check if there are RAW outputs (pre-NMS)
        # The issue is we're only seeing post-NMS tensors which are already filtered
        # Let's look for ALL tensor types
        print(f"\n🔍 DEBUG Frame {frame_count}: Checking all tensor types...")
        print(f"   Total tensors available: {len(raw_tensors)}")
        for i, t in enumerate(raw_tensors):
            print(f"   Tensor {i}: name='{t.name()}', type={type(t)}")
        
        # Only print every 30 frames to reduce spam, or when detections found
        if len(detections) > 0 or frame_count % 30 == 1:
            print(f"\nFrame {frame_count}:")
            
            # Show tensor info with detailed value analysis
            if len(raw_tensors) > 0:
                print(f"  Raw tensors: {len(raw_tensors)}")
                for t in raw_tensors:
                    tensor_name = t.name()
                    tensor_data = roi.get_tensor(tensor_name)
                    tensor_np = np.array(tensor_data, copy=False)
                    print(f"    - {tensor_name}: shape={tensor_np.shape}, dtype={tensor_np.dtype}")
                    
                    # Show non-zero count
                    non_zero = np.count_nonzero(tensor_np)
                    print(f"      Non-zero elements: {non_zero}/{tensor_np.size}")
                    
                    # Analyze values to debug NMS issue
                    if tensor_np.size > 0:
                        print(f"      Value range: [{tensor_np.min():.4f}, {tensor_np.max():.4f}]")
                        print(f"      Mean: {tensor_np.mean():.4f}, Std: {tensor_np.std():.4f}")
                        
                        # For uint8, check if values are quantized
                        if tensor_np.dtype == np.uint8:
                            unique_vals = np.unique(tensor_np)
                            print(f"      Unique values: {len(unique_vals)} (sample: {unique_vals[:10]})")
                        
                        # Check for potential confidence/detection values
                        high_values = (tensor_np > 0.5 * tensor_np.max()).sum() if tensor_np.max() > 0 else 0
                        print(f"      Values > 50% of max: {high_values}")
            
            print(f"  Detections: {len(detections)}")
            
            if len(detections) > 0:
                print("  🎉 DETECTIONS FOUND!")
                for i, detection in enumerate(detections):
                    label = detection.get_label()
                    bbox = detection.get_bbox()
                    confidence = detection.get_confidence()
                    
                    print(f"    {i+1}. {label}: conf={confidence:.3f}, bbox=({bbox.xmin():.3f}, {bbox.ymin():.3f}, {bbox.width():.3f}, {bbox.height():.3f})")
                    
                    total_detections += 1
            
            print(f"  Total detections so far: {total_detections}")
        
    except Exception as e:
        print(f"Frame {frame_count}: Error: {e}")
        import traceback
        traceback.print_exc()
    
    return Gst.FlowReturn.OK


# Module initialization (called when module is loaded)
print("="*70)
print("🐝 Hailo Python Module Loaded")
print("="*70)
print(f"✅ YOLO post-processor initialized")
print(f"✅ Ready to process frames")
print("="*70)
