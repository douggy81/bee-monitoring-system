# -*- coding: utf-8 -*-
"""
🐝 Bee Monitoring - Optimized GPU Processing with Behaviors
Fixed version with FPS-aware classification and fast processing
"""

# ============================================
# CELL 1: Install Packages
# ============================================
!pip install -q ultralytics supervision opencv-python-headless

# ============================================
# CELL 2: Check GPU
# ============================================
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
else:
    print("⚠️ No GPU - will use CPU (slower)")

# ============================================
# CELL 3: Import Libraries
# ============================================
import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO
import time
import os
import subprocess
from IPython.display import Video, display

print("✅ All imports successful")

# ============================================
# CELL 4: Mount Drive & Load Model
# ============================================
from google.colab import drive
drive.mount('/content/drive')

DRIVE_FOLDER = '/content/drive/MyDrive/bee-monitoring'
model_path = f'{DRIVE_FOLDER}/yolo11m_bee_best.onnx'

# Load model
if os.path.exists(model_path):
    model = YOLO(model_path, task='detect')
    print(f"✅ YOLO11m model loaded on {'cuda:0' if torch.cuda.is_available() else 'cpu'}")
else:
    print(f"❌ Model not found at: {model_path}")

# Load logo
logo_path = f'{DRIVE_FOLDER}/innovation-lab-logo.png'
if os.path.exists(logo_path):
    logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
    logo_height, logo_width = logo.shape[:2]
    new_width = 275
    new_height = int(logo_height * (new_width / logo_width))
    logo_resized = cv2.resize(logo, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    # Create shadow
    logo_shadow = np.zeros_like(logo_resized)
    if logo_resized.shape[2] == 4:
        logo_shadow[:, :, :3] = 30
        logo_shadow[:, :, 3] = logo_resized[:, :, 3] * 0.5
    
    print(f"✅ Logo loaded: {new_width}x{new_height}")
else:
    logo_resized = None
    logo_shadow = None

# ============================================
# CELL 5: Select & Convert Video (FAST!)
# ============================================
# Set input video
input_video = f'{DRIVE_FOLDER}/clean_bee_hi_res.mp4'

# Fast conversion: 4K → 1080p + 60fps interpolation (2-3 minutes)
print("🔄 Converting to 1080p @ 60fps (optimized)...")
compatible_video = 'bee_1080p_60fps.mp4'

cmd = [
    'ffmpeg', '-i', input_video,
    '-vf', 'scale=1920:1080,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
    '-c:v', 'h264_nvenc',  # GPU encoder
    '-preset', 'p4',
    '-crf', '23',
    '-c:a', 'copy',
    '-y',
    compatible_video
]

result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    cap = cv2.VideoCapture(compatible_video)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    print(f"✅ Video ready!")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Frames: {total_frames}")
    
    input_video = compatible_video
else:
    print("❌ Conversion failed, using original")

# ============================================
# CELL 6: Configuration (60fps optimized)
# ============================================
CONFIG = {
    'output_path': 'bee_enhanced_60fps.mp4',
    'conf_threshold': 0.50,
    'iou_threshold': 0.45,
    'track_activation_threshold': 0.25,
    'lost_track_buffer': 60,  # 2x for 60fps (was 30 for 30fps)
    'minimum_matching_threshold': 0.8,
    'minimum_consecutive_frames': 2,  # Slightly higher for 60fps
    'show_trails': True,
    'trail_length': 60,  # 1 second trail at 60fps
    'show_labels': True,
    'use_bytetrack': True,
}

print("✅ 60fps configuration ready")

# ============================================
# CELL 7: FPS-Aware Behavior Classifier (FIXED!)
# ============================================
def classify_bee_behavior(track_positions, fps):
    """
    FPS-aware behavior classification:
    - Flying: Fast movement (incoming/outgoing bees)
    - Browsing: Slow movement (bees on hive surface)
    - Stationary: No movement (dead bee, stuck, or resting)
    """
    
    if len(track_positions) < int(0.5 * fps):
        return 'unknown'
    
    positions = np.array([(x, y) for x, y, _ in track_positions])
    
    # Calculate speed (pixels per frame)
    distances = np.sqrt(np.sum(np.diff(positions, axis=0)**2, axis=1))
    avg_speed = np.mean(distances)
    max_speed = np.max(distances) if len(distances) > 0 else 0
    
    # FPS-AWARE THRESHOLDS (automatically scale!)
    fps_scale = 30.0 / fps
    SPEED_THRESHOLD_FLYING = 3.0 * fps_scale   # Fast movement
    SPEED_THRESHOLD_MOVING = 0.5 * fps_scale   # Minimum movement
    
    # Classify based on speed
    if max_speed > SPEED_THRESHOLD_FLYING:
        # If bee ever moved fast, it's flying (even if it slows down later)
        return 'flying'
    elif avg_speed < SPEED_THRESHOLD_MOVING:
        # Almost no movement - could be dead or stuck
        return 'stationary'
    else:
        # Slow movement - browsing/walking on hive
        return 'browsing'

print("✅ FPS-aware behavior classifier ready")

# ============================================
# CELL 8: Enhanced Processing Function
# ============================================
def process_video_with_behaviors(model, input_path, output_path, config, logo=None, logo_shadow=None):
    """
    Enhanced processing with:
    - FPS-aware behavior classification
    - Logo with fade-in + shadow
    - 5-second rolling average
    - Text symbols (no emoji issues)
    """
    
    cap = cv2.VideoCapture(input_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Initialize ByteTrack
    byte_tracker = sv.ByteTrack(
        track_activation_threshold=config['track_activation_threshold'],
        lost_track_buffer=config['lost_track_buffer'],
        minimum_matching_threshold=config['minimum_matching_threshold'],
        minimum_consecutive_frames=config['minimum_consecutive_frames'],
        frame_rate=int(fps)
    )
    
    # Annotators
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=2)
    trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=config['trail_length'])
    
    # Logo setup
    logo_position = None
    shadow_position = None
    if logo is not None:
        logo_h, logo_w = logo.shape[:2]
        padding = 20
        shadow_offset = 5
        logo_position = (width - logo_w - padding, height - logo_h - padding)
        shadow_position = (logo_position[0] + shadow_offset, logo_position[1] + shadow_offset)
    
    fade_duration_frames = int(2 * fps)
    
    # Tracking
    track_history = {}
    track_behaviors = {}  # Current behavior
    track_peak_behaviors = {}  # Peak behavior (once flying, always flying)
    
    # Rolling averages (5 seconds)
    rolling_window_frames = int(5 * fps)
    bee_count_history = []
    behavior_history = {'flying': [], 'browsing': [], 'stationary': []}
    
    # Pollen counter (simple incrementing counter)
    pollen_count = 0
    
    print(f"\n🎬 Processing with FPS-aware behavior analysis...")
    print("="*70)
    
    frame_count = 0
    start_time = time.time()
    inference_times = []
    behavior_stats = {'flying': 0, 'erratic': 0, 'browsing': 0}
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # YOLO inference
            t0 = time.time()
            results = model(frame, conf=config['conf_threshold'], iou=config['iou_threshold'], verbose=False)[0]
            inference_times.append(time.time() - t0)
            
            detections = sv.Detections.from_ultralytics(results)
            detections = byte_tracker.update_with_detections(detections)
            
            # Update track history and classify
            for bbox, tracker_id in zip(detections.xyxy, detections.tracker_id):
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                if tracker_id not in track_history:
                    track_history[tracker_id] = []
                    track_behaviors[tracker_id] = 'unknown'
                
                track_history[tracker_id].append((center_x, center_y, frame_count))
                
                # Keep last 3 seconds
                max_history = int(3 * fps)
                if len(track_history[tracker_id]) > max_history:
                    track_history[tracker_id] = track_history[tracker_id][-max_history:]
                
                # Classify (need 1 second of data)
                if len(track_history[tracker_id]) >= int(1 * fps):
                    current_behavior = classify_bee_behavior(track_history[tracker_id], fps)
                    track_behaviors[tracker_id] = current_behavior
                    
                    # Track peak behavior (once flying, always flying)
                    if tracker_id not in track_peak_behaviors:
                        track_peak_behaviors[tracker_id] = current_behavior
                    elif current_behavior == 'flying':
                        track_peak_behaviors[tracker_id] = 'flying'
                    elif track_peak_behaviors[tracker_id] != 'flying' and current_behavior == 'browsing':
                        track_peak_behaviors[tracker_id] = 'browsing'
            
            # Rolling averages
            bee_count_history.append(len(detections))
            if len(bee_count_history) > rolling_window_frames:
                bee_count_history = bee_count_history[-rolling_window_frames:]
            rolling_avg_bees = np.mean(bee_count_history) if bee_count_history else 0
            
            # Count current behaviors
            current_behaviors = {'flying': 0, 'browsing': 0, 'stationary': 0}
            for tracker_id in detections.tracker_id:
                behavior = track_peak_behaviors.get(tracker_id, 'unknown')
                if behavior in current_behaviors:
                    current_behaviors[behavior] += 1
            
            # Update behavior rolling averages
            for behavior in ['flying', 'browsing', 'stationary']:
                behavior_history[behavior].append(current_behaviors[behavior])
                if len(behavior_history[behavior]) > rolling_window_frames:
                    behavior_history[behavior] = behavior_history[behavior][-rolling_window_frames:]
            
            # Calculate 5-second rolling averages
            rolling_avg_flying = np.mean(behavior_history['flying']) if behavior_history['flying'] else 0
            rolling_avg_browsing = np.mean(behavior_history['browsing']) if behavior_history['browsing'] else 0
            rolling_avg_stationary = np.mean(behavior_history['stationary']) if behavior_history['stationary'] else 0
            
            # Annotate trails
            if len(detections) > 0:
                frame = trace_annotator.annotate(scene=frame, detections=detections)
            
            # Bounding boxes with behavior colors (use peak behavior)
            for bbox, tracker_id in zip(detections.xyxy, detections.tracker_id):
                behavior = track_peak_behaviors.get(tracker_id, 'unknown')
                color_map = {
                    'flying': (0, 255, 255),      # Cyan
                    'browsing': (0, 255, 0),      # Green
                    'stationary': (0, 0, 255),    # Red
                    'unknown': (128, 128, 128)    # Gray
                }
                color = color_map.get(behavior, (255, 255, 255))
                x1, y1, x2, y2 = bbox.astype(int)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Labels with TEXT symbols (use peak behavior)
            if len(detections) > 0:
                labels = []
                for tracker_id, confidence in zip(detections.tracker_id, detections.confidence):
                    behavior = track_peak_behaviors.get(tracker_id, 'unknown')
                    symbol_map = {
                        'flying': 'FLY',
                        'browsing': 'BRW',
                        'stationary': 'STA',
                        'unknown': '???'
                    }
                    symbol = symbol_map.get(behavior, '???')
                    labels.append(f"#{tracker_id} {symbol} {confidence:0.2f}")
                
                frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
            
            # Pollen detection (simple counter - increment randomly for demo)
            # TODO: Replace with actual YOLO pollen detection model
            if len(detections) > 0 and frame_count % 60 == 0:  # Every 2 seconds
                pollen_count += np.random.randint(0, 2)  # Simulate pollen detection
            
            # Count behaviors
            behavior_stats = {'flying': 0, 'browsing': 0, 'stationary': 0}
            for tracker_id in detections.tracker_id:
                behavior = track_behaviors.get(tracker_id, 'unknown')
                if behavior in behavior_stats:
                    behavior_stats[behavior] += 1
            
            # Stats panel (expanded for new classifications)
            panel_height = 240
            cv2.rectangle(frame, (10, 10), (400, panel_height), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, 10), (400, panel_height), (0, 255, 255), 2)
            
            y_pos = 30
            cv2.putText(frame, "DIGITAL4.AI BYTETRACK", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            y_pos += 30
            cv2.putText(frame, f"BEES NOW: {len(detections)}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 25
            cv2.putText(frame, f"5s AVG: {rolling_avg_bees:.1f}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 2)
            
            y_pos += 25
            cv2.putText(frame, "BEHAVIORS (5s AVG):", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_pos += 20
            cv2.putText(frame, f"  Flying: {rolling_avg_flying:.1f}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y_pos += 18
            cv2.putText(frame, f"  Browsing: {rolling_avg_browsing:.1f}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y_pos += 18
            cv2.putText(frame, f"  Stationary: {rolling_avg_stationary:.1f}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            y_pos += 25
            cv2.putText(frame, f"POLLEN COUNT: {pollen_count}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 2)
            
            y_pos += 25
            cv2.putText(frame, f"FRAME: {frame_count}/{total_frames}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            
            # Logo with fade-in
            if logo is not None and logo_position is not None:
                fade_alpha = min(1.0, frame_count / fade_duration_frames)
                x, y = logo_position
                shadow_x, shadow_y = shadow_position
                logo_h, logo_w = logo.shape[:2]
                
                # Shadow
                if logo_shadow is not None and logo_shadow.shape[2] == 4:
                    shadow_alpha_channel = (logo_shadow[:, :, 3] / 255.0) * fade_alpha * 0.6
                    for c in range(3):
                        frame[shadow_y:shadow_y+logo_h, shadow_x:shadow_x+logo_w, c] = (
                            shadow_alpha_channel * logo_shadow[:, :, c] +
                            (1 - shadow_alpha_channel) * frame[shadow_y:shadow_y+logo_h, shadow_x:shadow_x+logo_w, c]
                        )
                
                # Logo
                if logo.shape[2] == 4:
                    alpha = (logo[:, :, 3] / 255.0) * fade_alpha
                    for c in range(3):
                        frame[y:y+logo_h, x:x+logo_w, c] = (
                            alpha * logo[:, :, c] +
                            (1 - alpha) * frame[y:y+logo_h, x:x+logo_w, c]
                        )
            
            out.write(frame)
            
            # Progress
            if frame_count % 30 == 0 or frame_count == total_frames:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed
                avg_inference = np.mean(inference_times[-30:]) * 1000
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                
                print(f"Frame {frame_count:4d}/{total_frames} ({frame_count/total_frames*100:5.1f}%) | "
                      f"Bees:{len(detections):3d} Avg:{rolling_avg_bees:.1f} | "
                      f"FLY:{rolling_avg_flying:.1f} BRW:{rolling_avg_browsing:.1f} STA:{rolling_avg_stationary:.1f} | "
                      f"Pollen:{pollen_count} | GPU:{avg_inference:5.1f}ms | FPS:{fps_processing:5.1f} | ETA:{eta/60:4.1f}min")
    
    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted")
    
    finally:
        cap.release()
        out.release()
    
    elapsed = time.time() - start_time
    avg_inference = np.mean(inference_times) * 1000 if inference_times else 0
    
    print("\n" + "="*70)
    print(f"✅ PROCESSING COMPLETE!")
    print("="*70)
    print(f"Processed: {frame_count}/{total_frames} frames")
    print(f"⚡ Avg inference: {avg_inference:.1f}ms")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print(f"🚀 Processing FPS: {frame_count/elapsed:.1f}")
    print(f"📁 Output: {output_path}")
    
    return output_path, track_history, track_peak_behaviors, pollen_count

print("✅ Processing function ready")

# ============================================
# CELL 9: Run Processing
# ============================================
output_video, track_history, track_behaviors, pollen_count = process_video_with_behaviors(
    model=model,
    input_path=input_video,
    output_path=CONFIG['output_path'],
    config=CONFIG,
    logo=logo_resized,
)

print(f"\n✅ Enhanced video ready: {output_video}")
print(f"   Total pollen detected: {pollen_count}")
print("\n📊 Features included:")
print("  ✅ FPS-aware behavior classification (Flying/Browsing/Stationary)")
print("  ✅ Peak behavior tracking (bees that flew stay as 'flying')")
print("  ✅ 5-second rolling averages for ALL metrics")
print("  ✅ Stationary detection (dead/stuck bees)")
print("  ✅ Pollen counter (demo - needs actual YOLO model)")
print("  ✅ Logo with 2-second fade-in + shadow")
print("  ✅ Text symbols (FLY/BRW/STA) - no emoji issues")
print("  ✅ Color-coded: Cyan=Flying, Green=Browsing, Red=Stationary")

# ============================================
# CELL 10: Export Data
# ============================================
import json

# Get video info
cap = cv2.VideoCapture(input_video)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()

# Export
export_data = {
    'video': os.path.basename(input_video),
    'fps': fps,
    'total_frames': total_frames,
    'tracks': {},
    'summary': {
        'total_unique_bees': len(track_history),
        'behaviors': {
            'flying': sum(1 for b in track_behaviors.values() if b == 'flying'),
            'browsing': sum(1 for b in track_behaviors.values() if b == 'browsing'),
            'stationary': sum(1 for b in track_behaviors.values() if b == 'stationary'),
            'unknown': sum(1 for b in track_behaviors.values() if b == 'unknown')
        },
        'pollen_count': pollen_count
    }
}

for track_id, positions in track_history.items():
    export_data['tracks'][int(track_id)] = {
        'behavior': track_behaviors.get(track_id, 'unknown'),
        'trajectory': [(float(x), float(y), int(f)) for x, y, f in positions]
    }

json_path = 'bee_tracking_data.json'
with open(json_path, 'w') as f:
    json.dump(export_data, f, indent=2)

print(f"\n📊 Exported tracking data:")
print(f"   Unique bees: {export_data['summary']['total_unique_bees']}")
print(f"   Flying: {export_data['summary']['behaviors']['flying']}")
print(f"   Browsing: {export_data['summary']['behaviors']['browsing']}")
print(f"   Stationary: {export_data['summary']['behaviors']['stationary']}")
print(f"   Pollen count: {export_data['summary']['pollen_count']}")

# Download
from google.colab import files
files.download(json_path)

# ============================================
# CELL 11: Display & Download
# ============================================
print("📺 Displaying processed video:")
display(Video(output_video, width=800))

print("\n📥 Downloading video...")
files.download(output_video)

print("\n✅ All done!")
