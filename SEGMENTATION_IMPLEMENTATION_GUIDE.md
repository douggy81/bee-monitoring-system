# 🎯 Bee Segmentation Implementation Guide

**Date:** October 14, 2025  
**Goal:** Add instance segmentation to get precise bee outlines instead of just bounding boxes

---

## 📋 What is Instance Segmentation?

**Detection (what you have now):**
- Bounding boxes around bees
- Format: `[x, y, width, height]`

**Segmentation (what you want):**
- Pixel-precise bee outlines/masks
- Better for: occlusion handling, size estimation, overlapping bees
- Format: Polygon points or pixel masks

---

## 🎯 Implementation Options

### **Option 1: Train YOLO11m-seg Model (Recommended)**

**Pros:**
- Best accuracy
- Native YOLO support
- Works with existing pipeline

**Steps:**

#### **1. Annotate Your Dataset with Polygons**

Use annotation tools to draw polygon outlines around bees:

**Tools:**
- **CVAT** (https://cvat.org) - Free, professional
- **Roboflow** (https://roboflow.com) - Easy, includes auto-annotation
- **Label Studio** (https://labelstud.io) - Open source

**What you need:**
- Take your existing 300 bee images
- Draw polygons around each bee (not boxes)
- Export in YOLO segmentation format

**Example annotation:**
```
# Instead of: class x_center y_center width height
0 0.5 0.5 0.1 0.1

# Segmentation format: class x1 y1 x2 y2 x3 y3 ...
0 0.45 0.42 0.52 0.43 0.54 0.48 0.50 0.55 0.46 0.54 ...
```

#### **2. Update Dataset YAML**

```yaml
# bee_seg.yaml
path: /path/to/dataset
train: images/train
val: images/val

names:
  0: bee

# Add task specification
task: segment  # This tells YOLO it's segmentation
```

#### **3. Train YOLO11m-seg Model**

```python
from ultralytics import YOLO

# Load segmentation model (not detection)
model = YOLO('yolo11m-seg.pt')

# Train
results = model.train(
    data='bee_seg.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    device=0,
    name='yolo11m_bee_seg'
)

# Export
model.export(format='onnx')
```

**Training time:** 
- Colab T4 GPU: ~3-4 hours
- Local GPU: Varies

#### **4. Use in ByteTrack Pipeline**

The segmentation model outputs are compatible with supervision:

```python
# Detection model
results = model(frame)
detections = sv.Detections.from_ultralytics(results)
# detections.mask will be None

# Segmentation model  
results_seg = model_seg(frame)
detections_seg = sv.Detections.from_ultralytics(results_seg)
# detections_seg.mask contains pixel masks! ✅
```

Add mask visualization:

```python
# In processing loop
mask_annotator = sv.MaskAnnotator(opacity=0.5)
frame = mask_annotator.annotate(scene=frame, detections=detections_seg)
```

---

### **Option 2: SAM (Segment Anything Model) Post-Processing**

**Pros:**
- No need to re-annotate dataset
- Uses existing detection boxes
- Good for quick prototyping

**Cons:**
- Slower (two-stage process)
- Less accurate than trained model

**Implementation:**

```python
from segment_anything import sam_model_registry, SamPredictor
import supervision as sv

# Load SAM
sam = sam_model_registry["vit_h"](checkpoint="sam_vit_h.pth")
predictor = SamPredictor(sam)

# Process frame
# 1. Detect with YOLO
results = yolo_model(frame)
detections = sv.Detections.from_ultralytics(results)

# 2. Segment with SAM using detection boxes as prompts
predictor.set_image(frame)
masks = []
for box in detections.xyxy:
    mask, _, _ = predictor.predict(box=box, multimask_output=False)
    masks.append(mask)

detections.mask = np.array(masks)

# 3. Track with ByteTrack (works with masks!)
detections = byte_tracker.update_with_detections(detections)

# 4. Visualize
frame = mask_annotator.annotate(scene=frame, detections=detections)
```

---

### **Option 3: Box-to-Mask Approximation (Quick & Dirty)**

**Pros:**
- No training needed
- Instant

**Cons:**
- Not real segmentation
- Just approximate masks from boxes

```python
def boxes_to_masks(detections, frame_shape):
    """Convert bounding boxes to simple rectangular masks"""
    h, w = frame_shape[:2]
    masks = []
    
    for box in detections.xyxy:
        x1, y1, x2, y2 = box.astype(int)
        mask = np.zeros((h, w), dtype=bool)
        mask[y1:y2, x1:x2] = True
        masks.append(mask)
    
    return np.array(masks)

# Usage
detections.mask = boxes_to_masks(detections, frame.shape)
```

---

## 🎯 Recommendation

**For Production/Demo:**
1. **Start with Option 1** (Train YOLO11m-seg)
   - Best quality
   - Worth the annotation effort
   - ~1-2 days to annotate 300 images

**For Quick Testing:**
2. Use **Option 2** (SAM) to see if segmentation helps your use case
3. If valuable, invest in Option 1

**For Immediate Results:**
3. Use **Option 3** for rough masks (5 minutes to implement)

---

## 📊 Segmentation Benefits for Bee Monitoring

### **Why Add Segmentation?**

1. **Better Occlusion Handling**
   - Overlapping bees can be separated
   - More accurate counting in crowded areas

2. **Size/Health Analysis**
   - Pixel-accurate bee size
   - Detect abnormal bee shapes
   - Weight estimation

3. **Improved Tracking**
   - More accurate centroid calculation
   - Better re-identification

4. **Visual Quality**
   - Professional-looking masks
   - Better for demonstrations

### **When is Detection Enough?**

If you only need:
- ✅ Counting (IN/OUT)
- ✅ Track persistence
- ✅ Speed/movement patterns
- ✅ General activity levels

Then **bounding boxes are sufficient** - segmentation adds overhead.

---

## 🚀 Quick Start: Annotation Workflow

### **Using Roboflow (Easiest)**

1. Create free account: https://roboflow.com
2. Upload your 300 bee images
3. Use "Smart Polygon" tool (AI-assisted)
4. Export as "YOLO v11 Segmentation"
5. Download and train

**Time estimate:** 2-4 hours for 300 images

### **Using CVAT (Free, Professional)**

1. Install locally or use cvat.ai
2. Create segmentation task
3. Use polygon tool
4. Export as "YOLO 1.1" with masks
5. Convert and train

**Time estimate:** 3-5 hours for 300 images

---

## 📝 Next Steps

1. **Decide:** Do you need segmentation for your demo?
2. **Choose:** Pick annotation tool (Roboflow recommended)
3. **Annotate:** Start with 50 images to test
4. **Train:** Use Colab notebook for seg model
5. **Test:** Compare detection vs segmentation results
6. **Scale:** If good, annotate remaining images

---

## 💡 My Recommendation

**For your demonstration:**
- Stick with **detection + ByteTrack** (what you have now)
- It's working perfectly
- Segmentation is overkill for entry/exit counting

**Add segmentation later if you need:**
- Bee size analysis
- Health monitoring
- Academic/research requirements
- Visual wow-factor for presentations

**Your current setup (YOLO11m + ByteTrack) is production-ready!** 🐝✅
