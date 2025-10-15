# 🐝 Enhanced Bee Processing with Behaviors & Analytics

## Features:
- ✅ Logo with fade-in animation + shadow
- ✅ 5-second rolling average bee count
- ✅ Bee behavior classification (Flying, Erratic, Browsing)
- ✅ Trajectory analysis with ByteTrack

---

## Part 1: Logo Loading with Shadow

```python
# Load logo with 10% larger size + prepare for shadow
logo_path = f'{DRIVE_FOLDER}/digital4ai-logo.png'

if os.path.exists(logo_path):
    logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
    print(f"✅ Logo loaded: {logo.shape}")
    
    logo_height, logo_width = logo.shape[:2]
    # 10% larger than before (was 250, now 275)
    new_width = 275
    new_height = int(logo_height * (new_width / logo_width))
    logo_resized = cv2.resize(logo, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    print(f"   Resized to: {new_width}x{new_height} (10% larger)")
    
    # Create shadow layer (same size, offset, darker)
    shadow_offset = 5  # pixels
    logo_shadow = np.zeros_like(logo_resized)
    if logo_resized.shape[2] == 4:  # Has alpha
        # Create dark shadow with same alpha
        logo_shadow[:, :, :3] = 30  # Dark gray
        logo_shadow[:, :, 3] = logo_resized[:, :, 3] * 0.5  # 50% alpha
    
else:
    print(f"❌ Logo not found")
    logo_resized = None
    logo_shadow = None
```

---

## Part 2: Enhanced Processing Function with Behaviors

