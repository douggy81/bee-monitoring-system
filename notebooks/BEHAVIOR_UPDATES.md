# 🐝 Behavior Classification Updates

## New Features (v2)

### 1. ✅ **Stationary Classification**
**Problem:** No way to detect dead/stuck bees  
**Solution:** New "Stationary" behavior for bees that don't move

**Classification:**
- **Flying (FLY):** Fast movement (>3 px/frame @ 30fps) - **Cyan boxes**
- **Browsing (BRW):** Slow movement (0.5-3 px/frame) - **Green boxes**
- **Stationary (STA):** Almost no movement (<0.5 px/frame) - **Red boxes**
- **Removed:** Erratic (was causing confusion)

---

### 2. ✅ **Peak Behavior Tracking**
**Problem:** Flying bees turned into "browsing" when they landed  
**Solution:** Track peak behavior - once a bee flies fast, it stays labeled as "Flying"

```python
# Once flying, always flying
if max_speed > SPEED_THRESHOLD_FLYING:
    return 'flying'  # Even if bee slows down later
```

**Why:** Preserves the fact that a bee flew in/out, even after landing

---

### 3. ✅ **5-Second Rolling Averages for ALL Metrics**
**Problem:** Only bee count had rolling average  
**Solution:** All behavior counts now have 5-second rolling averages

**Displayed:**
- `BEES NOW: 12` (instant count)
- `5s AVG: 10.5` (bee count average)
- `Flying: 4.2` (5-second average)
- `Browsing: 5.8` (5-second average)
- `Stationary: 0.5` (5-second average)

---

### 4. ✅ **Pollen Counter**
**Current:** Simple incrementing counter (demo)  
**Future:** Replace with actual YOLO pollen detection model

**Display:** `POLLEN COUNT: 42`

**Note:** Currently simulates pollen detection. To make it real:
1. Train YOLO model to detect pollen on bees
2. Replace line 343-344 with actual detection logic

---

## Visual Changes

### Stats Panel (Expanded)
```
┌─────────────────────────────────┐
│ DIGITAL4.AI BYTETRACK           │
│ BEES NOW: 12                    │
│ 5s AVG: 10.5                    │
│                                  │
│ BEHAVIORS (5s AVG):              │
│   Flying: 4.2                   │
│   Browsing: 5.8                 │
│   Stationary: 0.5               │
│                                  │
│ POLLEN COUNT: 42                │
│ FRAME: 1250/3600                │
└─────────────────────────────────┘
```

### Bounding Box Colors
- **Cyan:** Flying bees (fast incoming/outgoing)
- **Green:** Browsing bees (slow on hive)
- **Red:** Stationary bees (dead/stuck/resting)
- **Gray:** Unknown (insufficient data)

### Labels
- `#107 FLY 0.79` - Bee #107, Flying, 79% confidence
- `#131 BRW 0.82` - Bee #131, Browsing, 82% confidence
- `#95 STA 0.85` - Bee #95, Stationary, 85% confidence

---

## Algorithm Details

### Speed Thresholds (FPS-Aware)
```python
fps_scale = 30.0 / fps  # Auto-scales to any frame rate

# At 30fps:
SPEED_THRESHOLD_FLYING = 3.0 px/frame   # Fast
SPEED_THRESHOLD_MOVING = 0.5 px/frame   # Minimum

# At 120fps (auto-scaled):
SPEED_THRESHOLD_FLYING = 0.75 px/frame  # Fast
SPEED_THRESHOLD_MOVING = 0.125 px/frame # Minimum
```

### Peak Behavior Logic
```python
# Track both current and peak behavior
current_behavior = classify_bee_behavior(...)
track_behaviors[bee_id] = current_behavior

# Peak behavior (persistent)
if current_behavior == 'flying':
    track_peak_behaviors[bee_id] = 'flying'  # Lock in
elif peak != 'flying' and current == 'browsing':
    track_peak_behaviors[bee_id] = 'browsing'
```

---

## Expected Results

### Behavior Distribution
After processing, you should see:
- **Flying:** 20-35% (bees that entered/left quickly)
- **Browsing:** 50-70% (bees walking on hive)
- **Stationary:** 5-15% (resting/dead bees)

### Console Output Example
```
Frame  900/3600 (25.0%) | Bees: 12 Avg:10.5 | 
FLY:4.2 BRW:5.8 STA:0.5 | Pollen:42 | 
GPU:15.2ms | FPS:45.3 | ETA:1.2min
```

---

## JSON Export Structure

```json
{
  "summary": {
    "total_unique_bees": 156,
    "behaviors": {
      "flying": 45,
      "browsing": 98,
      "stationary": 13,
      "unknown": 0
    },
    "pollen_count": 42
  },
  "tracks": {
    "107": {
      "behavior": "flying",
      "trajectory": [[x, y, frame], ...]
    }
  }
}
```

---

## Future Enhancements

### 1. Real Pollen Detection
- Train YOLO model on bee + pollen images
- Replace demo counter with actual detections
- Track which bees have pollen

### 2. Stationary Duration
- Track how long bees are stationary
- Alert if >30 seconds (likely dead)

### 3. Direction Tracking
- Classify as "incoming" vs "outgoing"
- Track hive entry/exit patterns

### 4. Heatmap
- Show where bees spend most time
- Identify popular landing zones

---

## Files Updated
- `bee_processing_FIXED.py` - Source with all changes
- `bee_processing_FIXED.ipynb` - Colab-ready notebook
- Generated automatically with `python3 convert_to_notebook.py`
