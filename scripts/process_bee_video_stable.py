#!/usr/bin/env python3
"""
Process bee video with STABLE AI detection overlay using tracking.

This version uses simple tracking to smooth detections across frames,
making bounding boxes much more stable and less jittery.

Usage (on Raspberry Pi):
    cd /opt/bee-monitoring/src
    python3 scripts/process_bee_video_stable.py input.mov output.mp4
"""

import argparse
import cv2
import numpy as np
import sys
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Colors for different classes (BGR format)
COLORS = {
    'bee': (0, 255, 0),      # Green
    'pollen': (0, 165, 255),  # Orange
    'default': (255, 0, 0)    # Blue
}

class SimpleTracker:
    """Simple tracker for smoothing detections across frames."""
    
    def __init__(self, max_age=30, iou_threshold=0.3):
        self.tracks = {}  # track_id -> {bbox, class, conf, age, history}
        self.next_id = 0
        self.max_age = max_age
        self.iou_threshold = iou_threshold
    
    def compute_iou(self, box1, box2):
        """Compute IOU between two boxes [x, y, w, h]."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Convert to x1, y1, x2, y2
        box1_x2, box1_y2 = x1 + w1, y1 + h1
        box2_x2, box2_y2 = x2 + w2, y2 + h2
        
        # Intersection
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(box1_x2, box2_x2)
        yi2 = min(box1_y2, box2_y2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        # Union
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        Update tracks with new detections and return smoothed detections.
        
        Args:
            detections: List of detection dicts with 'bbox', 'class_name', 'confidence'
        
        Returns:
            List of smoothed detection dicts with stable 'track_id'
        """
        # Match detections to existing tracks
        matched_tracks = set()
        matched_detections = set()
        updated_detections = []
        
        # Try to match each detection to existing tracks
        for det_idx, detection in enumerate(detections):
            det_box = detection['bbox']
            best_iou = 0
            best_track_id = None
            
            for track_id, track in self.tracks.items():
                if track_id in matched_tracks:
                    continue
                    
                # Only match same class
                if track['class'] != detection['class_name']:
                    continue
                
                iou = self.compute_iou(det_box, track['bbox'])
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_track_id = track_id
            
            if best_track_id is not None:
                # Match found - update track
                matched_tracks.add(best_track_id)
                matched_detections.add(det_idx)
                
                track = self.tracks[best_track_id]
                
                # Smooth bbox using exponential moving average
                alpha = 0.6  # Smoothing factor (lower = more smoothing)
                old_box = track['bbox']
                new_box = det_box
                
                smoothed_box = [
                    int(alpha * new_box[0] + (1 - alpha) * old_box[0]),
                    int(alpha * new_box[1] + (1 - alpha) * old_box[1]),
                    int(alpha * new_box[2] + (1 - alpha) * old_box[2]),
                    int(alpha * new_box[3] + (1 - alpha) * old_box[3])
                ]
                
                # Update track
                track['bbox'] = smoothed_box
                track['confidence'] = detection['confidence']
                track['age'] = 0
                track['history'].append(smoothed_box)
                if len(track['history']) > 5:
                    track['history'].pop(0)
                
                updated_detections.append({
                    'bbox': smoothed_box,
                    'class_name': track['class'],
                    'confidence': track['confidence'],
                    'track_id': best_track_id
                })
        
        # Create new tracks for unmatched detections
        for det_idx, detection in enumerate(detections):
            if det_idx not in matched_detections:
                track_id = self.next_id
                self.next_id += 1
                
                self.tracks[track_id] = {
                    'bbox': detection['bbox'],
                    'class': detection['class_name'],
                    'confidence': detection['confidence'],
                    'age': 0,
                    'history': [detection['bbox']]
                }
                
                updated_detections.append({
                    'bbox': detection['bbox'],
                    'class_name': detection['class_name'],
                    'confidence': detection['confidence'],
                    'track_id': track_id
                })
        
        # Age unmatched tracks and remove old ones
        tracks_to_remove = []
        for track_id, track in self.tracks.items():
            if track_id not in matched_tracks:
                track['age'] += 1
                if track['age'] > self.max_age:
                    tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
        
        return updated_detections

