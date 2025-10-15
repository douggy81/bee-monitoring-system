# 🐝 Bee Video Processing - Colab Instructions

## Quick Setup in Your Existing Notebook

Add these cells to your working Colab notebook (`Copy_of_bee_bytetrack_gpu_processing.ipynb`):

---

## Cell: Configuration for Both Modes

```python
# ========================================
# TWO OUTPUT MODES
# ========================================

# Mode 1: WITH ByteTrack (persistent IDs, trails)
CONFIG_WITH_BYTETRACK = {
    'output_path': 'bee_WITH_bytetrack.mp4',
    'conf_threshold': 0.25,
    'iou_threshold': 0.45,
    'track_activation_threshold': 0.25,
    'lost_track_buffer': 30,
    'minimum_matching_threshold': 0.8,
    'minimum_consecutive_frames': 1,
    'show_trails': True,
    'trail_length': 30,
    'show_labels': True,
    'use_bytetrack': True,
}

# Mode 2: WITHOUT ByteTrack (detection only)
CONFIG_WITHOUT_BYTETRACK = {
    'output_path': 'bee_WITHOUT_bytetrack.mp4',
    'conf_threshold': 0.25,
    'iou_threshold': 0.45,
    'track_activation_threshold': 0.25,
    'lost_track_buffer': 30,
    'minimum_matching_threshold': 0.8,
    'minimum_consecutive_frames': 1,
    'show_trails': False,
    'trail_length': 30,
    'show_labels': True,
    'use_bytetrack': False,
}

print("✅ Configurations ready:")
print("   1. WITH ByteTrack: Persistent tracking + trails")
print("   2. WITHOUT ByteTrack: Detection boxes only")
```

---

## Cell: Updated Processing Function (Dual Mode)

```python
def process_video_dual_mode(model, input_path, output_path, config):
    """
    Process video with YOLO11m + optional ByteTrack.
    No line zones - just tracking/detection.
    """
    
    cap = cv2.VideoCapture(input_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Initialize ByteTrack only if enabled
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
    
    mode_name = "WITH ByteTrack" if byte_tracker else "WITHOUT ByteTrack"
    print(f"\n🎬 Processing {mode_name}...")
    print("="*70)
    
    frame_count = 0
    start_time = time.time()
    inference_times = []
    
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
            
            # Apply ByteTrack if enabled
            if byte_tracker:
                detections = byte_tracker.update_with_detections(detections)
            
            # Annotate: Trails (ByteTrack only)
            if trace_annotator and len(detections) > 0 and byte_tracker:
                frame = trace_annotator.annotate(scene=frame, detections=detections)
            
            # Annotate: Bounding boxes
            frame = box_annotator.annotate(scene=frame, detections=detections)
            
            # Annotate: Labels
            if config.get('show_labels', False) and len(detections) > 0:
                if byte_tracker:
                    # With ByteTrack: show persistent track IDs
                    labels = [
                        f"#{tracker_id} {confidence:0.2f}"
                        for tracker_id, confidence in zip(detections.tracker_id, detections.confidence)
                    ]
                else:
                    # Without ByteTrack: just confidence
                    labels = [f"{confidence:0.2f}" for confidence in detections.confidence]
                
                frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
            
            # Stats panel
            cv2.rectangle(frame, (10, 10), (350, 100), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, 10), (350, 100), (0, 255, 255), 2)
            
            y_pos = 30
            mode_text = "BYTETRACK + YOLO11M" if byte_tracker else "YOLO11M DETECTION"
            cv2.putText(frame, mode_text, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            y_pos += 30
            cv2.putText(frame, f"BEES: {len(detections)}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 30
            cv2.putText(frame, f"FRAME: {frame_count}/{total_frames}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            out.write(frame)
            
            # Progress
            if frame_count % 30 == 0 or frame_count == total_frames:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed
                avg_inference = np.mean(inference_times[-30:]) * 1000
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                
                print(f"Frame {frame_count:4d}/{total_frames} ({frame_count/total_frames*100:5.1f}%) | "
                      f"Bees:{len(detections):3d} | "
                      f"GPU:{avg_inference:5.1f}ms | "
                      f"FPS:{fps_processing:5.1f} | "
                      f"ETA:{eta/60:4.1f}min")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processing interrupted")
    
    finally:
        cap.release()
        out.release()
    
    # Final stats
    elapsed = time.time() - start_time
    avg_inference = np.mean(inference_times) * 1000 if inference_times else 0
    
    print("\n" + "="*70)
    print(f"✅ {mode_name} COMPLETE!")
    print("="*70)
    print(f"Processed: {frame_count}/{total_frames} frames")
    print(f"⚡ Avg inference: {avg_inference:.1f}ms")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print(f"🚀 Processing FPS: {frame_count/elapsed:.1f}")
    print(f"📁 Output: {output_path}")
    
    return output_path

print("✅ Dual-mode processing function ready!")
```

