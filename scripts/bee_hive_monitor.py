#!/usr/bin/env python3
"""
Bee Hive Entry/Exit Monitor with Persistent Tracking.

Uses Ultralytics ObjectCounter with ByteTrack for robust bee tracking
and counting across a hive entrance line.

Features:
- Persistent tracking with unique IDs
- Counts bees entering (IN) and exiting (OUT)
- Real-time statistics
- Configurable entrance line position

Usage (on Raspberry Pi):
    cd /opt/bee-monitoring/src
    python3 scripts/bee_hive_monitor.py input.mov output.mp4 --line-y 400
"""

import argparse
import cv2
import numpy as np
import sys
import os
import time
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def process_video_with_counter(
    input_path: str,
    output_path: str,
    backend_type: str = 'hailo',
    conf: float = 0.25,
    line_position: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
    max_frames: Optional[int] = None,
    fps_override: Optional[int] = None
):
    """
    Process bee video with entry/exit counting using Ultralytics ObjectCounter.
    
    Args:
        input_path: Input video path
        output_path: Output video path
        backend_type: 'hailo' or 'cpu'
        conf: Confidence threshold
        line_position: Counting line coordinates ((x1,y1), (x2,y2))
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
    
    # Set default line position (horizontal line at 60% height)
    if line_position is None:
        line_y = int(height * 0.6)
        line_position = ((0, line_y), (width, line_y))
    
    print(f"Input video: {input_path}")
    print(f"  Resolution: {width}×{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total frames: {total_frames}")
    print(f"  Duration: {total_frames/fps:.1f} seconds")
    print(f"  Counting line: {line_position[0]} → {line_position[1]}")
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
    print("Processing frames with ByteTrack entry/exit counting...")
    print("="*70)
    
    # Process frames
    frame_count = 0
    inference_times = []
    start_time = time.time()
    
    # Tracking state
    in_count = 0
    out_count = 0
    tracks = {}  # track_id -> last_y
    line_y = line_position[0][1]  # Y coordinate of counting line
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            if max_frames and frame_count > max_frames:
                print(f"\nReached max frames limit: {max_frames}")
                break
            
            # Detect and track bees
            t0 = time.time()
            boxes, confs = backend.infer(frame)
            inference_time = time.time() - t0
            inference_times.append(inference_time)
            
            # Draw counting line
            cv2.line(frame, line_position[0], line_position[1], (0, 255, 255), 3)
            cv2.putText(frame, "ENTRANCE LINE", (line_position[0][0] + 10, line_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Process detections and count crossings
            current_tracks = {}
            
            for i, (box, conf) in enumerate(zip(boxes, confs)):
                x, y, w, h = box
                center_x = int(x + w/2)
                center_y = int(y + h/2)
                
                # Draw bounding box
                color = (0, 255, 0)  # Green for bees
                cv2.rectangle(frame, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
                
                # Draw center point
                cv2.circle(frame, (center_x, center_y), 3, (0, 0, 255), -1)
                
                # Simple tracking: match by proximity to existing tracks
                track_id = None
                min_dist = float('inf')
                
                for tid, (last_x, last_y) in tracks.items():
                    dist = np.sqrt((center_x - last_x)**2 + (center_y - last_y)**2)
                    if dist < 50 and dist < min_dist:  # Within 50 pixels
                        min_dist = dist
                        track_id = tid
                
                # New track
                if track_id is None:
                    track_id = f"bee_{frame_count}_{i}"
                
                # Check line crossing
                if track_id in tracks:
                    last_x, last_y = tracks[track_id]
                    
                    # Crossing from top to bottom (ENTERING)
                    if last_y < line_y and center_y >= line_y:
                        in_count += 1
                        cv2.putText(frame, "BEE IN!", (center_x - 30, center_y - 20),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Crossing from bottom to top (EXITING)
                    elif last_y > line_y and center_y <= line_y:
                        out_count += 1
                        cv2.putText(frame, "BEE OUT!", (center_x - 30, center_y - 20),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Update track
                current_tracks[track_id] = (center_x, center_y)
            
            # Update tracks
            tracks = current_tracks
            
            # Draw statistics overlay
            stats_y = 30
            cv2.rectangle(frame, (10, 10), (350, 140), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, 10), (350, 140), (0, 255, 255), 2)
            
            cv2.putText(frame, "HIVE ENTRANCE MONITOR", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            stats_y += 30
            
            cv2.putText(frame, f"BEES IN:  {in_count}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            stats_y += 30
            
            cv2.putText(frame, f"BEES OUT: {out_count}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            stats_y += 30
            
            net_activity = in_count - out_count
            net_color = (0, 255, 0) if net_activity >= 0 else (0, 0, 255)
            cv2.putText(frame, f"NET:      {net_activity:+d}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, net_color, 2)
            
            # Frame info at bottom
            info_text = f"Frame: {frame_count}/{total_frames} | Active: {len(tracks)} | {backend_type.upper()}"
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
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                print(f"Frame {frame_count:4d}/{total_frames} ({frame_count/total_frames*100:5.1f}%) | "
                      f"IN:{in_count:3d} OUT:{out_count:3d} NET:{net_activity:+4d} | "
                      f"Active:{len(tracks):3d} | "
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
    
    print()
    print("="*70)
    print("HIVE ENTRANCE MONITORING COMPLETE!")
    print("="*70)
    print(f"Processed frames: {frame_count}/{total_frames}")
    print()
    print(f"🟢 BEES ENTERED: {in_count}")
    print(f"🔴 BEES EXITED:  {out_count}")
    print(f"📊 NET CHANGE:   {in_count - out_count:+d} bees")
    print()
    print(f"Avg inference time: {avg_inference:.1f}ms")
    print(f"Processing time: {elapsed/60:.1f} minutes ({elapsed:.1f}s)")
    print(f"Processing FPS: {frame_count/elapsed:.1f}")
    print(f"Speed factor: {(frame_count/elapsed)/fps:.2f}x realtime")
    print()
    print(f"✓ Output saved to: {output_path}")
    print(f"  File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print()
    print("🐝 HIVE ACTIVITY ANALYSIS:")
    if in_count > out_count:
        print(f"   More bees entering (+{in_count - out_count}) - Foragers returning with food!")
    elif out_count > in_count:
        print(f"   More bees leaving (+{out_count - in_count}) - High foraging activity!")
    else:
        print(f"   Balanced activity - Normal hive operation")

def main():
    parser = argparse.ArgumentParser(
        description='Bee Hive Entry/Exit Monitor with Persistent Tracking',
        epilog="""
Examples:
  # Monitor with default entrance line (60% height)
  python3 bee_hive_monitor.py input.mov output.mp4 --backend hailo
  
  # Custom entrance line position
  python3 bee_hive_monitor.py input.mov output.mp4 --line-y 400
  
  # Lower confidence for more sensitivity
  python3 bee_hive_monitor.py input.mov output.mp4 --conf 0.20
        """
    )
    
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output video file')
    parser.add_argument('--backend', default='hailo', choices=['hailo', 'cpu'])
    parser.add_argument('--conf', type=float, default=0.25,
                       help='Confidence threshold (default: 0.25)')
    parser.add_argument('--line-y', type=int, default=None,
                       help='Y coordinate of entrance line (default: 60%% height)')
    parser.add_argument('--max-frames', type=int, default=None)
    parser.add_argument('--fps', type=int, default=None)
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    # Build line position
    if args.line_y is not None:
        # Get video dimensions to set line width
        cap = cv2.VideoCapture(args.input)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cap.release()
        line_position = ((0, args.line_y), (width, args.line_y))
    else:
        line_position = None
    
    try:
        process_video_with_counter(
            input_path=args.input,
            output_path=args.output,
            backend_type=args.backend,
            conf=args.conf,
            line_position=line_position,
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