def draw_detections(frame: np.ndarray, detections: List[Dict], show_conf: bool = True, show_id: bool = False) -> np.ndarray:
    """Draw bounding boxes and labels on frame."""
    annotated = frame.copy()
    
    for det in detections:
        bbox = det.get('bbox', [])
        if len(bbox) != 4:
            continue
            
        x, y, w, h = bbox
        class_name = det.get('class_name', 'unknown')
        confidence = det.get('confidence', 0.0)
        track_id = det.get('track_id', -1)
        
        # Get color for this class
        color = COLORS.get(class_name, COLORS['default'])
        
        # Draw bounding box (thicker for more visibility)
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 3)
        
        # Draw label background
        label = f'{class_name}'
        if show_id and track_id >= 0:
            label += f' #{track_id}'
        if show_conf:
            label += f' {confidence:.2f}'
            
        (label_w, label_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        
        cv2.rectangle(
            annotated,
            (x, y - label_h - baseline - 8),
            (x + label_w + 4, y),
            color,
            -1
        )
        
        # Draw label text
        cv2.putText(
            annotated,
            label,
            (x + 2, y - baseline - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
    
    return annotated

def process_video(
    input_path: str,
    output_path: str,
    backend_type: str = 'hailo',
    conf: float = 0.20,  # Lower default for more stable tracking
    max_frames: Optional[int] = None,
    show_conf: bool = True,
    show_id: bool = False,
    fps_override: Optional[int] = None,
    track_max_age: int = 10  # Frames to keep track alive without detection
):
    """Process video file with stable bee detection using tracking."""
    
    # Import backend
    if backend_type == 'hailo':
        from ai.hailo_backend import HailoBackend as Backend
        print("Using Hailo backend (hardware accelerated)")
    else:
        from ai.cpu_backend import CpuBackend as Backend
        print("Using CPU backend (ONNX Runtime)")
    
    # Initialize backend
    print("Initializing backend...")
    backend = Backend()
    if not backend.initialize():
        raise RuntimeError("Failed to initialize backend")
    
    backend.conf = conf
    
    print(f"✓ Backend initialized")
    print(f"  Model: {backend.model_path if hasattr(backend, 'model_path') else backend.hef_path}")
    print(f"  Confidence threshold: {backend.conf}")
    print()
    
    # Initialize tracker
    tracker = SimpleTracker(max_age=track_max_age, iou_threshold=0.3)
    print(f"✓ Tracker initialized (max_age={track_max_age} frames)")
    print()
    
    # Open input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = fps_override if fps_override else cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Input video: {input_path}")
    print(f"  Resolution: {width}×{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total frames: {total_frames}")
    print(f"  Duration: {total_frames/fps:.1f} seconds")
    print()
    
    # Determine output codec
    output_ext = Path(output_path).suffix.lower()
    if output_ext in ['.mov', '.mp4']:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    elif output_ext == '.avi':
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
    else:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    # Create output video writer
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        raise ValueError(f"Could not create output video: {output_path}")
    
    print(f"Output video: {output_path}")
    print(f"  Codec: {output_ext[1:]} / mp4v")
    print(f"  FPS: {fps:.2f}")
    print()
    print("Processing frames with tracking...")
    print("="*60)
    
    # Process frames
    frame_count = 0
    detections_total = 0
    inference_times = []
    start_time = time.time()
    active_tracks_history = []
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            if max_frames and frame_count > max_frames:
                print(f"\nReached max frames limit: {max_frames}")
                break
            
            # Detect bees in frame
            t0 = time.time()
            boxes, confs = backend.infer(frame)
            inference_time = time.time() - t0
            inference_times.append(inference_time)
            
            # Convert to detection dicts
            raw_detections = []
            for box, conf in zip(boxes, confs):
                x, y, w, h = box
                class_id = 1  # bee
                class_name = backend.names.get(class_id, 'bee')
                
                raw_detections.append({
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'confidence': float(conf),
                    'class_id': class_id,
                    'class_name': class_name
                })
            
            # Update tracker for stable detections
            stable_detections = tracker.update(raw_detections)
            detections_total += len(stable_detections)
            active_tracks_history.append(len(tracker.tracks))
            
            # Draw stable detections
            annotated_frame = draw_detections(frame, stable_detections, show_conf, show_id)
            
            # Add frame info overlay
            info_text = f"Frame: {frame_count}/{total_frames} | Bees: {len(stable_detections)} | Tracks: {len(tracker.tracks)} | {backend_type.upper()}"
            cv2.putText(annotated_frame, info_text, (10, height - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(annotated_frame, info_text, (10, height - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
            
            # Write frame
            out.write(annotated_frame)
            
            # Progress update
            if frame_count % 30 == 0 or frame_count == total_frames:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed
                avg_inference = np.mean(inference_times[-30:]) * 1000
                avg_tracks = np.mean(active_tracks_history[-30:])
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                print(f"Frame {frame_count:4d}/{total_frames} ({frame_count/total_frames*100:5.1f}%) | "
                      f"Bees: {len(stable_detections):2d} | "
                      f"Tracks: {len(tracker.tracks):2d} | "
                      f"FPS: {fps_processing:4.1f} | "
                      f"ETA: {eta/60:4.1f}min")
    
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        
    finally:
        cap.release()
        out.release()
    
    # Final stats
    elapsed = time.time() - start_time
    avg_inference = np.mean(inference_times) * 1000 if inference_times else 0
    avg_tracks = np.mean(active_tracks_history) if active_tracks_history else 0
    
    print()
    print("="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Processed frames: {frame_count}/{total_frames}")
    print(f"Total detections: {detections_total}")
    print(f"Avg detections/frame: {detections_total/frame_count:.1f}")
    print(f"Avg active tracks: {avg_tracks:.1f}")
    print(f"Total unique tracks: {tracker.next_id}")
    print(f"Avg inference time: {avg_inference:.1f}ms")
    print(f"Processing time: {elapsed/60:.1f} minutes ({elapsed:.1f}s)")
    print(f"Processing FPS: {frame_count/elapsed:.1f}")
    print(f"Speed factor: {(frame_count/elapsed)/fps:.2f}x realtime")
    print()
    print(f"✓ Output saved to: {output_path}")
    print(f"  File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print()
    print("✓ STABLE TRACKING: Detections are smoothed across frames!")

def main():
    parser = argparse.ArgumentParser(
        description='Process bee video with STABLE AI detection',
        epilog="This version uses tracking to smooth detections and reduce jitter."
    )
    
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output video file')
    parser.add_argument('--backend', default='hailo', choices=['hailo', 'cpu'])
    parser.add_argument('--conf', type=float, default=0.20,
                       help='Confidence threshold (default: 0.20, lower=more stable)')
    parser.add_argument('--max-frames', type=int, default=None)
    parser.add_argument('--no-conf', action='store_true')
    parser.add_argument('--show-id', action='store_true',
                       help='Show track IDs on labels')
    parser.add_argument('--fps', type=int, default=None)
    parser.add_argument('--track-age', type=int, default=10,
                       help='Max frames to keep track alive (default: 10)')
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    try:
        process_video(
            input_path=args.input,
            output_path=args.output,
            backend_type=args.backend,
            conf=args.conf,
            max_frames=args.max_frames,
            show_conf=not args.no_conf,
            show_id=args.show_id,
            fps_override=args.fps,
            track_max_age=args.track_age
        )
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