---

## Cell: Process Both Versions

```python
# Process VERSION 1: WITH ByteTrack
print("=" * 70)
print("🎬 CREATING VERSION 1: WITH BYTETRACK")
print("=" * 70)

output_with = process_video_dual_mode(
    model=model,
    input_path=input_video,
    output_path=CONFIG_WITH_BYTETRACK['output_path'],
    config=CONFIG_WITH_BYTETRACK
)

print("\n\n")

# Process VERSION 2: WITHOUT ByteTrack  
print("=" * 70)
print("🎬 CREATING VERSION 2: WITHOUT BYTETRACK")
print("=" * 70)

output_without = process_video_dual_mode(
    model=model,
    input_path=input_video,
    output_path=CONFIG_WITHOUT_BYTETRACK['output_path'],
    config=CONFIG_WITHOUT_BYTETRACK
)

print("\n\n")
print("=" * 70)
print("✅ BOTH VIDEOS COMPLETE!")
print("=" * 70)
print(f"📹 1. WITH ByteTrack: {output_with}")
print(f"   - Persistent track IDs")
print(f"   - 30-frame trails")
print(f"   - Occlusion handling")
print(f"\n📹 2. WITHOUT ByteTrack: {output_without}")
print(f"   - Frame-by-frame detection")
print(f"   - No persistent tracking")
print(f"   - Simpler visualization")
```

---

## Cell: Download Both Videos

```python
# Save both to Google Drive
import shutil

print("💾 Saving to Google Drive...")

drive_path_with = f'{DRIVE_FOLDER}/{output_with}'
drive_path_without = f'{DRIVE_FOLDER}/{output_without}'

shutil.copy(output_with, drive_path_with)
shutil.copy(output_without, drive_path_without)

print(f"✅ Saved to Drive:")
print(f"   {drive_path_with}")
print(f"   {drive_path_without}")

# Download to local computer
from google.colab import files

print("\n📥 Downloading WITH ByteTrack...")
files.download(output_with)

print("📥 Downloading WITHOUT ByteTrack...")
files.download(output_without)

print("\n✅ Both videos downloaded!")
```

---

## What You Get:

### Video 1: WITH ByteTrack
- ✅ Persistent track IDs (#1, #2, #3...)
- ✅ 30-frame motion trails
- ✅ Tracks persist across frames
- ✅ Handles occlusions
- ✅ No IN/OUT line

### Video 2: WITHOUT ByteTrack  
- ✅ Detection boxes only
- ✅ New detections each frame
- ✅ No tracking persistence
- ✅ Simpler, cleaner look
- ✅ No IN/OUT line

---

## Speed Comparison:

- **Colab T4 GPU:** 2-3 minutes per video
- **Raspberry Pi CPU:** 2+ hours per video
- **Speedup:** 40-60x faster! ⚡

---

## Copy These Cells Into Your Notebook

1. Add the configuration cell
2. Add the processing function cell
3. Add the "Process Both" cell
4. Add the download cell
5. Run them in order!

Total processing time for both videos: **~4-5 minutes**
