#!/usr/bin/env python3
"""
Process bee video with AI detection overlay (local/direct backend access).

This version runs directly on the Pi and uses the backend without HTTP overhead.
Much faster than the API version!

Usage (on Raspberry Pi):
    cd /opt/bee-monitoring/src
    python3 scripts/process_bee_video_local.py /path/to/input.mov /path/to/output.mp4
"""

import argparse
import cv2
import numpy as np
import sys
import os
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path to import backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Colors for different classes (BGR format)
COLORS = {
    'bee': (0, 255, 0),      # Green
    'pollen': (0, 165, 255),  # Orange
    'default': (255, 0, 0)    # Blue
}

def draw_detections(frame: np.ndarray, detections: list, show_conf: bool = True) -> np.ndarray:
    """Draw bounding boxes and labels on frame."""
    annotated = frame.copy()
    
    for det in detections:
        bbox = det.get('bbox', [])
        if len(bbox) != 4:
            continue
            
        x, y, w, h = bbox
        class_name = det.get('class_name', 'unknown')
        confidence = det.get('confidence', 0.0)
        
        # Get color for this class
        color = COLORS.get(class_name, COLORS['default'])
        
        # Draw bounding box
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        
        # Draw label background
        label = f'{class_name}'
        if show_conf:
            label += f' {confidence:.2f}'
            
        (label_w, label_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        
        cv2.rectangle(
            annotated,
            (x, y - label_h - baseline - 5),
            (x + label_w, y),
            color,
            -1
        )
        
        # Draw label text
        cv2.putText(
            annotated,
            label,
            (x, y - baseline - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
    
    return annotated

def process_video(
    input_path: str,
    output_path: str,
    backend_type: str = 'hailo',
    conf: float = 0.25,
    max_frames: Optional[int] = None,
    show_conf: bool = True,
    fps_override: Optional[int] = None
):
    """Process video file with bee detection using local backend."""
    
    # Import backend
    if backend_type == 'hailo':
        from ai.hailo_backend import HailoBackend as Backend
        print("Using Hailo backend (hardware accelerated)")
    else:
        from ai.cpu_backend import CpuBackend as Backend
        print("Using CPU backend (ONNX Runtime)")
    
    # Initialize backend
    print("Initializing backend...")
    backend = Backend(conf_threshold=conf)
    if not backend.initialize():
        raise RuntimeError("Failed to initialize backend")
    print(f"✓ Backend initialized (model: {backend.model_path if hasattr(backend, 'model_path') else backend.hef_path})")
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
    
    # Determine output codec and extension
    output_ext = Path(output_path).suffix.lower()
    if output_ext == '.mov':
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    elif output_ext == '.mp4':
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    elif output_ext == '.avi':
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
    else:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        print(f"Warning: Unknown extension {output_ext}, using mp4v codec")
    
    # Create output video writer
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        raise ValueError(f"Could not create output video: {output_path}")
    
    print(f"Output video: {output_path}")
    print(f"  Codec: {output_ext[1:]} / mp4v")
    print(f"  FPS: {fps:.2f}")
    print()
    print("Processing frames...")
    print("="*60)
    
    # Process frames
    frame_count = 0
    detections_total = 0
    inference_times = []
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Check max frames limit
            if max_frames and frame_count > max_frames:
                print(f"\nReached max frames limit: {max_frames}")
                break
            
            # Detect bees in frame
            t0 = time.time()
            boxes, confs = backend.infer(frame)
            inference_time = time.time() - t0
            inference_times.append(inference_time)
            
            # Convert backend output to detection dicts
            detections = []
            for i, (box, conf) in enumerate(zip(boxes, confs)):
                x, y, w, h = box
                # Get class name from backend
                class_id = 1  # Default to bee
                class_name = backend.names.get(class_id, 'bee')
                
                detections.append({
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'confidence': float(conf),
                    'class_id': class_id,
                    'class_name': class_name
                })
            
            detections_total += len(detections)
            
            # Draw detections
            annotated_frame = draw_detections(frame, detections, show_conf)
            
            # Add frame info overlay
            info_text = f"Frame: {frame_count}/{total_frames} | Bees: {len(detections)} | {backend_type.upper()} | {inference_time*1000:.0f}ms"
            cv2.putText(
                annotated_frame,
                info_text,
                (10, height - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            cv2.putText(
                annotated_frame,
                info_text,
                (10, height - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                1
            )
            
            # Write frame
            out.write(annotated_frame)
            
            # Progress update
            if frame_count % 30 == 0 or frame_count == total_frames:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed
                avg_inference = np.mean(inference_times[-30:]) * 1000
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                print(f"Frame {frame_count:4d}/{total_frames} ({frame_count/total_frames*100:5.1f}%) | "
                      f"Bees: {len(detections):2d} | "
                      f"Inf: {avg_inference:4.0f}ms | "
                      f"FPS: {fps_processing:4.1f} | "
                      f"ETA: {eta/60:4.1f}min")
    
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        
    finally:
        # Cleanup
        cap.release()
        out.release()
    
    # Final stats
    elapsed = time.time() - start_time
    avg_inference = np.mean(inference_times) * 1000 if inference_times else 0
    
    print()
    print("="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Processed frames: {frame_count}/{total_frames}")
    print(f"Total bees detected: {detections_total}")
    print(f"Avg bees/frame: {detections_total/frame_count:.1f}")
    print(f"Avg inference time: {avg_inference:.1f}ms")
    print(f"Processing time: {elapsed/60:.1f} minutes ({elapsed:.1f}s)")
    print(f"Processing FPS: {frame_count/elapsed:.1f}")
    print(f"Speed factor: {(frame_count/elapsed)/fps:.2f}x realtime")
    print()
    print(f"✓ Output saved to: {output_path}")
    print(f"  File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")

def main():
    parser = argparse.ArgumentParser(
        description='Process bee video with AI detection (local backend)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process with Hailo backend (fastest, runs on Pi)
  python3 process_bee_video_local.py input.mov output.mp4
  
  # Process with CPU backend
  python3 process_bee_video_local.py input.mov output.mp4 --backend cpu
  
  # Lower confidence threshold
  python3 process_bee_video_local.py input.mov output.mp4 --conf 0.15
  
  # Process first 300 frames only (for testing)
  python3 process_bee_video_local.py input.mov output.mp4 --max-frames 300
  
  # Hide confidence scores
  python3 process_bee_video_local.py input.mov output.mp4 --no-conf

Note: This script must run on the Raspberry Pi to access the backends directly!
      For remote processing, use process_bee_video.py instead.
        """
    )
    
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('output', help='Output video file path')
    parser.add_argument('--backend', default='hailo', choices=['hailo', 'cpu'],
                        help='Detection backend (default: hailo)')
    parser.add_argument('--conf', type=float, default=0.25,
                        help='Confidence threshold (default: 0.25)')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Maximum frames to process (default: all)')
    parser.add_argument('--no-conf', action='store_true',
                        help='Hide confidence scores on labels')
    parser.add_argument('--fps', type=int, default=None,
                        help='Override output FPS (default: use input FPS)')
    
    args = parser.parse_args()
    
    # Check input file exists
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    # Process video
    try:
        process_video(
            input_path=args.input,
            output_path=args.output,
            backend_type=args.backend,
            conf=args.conf,
            max_frames=args.max_frames,
            show_conf=not args.no_conf,
            fps_override=args.fps
        )
        return 0
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