```python
def process_video_with_behaviors(model, input_path, output_path, config, logo=None, logo_shadow=None):
    """
    Enhanced video processing with:
    - Logo fade-in animation + shadow
    - 5-second rolling average bee count
    - Bee behavior classification (Flying, Erratic, Browsing)
    """
    
    cap = cv2.VideoCapture(input_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Initialize ByteTrack
    byte_tracker = None
    if config.get('use_bytetrack', True):
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
    
    trace_annotator = None
    if config.get('show_trails', False):
        trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=config['trail_length'])
    
    # Logo setup with shadow
    logo_position = None
    shadow_position = None
    if logo is not None:
        logo_h, logo_w = logo.shape[:2]
        padding = 20
        shadow_offset = 5
        logo_position = (width - logo_w - padding, height - logo_h - padding)
        shadow_position = (logo_position[0] + shadow_offset, logo_position[1] + shadow_offset)
    
    # Logo fade-in duration (2 seconds)
    fade_duration_frames = int(2 * fps)
    
    # Behavior tracking
    track_history = {}  # {track_id: [(x, y, frame), ...]}
    track_behaviors = {}  # {track_id: 'flying' | 'erratic' | 'browsing'}
    
    # Rolling average for bee count (5 seconds)
    rolling_window_frames = int(5 * fps)  # 5 seconds
    bee_count_history = []
    
    mode_name = "WITH ByteTrack" if byte_tracker else "WITHOUT ByteTrack"
    print(f"\n🎬 Processing {mode_name} with Behavior Analysis...")
    print("="*70)
    
    frame_count = 0
    start_time = time.time()
    inference_times = []
    
    # Behavior counters
    behavior_stats = {'flying': 0, 'erratic': 0, 'browsing': 0}
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # YOLO inference
            t0 = time.time()
            results = model(
                frame,
                conf=config['conf_threshold'],
                iou=config['iou_threshold'],
                verbose=False
            )[0]
            inference_time = time.time() - t0
            inference_times.append(inference_time)
            
            # Convert to supervision Detections
            detections = sv.Detections.from_ultralytics(results)
            
            # Apply ByteTrack
            if byte_tracker:
                detections = byte_tracker.update_with_detections(detections)
                
                # Update track history and classify behaviors
                for i, (bbox, tracker_id) in enumerate(zip(detections.xyxy, detections.tracker_id)):
                    x1, y1, x2, y2 = bbox
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    # Initialize track if new
                    if tracker_id not in track_history:
                        track_history[tracker_id] = []
                        track_behaviors[tracker_id] = 'unknown'
                    
                    # Store position
                    track_history[tracker_id].append((center_x, center_y, frame_count))
                    
                    # Keep only last 3 seconds of history
                    max_history = int(3 * fps)
                    if len(track_history[tracker_id]) > max_history:
                        track_history[tracker_id] = track_history[tracker_id][-max_history:]
                    
                    # Classify behavior (need at least 1 second of data)
                    min_frames = int(1 * fps)
                    if len(track_history[tracker_id]) >= min_frames:
                        behavior = classify_bee_behavior(track_history[tracker_id], fps)
                        track_behaviors[tracker_id] = behavior
            
            # Update bee count history for rolling average
            bee_count_history.append(len(detections))
            if len(bee_count_history) > rolling_window_frames:
                bee_count_history = bee_count_history[-rolling_window_frames:]
            
            # Calculate 5-second rolling average
            rolling_avg = np.mean(bee_count_history) if bee_count_history else 0
            
            # Annotate: Trails
            if trace_annotator and len(detections) > 0 and byte_tracker:
                frame = trace_annotator.annotate(scene=frame, detections=detections)
            
            # Annotate: Bounding boxes with behavior colors
            if byte_tracker and len(detections) > 0:
                # Color code by behavior
                for i, (bbox, tracker_id) in enumerate(zip(detections.xyxy, detections.tracker_id)):
                    behavior = track_behaviors.get(tracker_id, 'unknown')
                    
                    # Behavior colors
                    color_map = {
                        'flying': (0, 255, 255),    # Cyan - fast incoming
                        'erratic': (0, 165, 255),   # Orange - irregular
                        'browsing': (0, 255, 0),    # Green - slow/landed
                        'unknown': (128, 128, 128)  # Gray
                    }
                    color = color_map.get(behavior, (255, 255, 255))
                    
                    x1, y1, x2, y2 = bbox.astype(int)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            else:
                frame = box_annotator.annotate(scene=frame, detections=detections)
            
            # Annotate: Labels with behaviors
            if config.get('show_labels', False) and len(detections) > 0:
                if byte_tracker:
                    labels = []
                    for tracker_id, confidence in zip(detections.tracker_id, detections.confidence):
                        behavior = track_behaviors.get(tracker_id, '?')
                        behavior_emoji = {
                            'flying': '✈',
                            'erratic': '⚡',
                            'browsing': '🌸',
                            'unknown': '?'
                        }
                        emoji = behavior_emoji.get(behavior, '?')
                        labels.append(f"#{tracker_id} {emoji} {confidence:0.2f}")
                    
                    frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
                else:
                    labels = [f"{confidence:0.2f}" for confidence in detections.confidence]
                    frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
            
            # Count current behaviors
            if byte_tracker:
                behavior_stats = {'flying': 0, 'erratic': 0, 'browsing': 0}
                for tracker_id in detections.tracker_id:
                    behavior = track_behaviors.get(tracker_id, 'unknown')
                    if behavior in behavior_stats:
                        behavior_stats[behavior] += 1
            
            # Stats panel (top-left) - EXPANDED
            panel_height = 200
            cv2.rectangle(frame, (10, 10), (380, panel_height), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, 10), (380, panel_height), (0, 255, 255), 2)
            
            y_pos = 30
            mode_text = "BYTETRACK + YOLO11M" if byte_tracker else "YOLO11M DETECTION"
            cv2.putText(frame, mode_text, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            y_pos += 30
            cv2.putText(frame, f"BEES NOW: {len(detections)}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            y_pos += 30
            cv2.putText(frame, f"5s AVG: {rolling_avg:.1f}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
            
            # Behavior breakdown
            if byte_tracker and sum(behavior_stats.values()) > 0:
                y_pos += 25
                cv2.putText(frame, "BEHAVIORS:", (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                y_pos += 20
                cv2.putText(frame, f"  Flying: {behavior_stats['flying']}", (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                y_pos += 18
                cv2.putText(frame, f"  Erratic: {behavior_stats['erratic']}", (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                
                y_pos += 18
                cv2.putText(frame, f"  Browsing: {behavior_stats['browsing']}", (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            y_pos += 25
            cv2.putText(frame, f"FRAME: {frame_count}/{total_frames}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            
            # Add logo with fade-in and shadow
            if logo is not None and logo_position is not None:
                # Calculate fade alpha (0 to 1 over first 2 seconds)
                fade_alpha = min(1.0, frame_count / fade_duration_frames)
                
                x, y = logo_position
                shadow_x, shadow_y = shadow_position
                logo_h, logo_w = logo.shape[:2]
                
                # Draw shadow first (if has alpha)
                if logo_shadow is not None and logo_shadow.shape[2] == 4:
                    shadow_alpha_channel = (logo_shadow[:, :, 3] / 255.0) * fade_alpha * 0.6  # Softer shadow
                    for c in range(3):
                        frame[shadow_y:shadow_y+logo_h, shadow_x:shadow_x+logo_w, c] = (
                            shadow_alpha_channel * logo_shadow[:, :, c] +
                            (1 - shadow_alpha_channel) * frame[shadow_y:shadow_y+logo_h, shadow_x:shadow_x+logo_w, c]
                        )
                
                # Draw logo with fade
                if logo.shape[2] == 4:  # Has alpha channel
                    alpha = (logo[:, :, 3] / 255.0) * fade_alpha
                    for c in range(3):
                        frame[y:y+logo_h, x:x+logo_w, c] = (
                            alpha * logo[:, :, c] +
                            (1 - alpha) * frame[y:y+logo_h, x:x+logo_w, c]
                        )
                else:
                    # No alpha, use fade_alpha directly
                    blended = cv2.addWeighted(
                        logo[:, :, :3], fade_alpha,
                        frame[y:y+logo_h, x:x+logo_w], 1 - fade_alpha,
                        0
                    )
                    frame[y:y+logo_h, x:x+logo_w] = blended
            
            out.write(frame)
            
            # Progress
            if frame_count % 30 == 0 or frame_count == total_frames:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed
                avg_inference = np.mean(inference_times[-30:]) * 1000
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                
                print(f"Frame {frame_count:4d}/{total_frames} ({frame_count/total_frames*100:5.1f}%) | "
                      f"Bees:{len(detections):3d} Avg:{rolling_avg:.1f} | "
                      f"F:{behavior_stats.get('flying',0)} E:{behavior_stats.get('erratic',0)} B:{behavior_stats.get('browsing',0)} | "
                      f"GPU:{avg_inference:5.1f}ms | FPS:{fps_processing:5.1f} | ETA:{eta/60:4.1f}min")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processing interrupted")
    
    finally:
        cap.release()
        out.release()
    
    # Final stats
    elapsed = time.time() - start_time
    avg_inference = np.mean(inference_times) * 1000 if inference_times else 0
    
    print("\n" + "="*70)
    print(f"✅ {mode_name} WITH BEHAVIORS COMPLETE!")
    print("="*70)
    print(f"Processed: {frame_count}/{total_frames} frames")
    print(f"⚡ Avg inference: {avg_inference:.1f}ms")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print(f"🚀 Processing FPS: {frame_count/elapsed:.1f}")
    print(f"📁 Output: {output_path}")
    
    return output_path


def classify_bee_behavior(track_positions, fps):
    """
    Classify bee behavior based on trajectory:
    - Flying: Fast, relatively straight (incoming/outgoing)
    - Erratic: Fast but irregular, many direction changes
    - Browsing: Slow, small movements (landed or hovering)
    """
    
    if len(track_positions) < int(0.5 * fps):  # Need at least 0.5s data
        return 'unknown'
    
    # Extract positions
    positions = np.array([(x, y) for x, y, _ in track_positions])
    
    # Calculate metrics
    # 1. Speed (pixels per frame)
    distances = np.sqrt(np.sum(np.diff(positions, axis=0)**2, axis=1))
    avg_speed = np.mean(distances)
    
    # 2. Direction changes (angular variance)
    if len(positions) > 2:
        vectors = np.diff(positions, axis=0)
        angles = np.arctan2(vectors[:, 1], vectors[:, 0])
        angle_changes = np.abs(np.diff(angles))
        # Normalize angles to 0-π
        angle_changes = np.minimum(angle_changes, 2*np.pi - angle_changes)
        avg_angle_change = np.mean(angle_changes)
    else:
        avg_angle_change = 0
    
    # 3. Total displacement vs path length (straightness)
    total_path = np.sum(distances)
    displacement = np.linalg.norm(positions[-1] - positions[0])
    straightness = displacement / total_path if total_path > 0 else 0
    
    # Classification thresholds
    SPEED_THRESHOLD_FAST = 3.0  # pixels/frame
    SPEED_THRESHOLD_SLOW = 1.0
    ANGLE_THRESHOLD_ERRATIC = 0.5  # radians (~30 degrees)
    STRAIGHTNESS_THRESHOLD = 0.6
    
    # Classify
    if avg_speed < SPEED_THRESHOLD_SLOW:
        return 'browsing'  # Slow moving or landed
    elif avg_speed > SPEED_THRESHOLD_FAST:
        if avg_angle_change > ANGLE_THRESHOLD_ERRATIC or straightness < STRAIGHTNESS_THRESHOLD:
            return 'erratic'  # Fast but irregular
        else:
            return 'flying'  # Fast and relatively straight
    else:
        # Medium speed
        if avg_angle_change > ANGLE_THRESHOLD_ERRATIC:
            return 'erratic'
        else:
            return 'browsing'

print("✅ Enhanced processing function with behaviors ready!")
```

