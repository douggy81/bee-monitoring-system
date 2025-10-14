# 🎯 Active Scripts Inventory

**Date:** October 13, 2025  
**Purpose:** Track which scripts are ACTIVELY USED vs archived

---

## ✅ **ACTIVE SCRIPTS (Production)**

These scripts are currently used and maintained:

### **1. Video Processing (Core)**
```
scripts/process_video_with_health_metrics.py
├─ Purpose: Detection with 5-sec rolling health metrics
├─ Backends: Hailo (fast) or CPU (accurate)
├─ Output: Video with health overlay + metadata JSON
├─ Status: ✅ PRODUCTION READY
└─ Used for: Real-time health monitoring, detection-only processing
```

### **2. ByteTrack Processing**
```
scripts/process_bee_bytetrack_with_metadata.py
├─ Purpose: Detection + tracking with health metrics
├─ Backends: CPU only (Hailo has segfault issue)
├─ Output: Video with tracks + metadata JSON
├─ Status: ⚠️  ACTIVE - Requires NumPy >= 1.25.2
├─ Fixed: Overlay flickering, detection fallback
└─ Used for: Tracking analysis, individual bee paths
```

### **3. FPS Conversion Utility**
```
scripts/convert_video_fps.py
├─ Purpose: Convert video framerate (e.g., 120fps → 30fps)
├─ Output: Converted video file
├─ Status: ✅ UTILITY
└─ Used for: Preprocessing videos before detection
```

### **4. Smart Processing Wrapper** (NEW!)
```
scripts/smart_process.sh
├─ Purpose: Auto-manages NumPy versions for ByteTrack
├─ Handles: Upgrade NumPy → Run ByteTrack → Downgrade NumPy
├─ Status: 🆕 NEW - Testing
└─ Used for: Seamless ByteTrack processing
```

---

## 🗄️ **ARCHIVED SCRIPTS (Not Currently Used)**

These scripts are superseded or no longer maintained:

### **Detection Scripts (Superseded)**
```
scripts/archived/
├─ process_video_clean.py           → Replaced by process_video_with_health_metrics.py
├─ process_bee_video_stable.py      → Old version
├─ process_bee_video_local.py       → Old version
├─ bee_hive_monitor.py              → Legacy monitoring script
└─ ... (15+ other old scripts)
```

**Why archived:**
- Superseded by health metrics version
- Missing features (rolling averages, health scoring)
- No longer maintained

### **Tracking Scripts (Superseded)**
```
scripts/archived/
├─ bee_hive_bytetrack.py            → Old ByteTrack implementation
├─ bee_hive_botsort.py              → Experimental tracker
└─ bee_simple_tracker.py            → Basic tracker (no persistence)
```

**Why archived:**
- Missing health metrics integration
- No metadata export
- ByteTrack script has all features

---

## 📁 **File Structure**

### **Current Active Structure:**
```
bee-monitoring-system/
├── scripts/
│   ├── smart_process.sh                           🆕 NEW - Wrapper
│   ├── process_video_with_health_metrics.py       ✅ ACTIVE - Detection
│   ├── process_bee_bytetrack_with_metadata.py     ✅ ACTIVE - Tracking
│   ├── convert_video_fps.py                       ✅ ACTIVE - Utility
│   └── archived/                                   📦 OLD SCRIPTS
│       ├── process_video_clean.py
│       ├── bee_hive_monitor.py
│       └── ... (20+ deprecated scripts)
│
├── ai/
│   ├── cpu_backend.py                             ✅ ACTIVE
│   ├── hailo_backend.py                           ✅ ACTIVE
│   └── ... (camera, utils)
│
├── tracking/                                       🆕 NEW
│   ├── __init__.py
│   ├── byte_tracker.py                            ✅ ACTIVE
│   ├── basetrack.py
│   ├── kalman_filter.py
│   ├── matching.py
│   └── utils.py
│
└── docs/                                           📖 DOCUMENTATION
    ├── BYTETRACK_FIX_SUMMARY.md                   ✅ Current
    ├── OVERLAY_FIX_AND_BYTETRACK_STATUS.md        ✅ Current
    ├── MODEL_ORGANIZATION_AUDIT.md                ✅ Current
    └── ... (deployment guides, roadmaps)
```

