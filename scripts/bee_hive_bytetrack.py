#!/usr/bin/env python3
"""
Bee Hive Entry/Exit Monitor with Professional ByteTrack Tracking.

Uses Supervision library's ByteTrack implementation for robust, glitch-free
bee tracking and line crossing detection.

Features:
- Professional ByteTrack algorithm (robust to occlusion)
- Accurate entry/exit counting with LineZone
- Persistent track IDs across frames
- No jittery tracking glitches
- Real-time statistics

Usage (on Raspberry Pi):
    cd /opt/bee-monitoring/src
    python3 scripts/bee_hive_bytetrack.py input.mov output.mp4 --line-y 400
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

try:
    import supervision as sv
    print("✓ Supervision library loaded (ByteTrack available)")
except ImportError:
    print("ERROR: supervision library not installed")
    print("Install with: pip install supervision")
    sys.exit(1)

def process_video_with_bytetrack(
    input_path: str,
    output_path: str,
    backend_type: str = 'hailo',
    conf: float = 0.15,  # Lower for fast-moving bees
    line_y: Optional[int] = None,
    max_frames: Optional[int] = None,
    fps_override: Optional[int] = None,
    track_thresh: float = 0.15,  # Lower = easier to track
    track_buffer: int = 60,  # 1 second at 60fps
    match_thresh: float = 0.6  # Lower = more lenient matching
):
    """
    Process bee video with ByteTrack tracking and entry/exit counting.
    
    Args:
        input_path: Input video path
        output_path: Output video path
        backend_type: 'hailo' or 'cpu'
        conf: Confidence threshold for detection
        line_y: Y coordinate of entrance line (None = 60% height)
        max_frames: Max frames to process
        fps_override: Override output FPS
        track_thresh: Tracking confidence threshold
        track_buffer: Frames to keep lost tracks
        match_thresh: IoU threshold for matching
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
    if line_y is None:
        line_y = int(height * 0.6)
    
    print(f"Input video: {input_path}")
    print(f"  Resolution: {width}×{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total frames: {total_frames}")
    print(f"  Duration: {total_frames/fps:.1f} seconds")
    print()
    
    # Initialize ByteTrack tracker with aggressive parameters for fast-moving bees
    byte_tracker = sv.ByteTrack(
        track_activation_threshold=track_thresh,
        lost_track_buffer=track_buffer,
        minimum_matching_threshold=match_thresh,
        minimum_consecutive_frames=1,  # Start tracking immediately
        frame_rate=int(fps)
    )
    print(f"✓ ByteTrack initialized")
    print(f"  Track threshold: {track_thresh}")
    print(f"  Track buffer: {track_buffer} frames")
    print(f"  Match threshold: {match_thresh}")
    print()
    
    # Initialize LineZone for counting
    line_start = sv.Point(x=0, y=line_y)
    line_end = sv.Point(x=width, y=line_y)
    line_zone = sv.LineZone(start=line_start, end=line_end)
    
    print(f"✓ LineZone initialized")
    print(f"  Entrance line: (0, {line_y}) → ({width}, {line_y})")
    print()
    
    # Annotators
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=2)
    trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=30)
    
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
    print("Processing frames with ByteTrack...")
    print("="*70)
    
    # Process frames
    frame_count = 0
    inference_times = []
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
            
            # Detect bees with Hailo
            t0 = time.time()
            boxes, confs = backend.infer(frame)
            inference_time = time.time() - t0
            inference_times.append(inference_time)
            
            # Convert to supervision Detections format
            if len(boxes) > 0:
                # Convert [x, y, w, h] to [x1, y1, x2, y2]
                xyxy = np.array([[x, y, x+w, y+h] for x, y, w, h in boxes])
                class_ids = np.ones(len(boxes), dtype=int)  # All bees (class 1)
                
                detections = sv.Detections(
                    xyxy=xyxy,
                    confidence=np.array(confs),
                    class_id=class_ids
                )
            else:
                detections = sv.Detections.empty()
            
            # Update ByteTrack tracker
            detections = byte_tracker.update_with_detections(detections)
            
            # Update line zone (counts crossings)
            line_zone.trigger(detections)
            
            # Annotate frame
            # 1. Draw traces (bee paths)
            frame = trace_annotator.annotate(scene=frame, detections=detections)
            
            # 2. Draw bounding boxes
            frame = box_annotator.annotate(scene=frame, detections=detections)
            
            # 3. Draw labels with track IDs
            labels = [
                f"#{tracker_id} {confidence:0.2f}"
                for tracker_id, confidence in zip(detections.tracker_id, detections.confidence)
            ]
            frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
            
            # 4. Draw line zone
            line_zone_annotator = sv.LineZoneAnnotator(thickness=3, text_thickness=2, text_scale=0.7)
            frame = line_zone_annotator.annotate(frame, line_counter=line_zone)
            
            # 5. Draw statistics panel
            in_count = line_zone.in_count
            out_count = line_zone.out_count
            net_count = in_count - out_count
            
            stats_y = 30
            cv2.rectangle(frame, (10, 10), (400, 160), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, 10), (400, 160), (0, 255, 255), 2)
            
            cv2.putText(frame, "BYTETRACK HIVE MONITOR", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            stats_y += 30
            
            cv2.putText(frame, f"BEES IN:  {in_count}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            stats_y += 30
            
            cv2.putText(frame, f"BEES OUT: {out_count}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            stats_y += 30
            
            net_color = (0, 255, 0) if net_count >= 0 else (0, 0, 255)
            cv2.putText(frame, f"NET:      {net_count:+d}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, net_color, 2)
            stats_y += 30
            
            cv2.putText(frame, f"TRACKS:   {len(detections)}", (20, stats_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Frame info at bottom
            info_text = f"Frame: {frame_count}/{total_frames} | ByteTrack | {backend_type.upper()}"
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
                      f"IN:{in_count:3d} OUT:{out_count:3d} NET:{net_count:+4d} | "
                      f"Tracks:{len(detections):3d} | "
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
    
    in_count = line_zone.in_count
    out_count = line_zone.out_count
    net_count = in_count - out_count
    
    print()
    print("="*70)
    print("BYTETRACK HIVE ENTRANCE MONITORING COMPLETE!")
    print("="*70)
    print(f"Processed frames: {frame_count}/{total_frames}")
    print()
    print(f"🟢 BEES ENTERED: {in_count}")
    print(f"🔴 BEES EXITED:  {out_count}")
    print(f"📊 NET CHANGE:   {net_count:+d} bees")
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
    print()
    print("✓ ByteTrack: Professional tracking with no glitches!")

def main():
    parser = argparse.ArgumentParser(
        description='Bee Hive Entry/Exit Monitor with ByteTrack',
        epilog="""
ByteTrack Features:
  - Robust tracking with Kalman filtering
  - Re-identification for occluded bees
  - Multi-stage association
  - Professional quality, no glitches!

Examples:
  # Default settings
  python3 bee_hive_bytetrack.py input.mov output.mp4
  
  # Custom entrance line
  python3 bee_hive_bytetrack.py input.mov output.mp4 --line-y 400
  
  # Fine-tune tracking
  python3 bee_hive_bytetrack.py input.mov output.mp4 --track-thresh 0.3 --track-buffer 40
        """
    )
    
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output video file')
    parser.add_argument('--backend', default='hailo', choices=['hailo', 'cpu'])
    parser.add_argument('--conf', type=float, default=0.15,
                       help='Detection confidence threshold (default: 0.15 - optimized for fast bees)')
    parser.add_argument('--line-y', type=int, default=None,
                       help='Y coordinate of entrance line (default: 60%% height)')
    parser.add_argument('--track-thresh', type=float, default=0.15,
                       help='Track activation threshold (default: 0.15 - lower for fast movement)')
    parser.add_argument('--track-buffer', type=int, default=60,
                       help='Frames to keep lost tracks (default: 60 = 1s @ 60fps)')
    parser.add_argument('--match-thresh', type=float, default=0.6,
                       help='IoU threshold for matching (default: 0.6 - more lenient)')
    parser.add_argument('--max-frames', type=int, default=None)
    parser.add_argument('--fps', type=int, default=None)
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    try:
        process_video_with_bytetrack(
            input_path=args.input,
            output_path=args.output,
            backend_type=args.backend,
            conf=args.conf,
            line_y=args.line_y,
            max_frames=args.max_frames,
            fps_override=args.fps,
            track_thresh=args.track_thresh,
            track_buffer=args.track_buffer,
            match_thresh=args.match_thresh
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
