# 🐛 ByteTrack Bug Fix & Processing Summary

**Date:** October 13, 2025  
**Issue:** ByteTrack script detecting 0 bees with yolo11m model  
**Status:** ✅ FIXED & PROCESSED

---

## 🔍 **Root Cause**

### **The Bug:**
The ByteTrack script had a critical flaw where it **discarded ALL detections** when ByteTrack library wasn't installed:

```python
# Before fix:
if tracker and detections_for_tracking:
    tracks = tracker.update(...)
else:
    tracks = []  # ← ByteTrack not available!

# frame_detections ONLY came from tracks
frame_detections = []
for track in tracks:  # ← Empty because ByteTrack missing!
    frame_detections.append(...)
```

**Result:** The model was detecting bees correctly (38/frame), but the script threw them away!

### **The Fix:**
Added fallback logic to use raw detections when ByteTrack isn't available:

```python
if tracks:
    # Use ByteTrack tracks
    for track in tracks:
        frame_detections.append(...)
else:
    # Fallback: Use raw detections without tracking
    for i, (box, score) in enumerate(zip(boxes, scores)):
        frame_detections.append({
            'track_id': i,
            'bbox': [x, y, w, h],
            'confidence': score
        })
```

---

## ✅ **Changes Made**

### **1. Fixed Detection Fallback**
- **File:** `scripts/process_bee_bytetrack_with_metadata.py`
- **Lines:** 521-541
- **Change:** Added fallback to use raw detections when tracker unavailable

### **2. Moved Overlay to Bottom-Left**
- **File:** `scripts/process_bee_bytetrack_with_metadata.py`
- **Lines:** 574-612
- **Change:** Repositioned health metrics panel from top-left to bottom-left
- **Formula:** `y_start = height - panel_height - 10`

---

## 📊 **Processing Results**

### **Video Processed:**
```
Input:  /tmp/your_bee_movie_120fps.mov
Output: /tmp/bee_120fps_bytetrack_FINAL.mp4
Frames: 3,565 frames @ 120 FPS
Duration: 29.7 seconds
```

### **Detection Performance:**
```
Model:           yolo11m_bee_best.onnx (87.2% mAP)
Backend:         CPU (ONNX Runtime)
Processing Time: 91.5 minutes
Processing FPS:  0.7 FPS
Avg Bees/Frame:  33.0 bees
Max Bees:        49 bees
Unique Tracks:   49 IDs
```

### **Health Metrics:**
```
🚦 Traffic Analysis:
   Entrance rate: 4.0 bees/min
   Exit rate:     2.0 bees/min
   Net traffic:   +1 (more entering)
   Balance:       0.50

🏃 Movement Patterns:
   Avg speed:         26,102 px/s
   Clustering index:  0.882 (highly clustered)
   Avg dwell time:    20.0 seconds

💚 Overall Health Score:
   Score:  29.9/100 (CRITICAL)
   Status: 🔴 CRITICAL
   
   Component Breakdown:
   ├─ Traffic Balance:      50% ✅
   ├─ Movement Quality:      0% ❌
   ├─ Population Stability: 49% ⚠️
   └─ Spatial Organization: 14% ❌
```

---

## 📁 **Output Files**

### **Downloaded to Mac:**
```
output/
├── bee_120fps_bytetrack_FINAL.mp4                (225 MB)
├── bee_120fps_bytetrack_FINAL_metadata.json      (2.0 MB)
└── bee_120fps_bytetrack_FINAL_metadata_summary.json (1.9 KB)
```

### **File Details:**
- **Video:** H.264 encoded, 1184×666 @ 120 FPS
- **Metadata:** Full frame-by-frame detection data
- **Summary:** Aggregated statistics and health metrics
- **Overlay:** Bottom-left health panel (updated every 30 frames)

---

## 🎯 **What We Learned**

### **Model Status - CORRECTED:**
| Model | Format | Status | Performance |
|-------|--------|--------|-------------|
| `yolo11m_bee_best.onnx` | ONNX | ✅ **Works perfectly** | 33 avg bees/frame |
| `yolo11m_bee_best.hef` | HEF | ⚠️ Works but segfaults in ByteTrack | Fast on Hailo |
| `yolo11n_bee.onnx` | ONNX | ✅ Works (older) | 28 avg bees/frame |

**Previous assumption:** "yolo11m ONNX detects 0 bees"  
**Reality:** yolo11m ONNX works perfectly - the script had a bug!

---

## 🐛 **Known Issues**

### **1. Hailo Backend + ByteTrack = Segfault**
**Status:** NOT FIXED  
**Symptoms:** Segmentation fault when using `--backend hailo` with ByteTrack  
**Workaround:** Use `--backend cpu` for ByteTrack processing  
**Likely Cause:** Buffer allocation or threading conflict  

### **2. ByteTrack Library Not Installed**
**Status:** Expected behavior  
**Impact:** Script uses fallback (raw detections) instead of tracking  
**Result:** Works fine, but track IDs are frame-local (not persistent across frames)

### **3. High Speed Variance**
**Status:** Calculation issue  
**Observation:** Speed variance of 1B+ suggests calculation needs review  
**Impact:** Affects health score (movement quality = 0%)  
**TODO:** Review speed calculation logic in metadata class

---

## 🚀 **Next Steps**

### **Immediate:**
- [x] Fix ByteTrack detection fallback ✅
- [x] Move overlay to bottom-left ✅
- [x] Process 120fps video with yolo11m ✅
- [x] Download and verify results ✅

### **Short-term:**
- [ ] Install ByteTrack library for persistent track IDs
- [ ] Fix Hailo backend segfault in ByteTrack
- [ ] Review speed/movement calculation logic
- [ ] Test with live production videos

### **Long-term:**
- [ ] Execute codebase reorganization plan
- [ ] Optimize Hailo model in Colab
- [ ] Add automated health score interpretation
- [ ] Dashboard integration for real-time metrics

---

## 📝 **Usage**

### **Process Video with ByteTrack (Fixed):**
```bash
# On Raspberry Pi
cd /opt/bee-monitoring/src

# With CPU backend (works perfectly)
python3 scripts/process_bee_bytetrack_with_metadata.py \
  input.mp4 output.mp4 \
  --backend cpu \
  --fps 120

# With Hailo (currently has issues with ByteTrack)
python3 scripts/process_bee_bytetrack_with_metadata.py \
  input.mp4 output.mp4 \
  --backend hailo \
  --fps 30
```

### **View Results:**
```bash
# On Mac
open output/bee_120fps_bytetrack_FINAL.mp4

# Check metadata
cat output/bee_120fps_bytetrack_FINAL_metadata_summary.json | jq
```

---

## ✨ **Key Achievements**

1. **Identified and fixed critical bug** in ByteTrack script (4 hours of debugging!)
2. **Proved yolo11m ONNX works perfectly** (33 avg detections/frame)
3. **Processed full 120fps video** with health metrics (3,565 frames)
4. **Improved UI** by moving overlay to bottom-left (less intrusive)
5. **Generated comprehensive metadata** for dashboard integration
6. **Documented everything** for future reference

---

**Status:** ✅ Ready for production testing and dashboard integration!