---

## Part 3: Process with All Enhancements

```python
# Process video with all enhancements
output_enhanced = process_video_with_behaviors(
    model=model,
    input_path=input_video,
    output_path='bee_ENHANCED_bytetrack.mp4',
    config=CONFIG_WITH_BYTETRACK,
    logo=logo_resized,
    logo_shadow=logo_shadow
)

print(f"\n✅ Enhanced video ready: {output_enhanced}")
print("\nFeatures included:")
print("  ✅ Logo with 2-second fade-in + shadow")
print("  ✅ 5-second rolling average bee count")
print("  ✅ Behavior classification:")
print("     - ✈ Flying (fast, straight)")
print("     - ⚡ Erratic (fast, irregular)")
print("     - 🌸 Browsing (slow, landed)")
print("  ✅ Color-coded bounding boxes by behavior")
print("  ✅ Real-time behavior statistics")
```

---

## Part 4: Export Data for Analysis

```python
# Save trajectory and behavior data to JSON
import json

# Export track data
export_data = {
    'video': os.path.basename(input_video),
    'fps': fps,
    'total_frames': total_frames,
    'tracks': {},
    'summary': {
        'total_unique_bees': len(track_history),
        'behaviors': {
            'flying': sum(1 for b in track_behaviors.values() if b == 'flying'),
            'erratic': sum(1 for b in track_behaviors.values() if b == 'erratic'),
            'browsing': sum(1 for b in track_behaviors.values() if b == 'browsing')
        }
    }
}

for track_id, positions in track_history.items():
    export_data['tracks'][int(track_id)] = {
        'behavior': track_behaviors.get(track_id, 'unknown'),
        'trajectory': [(float(x), float(y), int(f)) for x, y, f in positions]
    }

# Save to file
json_path = 'bee_tracking_data.json'
with open(json_path, 'w') as f:
    json.dump(export_data, f, indent=2)

print(f"\n📊 Exported tracking data to: {json_path}")
print(f"   Unique bees tracked: {export_data['summary']['total_unique_bees']}")
print(f"   Flying: {export_data['summary']['behaviors']['flying']}")
print(f"   Erratic: {export_data['summary']['behaviors']['erratic']}")
print(f"   Browsing: {export_data['summary']['behaviors']['browsing']}")

# Download the JSON
from google.colab import files
files.download(json_path)
```

---

## Summary of Enhancements:

### Visual:
- ✅ **Logo:** 10% larger (275px), fade-in over 2 seconds, drop shadow
- ✅ **Behavior colors:** Cyan (flying), Orange (erratic), Green (browsing)
- ✅ **Rolling average:** 5-second window displayed prominently

### Analytics:
- ✅ **Behavior classification:** Flying, Erratic, Browsing based on speed + trajectory
- ✅ **Real-time stats:** Live behavior counts in video overlay
- ✅ **Data export:** JSON with all track trajectories and classifications

### Metrics:
- Speed: pixels/frame
- Direction changes: angular variance
- Straightness: displacement vs path length
- All tunable thresholds

**Copy these cells into your Colab and run!** 🚀🐝
