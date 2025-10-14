# YOLO11m Custom Bee Detection - Training & Deployment Plan

## 🎯 Objective
Train YOLO11m (medium) on custom bee dataset and deploy across multiple configurations for comparison.

---

## 📊 Phase 1: Dataset Preparation (Roboflow)

### 1.1 Dataset Upload & Annotation
- [ ] Upload bee images/videos to Roboflow
- [ ] Label/annotate bees (if not already done)
- [ ] Define classes: `bee`, `queen`, `drone` (or whatever classes you need)
- [ ] Split: 70% train, 20% val, 10% test

### 1.2 Dataset Augmentation (Roboflow)
- [ ] Flip: Horizontal
- [ ] Rotate: ±15°
- [ ] Brightness: ±25%
- [ ] Blur: Up to 1.5px
- [ ] Noise: Up to 1%
- [ ] Target: ~2000-3000 images

### 1.3 Export Format
- [ ] Export as YOLO v11 format
- [ ] Download dataset with `data.yaml`

---

## 🚀 Phase 2: Model Training

### 2.1 Setup Training Environment
**Location:** Local Mac or Cloud (Colab/Vast.ai)

```bash
# Install Ultralytics
pip install ultralytics

# Verify GPU (if available)
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 2.2 Train YOLO11m
```python
from ultralytics import YOLO

# Load pretrained YOLO11m
model = YOLO('yolo11m.pt')

# Train on custom bee dataset
results = model.train(
    data='path/to/data.yaml',
    epochs=100,
    imgsz=640,  # or 800 for better accuracy
    batch=16,   # adjust based on GPU memory
    patience=20,
    device=0,   # GPU
    name='yolo11m_bee_custom',
    
    # Hyperparameters
    lr0=0.01,
    lrf=0.01,
    momentum=0.937,
    weight_decay=0.0005,
    warmup_epochs=3,
    
    # Augmentation
    degrees=10,
    translate=0.1,
    scale=0.5,
    shear=0.0,
    perspective=0.0,
    flipud=0.0,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.0,
)

# Export best model
model = YOLO('runs/detect/yolo11m_bee_custom/weights/best.pt')
model.export(format='onnx', imgsz=640)
```

**Training Time Estimate:**
- Local GPU: 2-4 hours (depends on dataset size)
- Google Colab (T4): 3-5 hours
- No GPU: Not recommended (very slow)

---

## 🧪 Phase 3: Testing Configurations

### 3.1 CPU Inference (Baseline)
```python
from ultralytics import YOLO

model = YOLO('yolo11m_bee_custom.pt')
results = model.predict('bee_video.mp4', device='cpu')
```

**Expected Performance:**
- Speed: ~500-800ms/frame (very slow)
- Accuracy: Best (no quantization)

---

### 3.2 CPU + ByteTrack
```python
from ultralytics import YOLO

model = YOLO('yolo11m_bee_custom.pt')
results = model.track(
    source='bee_video.mp4',
    tracker='bytetrack.yaml',
    device='cpu',
    conf=0.3,
    iou=0.5,
)
```

**ByteTrack Config:** `bytetrack.yaml`
```yaml
tracker_type: bytetrack
track_high_thresh: 0.5
track_low_thresh: 0.1
new_track_thresh: 0.6
track_buffer: 30
match_thresh: 0.8
```

---

### 3.3 CPU + BotSort
```python
results = model.track(
    source='bee_video.mp4',
    tracker='botsort.yaml',
    device='cpu',
)
```

**BotSort Config:** `botsort.yaml`
```yaml
tracker_type: botsort
track_high_thresh: 0.5
track_low_thresh: 0.1
new_track_thresh: 0.6
track_buffer: 30
match_thresh: 0.8
proximity_thresh: 0.5
appearance_thresh: 0.25
```

---

## ⚡ Phase 4: Hailo Compilation

### 4.1 Export to ONNX (on Mac/training machine)
```python
from ultralytics import YOLO

model = YOLO('yolo11m_bee_custom.pt')
model.export(format='onnx', imgsz=640, simplify=True)
```

### 4.2 Compile with Hailo DFC (WSL)

**Transfer to WSL:**
```bash
# From Mac
scp yolo11m_bee_custom.onnx user@wsl-host:/path/to/hailo/
```

**Compile Script:** (same as before but for YOLO11m)
```bash
#!/bin/bash
# compile_yolo11m_bee.sh

MODEL_NAME="yolo11m_bee_custom"
ONNX_FILE="${MODEL_NAME}.onnx"
HW_ARCH="hailo8l"
OUTPUT_DIR="output_yolo11m"