---

## 🔄 **Processing Workflows**

### **Workflow 1: Detection Only (Fast)**
```bash
# For real-time health monitoring
python3 scripts/process_video_with_health_metrics.py \
  input.mp4 output.mp4 \
  --backend hailo \
  --fps 30
```

**Use when:**
- Need fast processing
- Don't need individual tracking
- Health metrics only
- Hailo backend available

---

### **Workflow 2: Tracking + Detection (Accurate)**
```bash
# For individual bee tracking
./scripts/smart_process.sh bytetrack \
  input.mp4 output.mp4 \
  --backend cpu \
  --fps 120
```

**Use when:**
- Need persistent track IDs
- Individual bee analysis
- Path visualization
- Full health + tracking metrics

---

### **Workflow 3: High FPS → Standard FPS**
```bash
# Step 1: Convert 120fps → 30fps
python3 scripts/convert_video_fps.py \
  input_120fps.mp4 output_30fps.mp4 \
  --target-fps 30

# Step 2: Process with Hailo (fast)
python3 scripts/process_video_with_health_metrics.py \
  output_30fps.mp4 final.mp4 \
  --backend hailo
```

**Use when:**
- Video is too high FPS for real-time
- Want to use Hailo backend
- Don't need full 120fps analysis

---

## 📊 **Output Files**

### **Detection Output:**
```
output/
├── video_detected.mp4                  # Video with bounding boxes + health overlay
├── video_detected_metadata.json        # Frame-by-frame detection data
└── video_detected_metadata_summary.json  # Aggregated statistics
```

### **ByteTrack Output:**
```
output/
├── video_tracked.mp4                   # Video with tracks + health overlay
├── video_tracked_metadata.json         # Frame-by-frame tracking data
└── video_tracked_metadata_summary.json   # Tracking + health statistics
```

---

## 🚨 **Critical Files - DO NOT DELETE**

### **Models:**
```
models/yolo11m/
├── yolo11m_bee_best.pt         # Source model (87.2% mAP)
├── yolo11m_bee_best.onnx       # CPU inference ✅ WORKS
└── yolo11m_bee_best.hef        # Hailo inference ✅ WORKS
```

### **Backends:**
```
ai/
├── cpu_backend.py              # ONNX Runtime inference
└── hailo_backend.py            # Hailo accelerator inference
```

### **Tracking:**
```
tracking/
└── (all files)                 # ByteTrack implementation
```

### **Active Scripts:**
```
scripts/
├── smart_process.sh
├── process_video_with_health_metrics.py
└── process_bee_bytetrack_with_metadata.py
```

---

## 📝 **Maintenance Notes**

### **When Adding New Scripts:**
1. Document purpose in this file
2. Mark status (🆕 NEW, ✅ ACTIVE, ⚠️ EXPERIMENTAL)
3. Explain when to use it

### **When Deprecating Scripts:**
1. Move to `scripts/archived/`
2. Update this document
3. Add deprecation note in script header

### **Version Control:**
- Git commit before major changes
- Tag releases (e.g., `v1.0-bytetrack-working`)
- Keep this document updated with each change

---

## 🎯 **Quick Reference**

**Need detection only?**
→ `process_video_with_health_metrics.py` + `--backend hailo`

**Need tracking?**
→ `smart_process.sh bytetrack` + `--backend cpu`

**High FPS video?**
→ `convert_video_fps.py` first, then process

**Hailo not working?**
→ Use `--backend cpu` instead

**ByteTrack not working?**
→ Run `smart_process.sh bytetrack` (handles NumPy automatically)

---

**Last Updated:** October 13, 2025  
**Maintained By:** Cascade AI + User  
**Status:** ✅ Current and accurate
