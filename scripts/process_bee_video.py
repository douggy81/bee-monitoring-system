#!/usr/bin/env python3
"""
Process bee video with AI detection overlay.

Reads a video file, runs Hailo detection on each frame, and outputs
an annotated video with bounding boxes.

Usage:
    python process_bee_video.py input.mov output.mp4
    python process_bee_video.py input.mov output.mp4 --backend hailo --conf 0.25
"""

import argparse
import cv2
import numpy as np
import requests
import base64
import json
import time
from pathlib import Path
from typing import Optional, Tuple

# Colors for different classes (BGR format)
COLORS = {
    'bee': (0, 255, 0),      # Green
    'pollen': (0, 165, 255),  # Orange
    'default': (255, 0, 0)    # Blue
}

def detect_frame(frame: np.ndarray, api_url: str, backend: str, conf: float) -> Tuple[list, Optional[np.ndarray]]:
    """
    Send frame to API for detection.
    
    Returns: (detections, annotated_frame)
    """
    # Encode frame as JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    # Prepare request
    payload = {
        'image': f'data:image/jpeg;base64,{img_base64}',
        'backend': backend,
        'conf': conf,
        'annotate': False  # We'll draw boxes ourselves for consistency
    }
    
    try:
        response = requests.post(
            f'{api_url}/api/bee/ai/detect',
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result.get('detections', []), None
        
        return [], None
        
    except Exception as e:
        print(f"Error detecting frame: {e}")
        return [], None

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
    api_url: str = 'http://localhost:5000',
    backend: str = 'hailo',
    conf: float = 0.25,
    max_frames: Optional[int] = None,
    show_conf: bool = True,
    fps_override: Optional[int] = None
):
    """
    Process video file with bee detection.
    
    Args:
        input_path: Input video file path
        output_path: Output video file path
        api_url: API base URL
        backend: Detection backend (hailo/cpu)
        conf: Confidence threshold
        max_frames: Max frames to process (None = all)
        show_conf: Show confidence scores on labels
        fps_override: Override output FPS (None = use input FPS)
    """
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
    print(f"  Backend: {backend}")
    print(f"  Confidence threshold: {conf}")
    print()
    
    # Determine output codec and extension
    output_ext = Path(output_path).suffix.lower()
    if output_ext == '.mov':
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # or 'avc1' for H.264
    elif output_ext == '.mp4':
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # or 'avc1' for H.264
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
    print(f"  Codec: {output_ext} / {'mp4v' if output_ext in ['.mov', '.mp4'] else 'XVID'}")
    print()
    
    # Process frames
    frame_count = 0
    detections_total = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Check max frames limit
            if max_frames and frame_count > max_frames:
                print(f"Reached max frames limit: {max_frames}")
                break
            
            # Detect bees in frame
            detections, _ = detect_frame(frame, api_url, backend, conf)
            detections_total += len(detections)
            
            # Draw detections
            annotated_frame = draw_detections(frame, detections, show_conf)
            
            # Add frame info overlay
            info_text = f"Frame: {frame_count}/{total_frames if not max_frames else max_frames} | Detections: {len(detections)} | Backend: {backend}"
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
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                print(f"Progress: {frame_count}/{total_frames} ({frame_count/total_frames*100:.1f}%) | "
                      f"Detections: {len(detections)} | "
                      f"FPS: {fps_processing:.1f} | "
                      f"ETA: {eta/60:.1f}min")
    
    finally:
        # Cleanup
        cap.release()
        out.release()
    
    # Final stats
    elapsed = time.time() - start_time
    print()
    print("="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Processed frames: {frame_count}")
    print(f"Total detections: {detections_total}")
    print(f"Avg detections/frame: {detections_total/frame_count:.1f}")
    print(f"Processing time: {elapsed/60:.1f} minutes")
    print(f"Processing FPS: {frame_count/elapsed:.1f}")
    print(f"Output saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description='Process bee video with AI detection overlay',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process with Hailo backend (fastest)
  python process_bee_video.py input.mov output.mp4 --backend hailo
  
  # Process with CPU backend
  python process_bee_video.py input.mov output.mp4 --backend cpu
  
  # Lower confidence threshold to detect more bees
  python process_bee_video.py input.mov output.mp4 --conf 0.15
  
  # Process first 300 frames only (for testing)
  python process_bee_video.py input.mov output.mp4 --max-frames 300
  
  # Custom API URL (if not running on localhost)
  python process_bee_video.py input.mov output.mp4 --api-url http://192.168.68.66
        """
    )
    
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('output', help='Output video file path')
    parser.add_argument('--api-url', default='http://localhost:5000',
                        help='API base URL (default: http://localhost:5000)')
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
            api_url=args.api_url,
            backend=args.backend,
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
