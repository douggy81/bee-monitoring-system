#!/usr/bin/env python3
"""
Clean Bee Detection Video Processing.

Simple, clean bee detection overlay using Hailo acceleration.
No tracking, no counting - just pure detection visualization.

Usage (on Raspberry Pi):
    cd /opt/bee-monitoring/src
    python3 scripts/process_video_clean.py input.mov output.mp4
"""

import argparse
import cv2
import numpy as np
import sys
import os
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def process_video_clean(
    input_path: str,
    output_path: str,
    backend_type: str = 'hailo',
    conf: float = 0.25,
    max_frames: Optional[int] = None,
    fps_override: Optional[int] = None
):
    """
    Process bee video with clean detection overlay.
    
    Args:
        input_path: Input video path
        output_path: Output video path
        backend_type: 'hailo' or 'cpu'
        conf: Confidence threshold
        max_frames: Max frames to process
        fps_override: Override output FPS
    """
    
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
    print("Processing frames with clean detection overlay...")
    print("="*70)
    
    # Process frames
    frame_count = 0
    inference_times = []
    detection_counts = []
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            if max_frames and frame_count > max_frames:
                print(f"\nReached max frames limit: {max_frames}")
                break
            
            # Detect bees
            t0 = time.time()
            boxes, confs = backend.infer(frame)
            inference_time = time.time() - t0
            inference_times.append(inference_time)
            detection_counts.append(len(boxes))
            
            # Draw clean bounding boxes
            for (x, y, w, h), conf in zip(boxes, confs):
                # Box coordinates
                x1, y1 = int(x), int(y)
                x2, y2 = int(x + w), int(y + h)
                
                # Green boxes for bees
                color = (0, 255, 0)
                
                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw confidence label
                label = f"{conf:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                label_y = max(y1 - 5, label_size[1])
                
                # Label background
                cv2.rectangle(frame, 
                            (x1, label_y - label_size[1] - 4),
                            (x1 + label_size[0] + 4, label_y),
                            color, -1)
                
                # Label text
                cv2.putText(frame, label, (x1 + 2, label_y - 2),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Simple stats overlay (top-left)
            stats_y = 30
            cv2.rectangle(frame, (10, 10), (300, 90), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, 10), (300, 90), (0, 255, 0), 2)
            
            cv2.putText(frame, "HAILO BEE DETECTION", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            stats_y += 30
            
            cv2.putText(frame, f"Bees: {len(boxes)}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            stats_y += 30
            
            # Frame info at bottom
            info_text = f"Frame {frame_count}/{total_frames} | {fps:.0f} FPS | Hailo"
            cv2.putText(frame, info_text, (10, height - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, info_text, (10, height - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
            
            # Write frame
            out.write(frame)
            
            # Progress update
            if frame_count % 30 == 0 or frame_count == total_frames:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed
                avg_inference = np.mean(inference_times[-30:]) * 1000
                avg_detections = np.mean(detection_counts[-30:])
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                
                print(f"Frame {frame_count:4d}/{total_frames} ({frame_count/total_frames*100:5.1f}%) | "
                      f"Bees:{avg_detections:4.1f} | "
                      f"Inf:{avg_inference:4.1f}ms | "
                      f"FPS:{fps_processing:4.1f} | "
                      f"ETA:{eta/60:4.1f}min")
    
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        
    finally:
        cap.release()
        out.release()
    
    # Final stats
    elapsed = time.time() - start_time
    avg_inference = np.mean(inference_times) * 1000 if inference_times else 0
    avg_detections = np.mean(detection_counts) if detection_counts else 0
    
    print()
    print("="*70)
    print("CLEAN BEE DETECTION COMPLETE!")
    print("="*70)
    print(f"Processed frames: {frame_count}/{total_frames}")
    print()
    print(f"📊 Average bees per frame: {avg_detections:.1f}")
    print(f"⚡ Average inference time: {avg_inference:.1f}ms")
    print(f"🎬 Processing time: {elapsed/60:.1f} minutes ({elapsed:.1f}s)")
    print(f"🚀 Processing FPS: {frame_count/elapsed:.1f}")
    print(f"⏱️  Speed factor: {(frame_count/elapsed)/fps:.2f}x realtime")
    print()
    print(f"✓ Output saved to: {output_path}")
    print(f"  File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print()
    print("✨ Clean Hailo detection - no tracking complexity!")

def main():
    parser = argparse.ArgumentParser(
        description='Clean Bee Detection Video Processing',
        epilog="""
Simple, clean bee detection overlay using Hailo acceleration.

Examples:
  # Basic usage
  python3 process_video_clean.py input.mov output.mp4
  
  # Custom confidence
  python3 process_video_clean.py input.mov output.mp4 --conf 0.3
  
  # Process 120 FPS interpolated video
  python3 process_video_clean.py input_120fps.mov output.mp4
        """
    )
    
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output video file')
    parser.add_argument('--backend', default='hailo', choices=['hailo', 'cpu'])
    parser.add_argument('--conf', type=float, default=0.25,
                       help='Detection confidence threshold (default: 0.25)')
    parser.add_argument('--max-frames', type=int, default=None)
    parser.add_argument('--fps', type=int, default=None)
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    try:
        process_video_clean(
            input_path=args.input,
            output_path=args.output,
            backend_type=args.backend,
            conf=args.conf,
            max_frames=args.max_frames,
            fps_override=args.fps
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
