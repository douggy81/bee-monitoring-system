# 🎨 Overlay Fix & ByteTrack Status

**Date:** October 13, 2025  
**Status:** Overlay Fixed ✅ | ByteTrack Needs Alternative Solution ⚠️

---

## ✅ **Fixed: Flickering Overlay**

### **Problem:**
The health metrics overlay was flickering on/off because it was only drawn every 30 frames:
```python
# Before: Draw only when calculating
if frame_num % 30 == 0:
    # Calculate metrics
    # Draw overlay  ← Only visible on these frames!
```

### **Solution:**
Separated calculation from drawing:
```python
# Store last calculated values
last_health = None

# Calculate every 30 frames (performance)
if frame_num % 30 == 0:
    last_health = calculate_metrics()

# Draw on EVERY frame (no flicker!)
if last_health is not None:
    draw_overlay(last_health)
```

### **Changes Made:**
- **File:** `scripts/process_bee_bytetrack_with_metadata.py`
- **Lines 484-490:** Added storage variables for last calculated metrics
- **Lines 569-579:** Calculate and store metrics every 30 frames
- **Lines 581-635:** Draw overlay on ALL frames using stored values
- **Result:** Smooth, constant overlay display at bottom-left

---

## ⚠️ **ByteTrack Status: Not Fully Working**

### **Current Behavior:**
The tracking IDs you see are **frame-local** (reset every frame), not persistent across frames. This is because ByteTrack library is not actually installed.

### **Why ByteTrack Isn't Installed:**

#### **1. Dependency Conflict with Hailo**
- **ByteTrack requires:** NumPy >= 1.25.2, scipy
- **Hailo requires:** NumPy 1.23.3 (compiled against specific version)
- **Conflict:** Upgrading NumPy breaks Hailo inference
- **Previous attempt:** We tried upgrading NumPy and it broke Hailo

#### **2. Missing Dependencies:**
```python
from tracking.byte_tracker import BYTETracker, STrack
# ❌ ModuleNotFoundError: No module named 'tracking'
```

The script gracefully falls back to raw detections:
```python
try:
    from tracking.byte_tracker import BYTETracker
    BYTETRACK_AVAILABLE = True
except ImportError:
    print("⚠️  ByteTrack not available, using simple tracking")
    BYTETRACK_AVAILABLE = False
```

### **What You're Seeing:**
- ✅ **Bounding boxes:** Working perfectly (yolo11m detections)
- ✅ **Confidence scores:** Accurate
- ❌ **Track IDs:** Frame-local (not persistent)
- ❌ **Tracking paths:** Not drawn (no historical data)

---

## 🎯 **Solutions Going Forward**

### **Option 1: Simple Tracking (Without ByteTrack) ✅ RECOMMENDED**

Implement lightweight tracking without external dependencies:

```python
class SimpleTracker:
    def __init__(self, max_distance=50):
        self.tracks = {}  # {track_id: last_bbox}
        self.next_id = 0
        self.max_distance = max_distance
    
    def update(self, detections):
        """
        Match detections to existing tracks based on proximity
        detections: List of [x1, y1, x2, y2, score]
        """
        if not self.tracks:
            # First frame - create new tracks
            for det in detections:
                self.tracks[self.next_id] = {
                    'bbox': det[:4],
                    'score': det[4],
                    'age': 0
                }
                self.next_id += 1
            return list(self.tracks.items())
        
        # Match detections to existing tracks (IoU or distance-based)
        matched_tracks = []
        for det in detections:
            best_match = self._find_closest_track(det)
            if best_match is not None:
                self.tracks[best_match] = {
                    'bbox': det[:4],
                    'score': det[4],
                    'age': self.tracks[best_match]['age'] + 1
                }
                matched_tracks.append((best_match, self.tracks[best_match]))
            else:
                # New track
                self.tracks[self.next_id] = {
                    'bbox': det[:4],
                    'score': det[4],
                    'age': 0
                }
                matched_tracks.append((self.next_id, self.tracks[self.next_id]))
                self.next_id += 1
        
        # Remove old tracks (not seen in last N frames)
        self._cleanup_old_tracks()
        
        return matched_tracks
```