# 1. Parse ONNX → HAR
hailo parser onnx \
    ${ONNX_FILE} \
    --output-har-path ${OUTPUT_DIR}/${MODEL_NAME}.har

# 2. Optimize with calibration
hailo optimize \
    ${OUTPUT_DIR}/${MODEL_NAME}.har \
    --hw-arch ${HW_ARCH} \
    --use-random-calib-set \
    --output-har-path ${OUTPUT_DIR}/${MODEL_NAME}_optimized.har

# 3. Compile to HEF
hailo compiler \
    ${OUTPUT_DIR}/${MODEL_NAME}_optimized.har \
    --hw-arch ${HW_ARCH} \
    --output-dir ${OUTPUT_DIR}

echo "Compilation complete! HEF: ${OUTPUT_DIR}/${MODEL_NAME}.hef"
```

**Expected Results:**
- YOLO11m is ~2-3x larger than 11n
- Should still run at ~40-50ms/frame on Hailo-8L
- Better accuracy than 11n

---

### 4.3 Deploy Hailo HEF to Pi
```bash
# Copy HEF to Pi
scp output_yolo11m/yolo11m_bee_custom.hef rpi:/opt/bee-monitoring/src/api/models/

# Update hailo_backend.py model priority
# (Already has the infrastructure)
```

---

### 4.4 Hailo + ByteTrack

**Create tracking script:**
```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/bee-monitoring/src')

from ai.hailo_backend import HailoBackend
import cv2
import numpy as np

# ByteTrack implementation
from tracking.byte_tracker import BYTETracker

backend = HailoBackend(hef_path='/opt/bee-monitoring/src/api/models/yolo11m_bee_custom.hef')
tracker = BYTETracker(
    track_thresh=0.5,
    track_buffer=30,
    match_thresh=0.8,
)

cap = cv2.VideoCapture('bee_video.mp4')
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Hailo inference
    results = backend.infer(frame)
    detections = parse_detections(results)  # Convert to tracking format
    
    # Update tracks
    tracks = tracker.update(detections, frame.shape)
    
    # Draw tracked bees
    for track in tracks:
        draw_track(frame, track)
    
    cv2.imshow('Hailo + ByteTrack', frame)
```

---

### 4.5 Hailo + BotSort
Similar to ByteTrack but with appearance features.

---

## 📊 Phase 5: Performance Comparison

### Benchmark Matrix

| Configuration | Speed (FPS) | Accuracy | Tracking | Notes |
|--------------|-------------|----------|----------|-------|
| CPU (11m) | ~1-2 FPS | ⭐⭐⭐⭐⭐ | ❌ | Baseline accuracy |
| CPU + ByteTrack | ~1-2 FPS | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Smooth tracks |
| CPU + BotSort | ~0.5-1 FPS | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Best tracking |
| Hailo (11n) | ~47 FPS | ⭐⭐⭐ | ❌ | Current (fast, less accurate) |
| Hailo (11m) | ~20-25 FPS | ⭐⭐⭐⭐ | ❌ | Better accuracy |
| Hailo (11m) + ByteTrack | ~20 FPS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Best balance** |
| Hailo (11m) + BotSort | ~15-20 FPS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Best overall |

---

## 🎯 Recommended Approach

### **Option A: Fast Iteration (Start Here)**
1. ✅ Use current YOLO11n Hailo model
2. Add ByteTrack tracking (no retraining needed)
3. Evaluate if tracking improves results enough

### **Option B: Full Pipeline (If more accuracy needed)**
1. Train YOLO11m on custom dataset (Roboflow)
2. Test on CPU to verify accuracy improvement
3. Compile to Hailo HEF
4. Add ByteTrack/BotSort
5. Deploy best configuration

---

## 📝 Current Status

- ✅ YOLO11n compiled for Hailo (working)
- ✅ Hailo inference working (21ms/frame)
- ✅ 110k+ detections on test video
- ⏳ Need: Custom training data
- ⏳ Need: ByteTrack/BotSort integration
- ⏳ Need: YOLO11m training & compilation

---

## 🚀 Next Immediate Steps

1. **Do you have annotated training data ready?**
   - If YES → Start training YOLO11m
   - If NO → Annotate on Roboflow first

2. **Which tracking algorithm?**
   - ByteTrack (faster, simpler)
   - BotSort (more accurate, slower)
   - Both for comparison?

3. **Training location?**
   - Local GPU
   - Google Colab
   - Cloud GPU (Vast.ai/Lambda)

---

## 💾 Resources Needed

- **Training data:** 500+ annotated bee images
- **GPU:** For training (optional for inference)
- **Time:** 3-5 hours training + 30 min compilation
- **Storage:** ~2GB for training outputs

---

**Ready to start? Let me know which phase to begin with!** 🚀