**Pros:**
- ✅ No dependency conflicts
- ✅ Works with existing Hailo setup
- ✅ Persistent track IDs
- ✅ Simple to implement

**Cons:**
- ⚠️ Less sophisticated than ByteTrack
- ⚠️ May lose tracks during occlusions

---

### **Option 2: Use Ultralytics Built-in Tracking**

Ultralytics YOLO has built-in tracking that doesn't conflict with dependencies:

```python
from ultralytics import YOLO

model = YOLO('yolo11m_bee_best.pt')
results = model.track(source='video.mp4', tracker='bytetrack.yaml')
```

**Pros:**
- ✅ Professional tracking built-in
- ✅ No extra dependencies
- ✅ Tracking paths included

**Cons:**
- ❌ Requires .pt model (not ONNX/HEF)
- ❌ Can't use with Hailo backend
- ❌ Slower on CPU

---

### **Option 3: Separate Environment for ByteTrack**

Create a dedicated Python venv for ByteTrack processing:

```bash
# Create separate environment
python3 -m venv /opt/bee-monitoring/bytetrack_env
source /opt/bee-monitoring/bytetrack_env/bin/activate

# Install ByteTrack dependencies
pip install numpy>=1.25.2 scipy lap

# Process videos
python3 scripts/process_with_bytetrack.py
```

**Pros:**
- ✅ Full ByteTrack functionality
- ✅ No conflicts with Hailo

**Cons:**
- ❌ More complex setup
- ❌ Need to switch environments
- ❌ Can't use Hailo backend in same process

---

### **Option 4: Accept Current Behavior**

Keep using frame-local IDs for now:

**Current Output:**
- Average bees per frame: ✅
- Detection accuracy: ✅
- Health metrics: ✅
- Track persistence: ❌ (IDs reset each frame)

**Good enough for:**
- Counting bees
- Health monitoring
- Activity analysis

**Not good for:**
- Individual bee tracking
- Path visualization
- Behavior analysis

---

## 📊 **Current Video Output**

### **What's Working:**
```
output/bee_120fps_bytetrack_FINAL.mp4
├─ ✅ Bounding boxes drawn correctly
├─ ✅ Confidence scores displayed
├─ ✅ Track IDs shown (frame-local)
├─ ✅ Health overlay (bottom-left, no flicker!)
├─ ✅ Metadata export (JSON)
└─ ✅ Health score calculation
```

### **What's Missing:**
```
❌ Persistent track IDs across frames
❌ Tracking paths/trails
❌ Individual bee trajectory analysis
❌ Re-identification after occlusion
```

---

## 🚀 **Recommended Action Plan**

### **Immediate (Today):**
1. ✅ Fixed overlay flickering
2. 🔲 **Decide:** Which tracking solution to implement?
   - **Simple Tracker** (fastest, no dependencies)
   - **Ultralytics Tracking** (best quality, CPU only)
   - **Accept frame-local IDs** (current state)

### **Short-term (This Week):**
- If choosing Simple Tracker:
  - Implement `SimpleTracker` class
  - Test with sample video
  - Deploy to Pi
- If choosing Ultralytics:
  - Create separate processing script
  - Test with .pt model
  - Compare with current results

### **Long-term:**
- Consider if persistent tracking is critical for your use case
- May not need ByteTrack if health metrics are primary goal
- Can always add later if behavior analysis becomes important

---

## 💡 **My Recommendation**

Given your use case (hive health monitoring), I recommend:

**Option 1: Simple Tracker Implementation**

**Why:**
- ✅ Gets you persistent IDs without complexity
- ✅ No dependency conflicts with Hailo
- ✅ Good enough for counting and health metrics
- ✅ Can be implemented quickly (~1 hour)
- ✅ Works with both CPU and Hailo backends

**Trade-off:**
- Won't track individual bees through complex occlusions
- But for aggregate health metrics, it's perfect!

---

## 📝 **Next Steps**

**Want me to:**
1. **Implement SimpleTracker?** (Quick, clean solution)
2. **Test current output with frame-local IDs?** (See if it's good enough)
3. **Create tracking comparison video?** (Show difference between methods)

**Your call!** 🐝
