# 🗂️ Codebase Cleanup Summary

**Date:** October 12, 2025  
**Status:** ✅ Complete

---

## 📦 **Active Production Files**

### **Models** (`/opt/bee-monitoring/models/`)
- ✅ `yolo11m_bee_best.hef` (47 MB) - **ACTIVE YOLO11m model**

### **Backends** (`ai/`)
- ✅ `hailo_backend.py` - Main Hailo backend (v3, fixed buffer allocation)
- ✅ `cpu_backend.py` - CPU fallback (ONNX Runtime)
- ✅ `hailo_yolo_postprocess.py` - YOLO post-processing utilities
- ✅ `__init__.py`

### **Scripts** (`scripts/`)
- ✅ `process_video_clean.py` - Video processing with detections
- ✅ `process_bee_video_stable.py` - Stable processing pipeline
- ✅ `process_bee_video.py` - Main processing script
- ✅ `process_bee_video_local.py` - Local testing
- ✅ `bee_hive_bytetrack.py` - ByteTrack tracking
- ✅ `bee_hive_botsort.py` - BoT-SORT tracking
- ✅ `bee_hive_monitor.py` - Monitoring utilities
- ✅ `train_yolo11m_bee.py` - Training script

### **Tests** (Root)
- ✅ `test_yolo11m_hef.py` - YOLO11m HEF test (NEW, keep)

### **Documentation**
- ✅ `YOLO11M_DEPLOYMENT_SUMMARY.md` - Deployment guide
- ✅ `YOLO11M_TRAINING_DEPLOYMENT_PLAN.md` - Training/deployment plan
- ✅ `COMPILE_TO_HEF.md` - Compilation instructions
- ✅ `CODEBASE_CLEANUP_SUMMARY.md` (this file)

---

## 📂 **Archived Files**

### **`_archive/old_tests/`** (Mac)
Moved old Hailo test files that are no longer needed:
- `test_gstreamer_minimal.py`
- `test_hailo_complete.py`
- `test_hailo_fresh_hef.py`
- `test_hailo_gstreamer.py`
- `test_hailo_pure_gst.py`
- `test_hailo_raw_outputs.py`
- `test_hailopython.py`

### **`_archive/old_scripts/`** (Mac)
Moved old processing/integration scripts:
- `process_full_bee_video.py` (replaced by `process_video_clean.py`)
- `hailo_inference_complete.py` (old inference script)
- `hailo_bee_detection_official.py` (old detection script)
- `hailo_python_module.py` (old module)
- `hardware_integration.py` (old integration script)
- `data_analytics_engine.py` (unused analytics)

### **`_archive/old_backends/`** (Mac)
Moved unused backend implementations:
- `hailo_backend_v2.py` (old version with issues)
- `hailo_gstreamer_backend.py` (GStreamer approach, unused)
- `degirum_backend.py` (cloud service, unused)

### **`ai/_archive/`** (Raspberry Pi)
Moved broken/old backends:
- `hailo_backend_old_broken.py` (buffer allocation issues)
- `hailo_backend_old.py` (previous version)
- `hailo_gstreamer_backend.py` (alternative approach)
- `degirum_backend.py` (cloud service)

---

## 🎬 **Output Files**

### **Processed Videos** (`output/`)
- ✅ `bee_YOLO11M_FULL.mp4` (125 MB) - **Full 30-second video with YOLO11m detections**
  - Resolution: 1184×666
  - FPS: 120
  - Duration: ~30 seconds
  - Model: YOLO11m (87.2% mAP)
  - Detections: ~32 bees per frame average

---

## 📊 **Directory Structure**

```
bee-monitoring-system/
├── ai/                           # Backend implementations
│   ├── hailo_backend.py          # ✅ ACTIVE (v3)
│   ├── cpu_backend.py            # ✅ ACTIVE
│   ├── hailo_yolo_postprocess.py # ✅ ACTIVE
│   └── __init__.py               # ✅ ACTIVE
│
├── scripts/                      # Processing scripts
│   ├── process_video_clean.py   # ✅ ACTIVE
│   ├── bee_hive_bytetrack.py    # ✅ ACTIVE
│   ├── bee_hive_botsort.py      # ✅ ACTIVE
│   └── train_yolo11m_bee.py     # ✅ ACTIVE
│
├── models/                       # Model files
│   └── yolo11m/
│       ├── yolo11m_bee_best.onnx # Source model
│       ├── yolo11m_bee_best.har  # Hailo intermediate
│       └── yolo11m_bee_best.hef  # Hailo executable
│
├── output/                       # Processed videos
│   └── bee_YOLO11M_FULL.mp4     # ✅ NEW
│
├── wsl_transfer/                 # Compilation tools
│   ├── compile_hailo.sh
│   ├── download_calibration_images.py
│   ├── prepare_calibration.py
│   └── RECALIBRATION_GUIDE.md
│
├── _archive/                     # Archived files
│   ├── old_tests/                # Old test scripts
│   ├── old_scripts/              # Old processing scripts
│   └── old_backends/             # Old backend implementations
│
├── test_yolo11m_hef.py          # ✅ ACTIVE test
│
└── *.md                          # Documentation
    ├── YOLO11M_DEPLOYMENT_SUMMARY.md
    ├── YOLO11M_TRAINING_DEPLOYMENT_PLAN.md
    ├── COMPILE_TO_HEF.md
    └── CODEBASE_CLEANUP_SUMMARY.md (this file)
```

---

## 🔄 **Backend Version History**

| Version | Status | Notes |
|---------|--------|-------|
| `hailo_backend.py` (original) | ❌ Archived | Buffer allocation issues |
| `hailo_backend_v2.py` | ❌ Archived | Partial fixes |
| **`hailo_backend_v3.py`** | ✅ **ACTIVE** | Fixed buffer allocation, correct callback |
| `hailo_gstreamer_backend.py` | ❌ Archived | Alternative approach |

**Active backend copied to:** `ai/hailo_backend.py` (all scripts import this)

---

## 🧹 **Cleanup Actions Taken**

### **Mac (Development):**
1. ✅ Created `_archive/` directory structure
2. ✅ Moved 7 old test files to `_archive/old_tests/`
3. ✅ Moved 6 old scripts to `_archive/old_scripts/`
4. ✅ Moved 3 old backends to `_archive/old_backends/`
5. ✅ Created `output/` directory for processed videos

### **Raspberry Pi (Production):**
1. ✅ Created `ai/_archive/` directory
2. ✅ Moved 4 old/broken backends to `ai/_archive/`
3. ✅ Activated `hailo_backend_v3.py` as main `hailo_backend.py`

---

## 📈 **Project Status**

### **✅ Complete:**
- YOLO11m model training (87.2% mAP50)
- ONNX → HEF compilation
- Hailo backend integration (v3)
- Full video processing
- Codebase cleanup

### **🎯 Next Steps:**
1. Add ByteTrack/BoT-SORT object tracking
2. Integrate with dashboard/API
3. Test live camera stream
4. Production deployment

---

## 🔍 **Key Files to Remember**

**For development:**
- `ai/hailo_backend_v3.py` - Source of truth for Hailo backend
- `scripts/process_video_clean.py` - Main video processing

**For deployment:**
- `/opt/bee-monitoring/models/yolo11m_bee_best.hef` - Production model
- `/opt/bee-monitoring/src/ai/hailo_backend.py` - Production backend

**For compilation:**
- `wsl_transfer/compile_hailo.sh` - Automated compilation
- `models/yolo11m/yolo11m_bee_best.onnx` - Source model

---

## 📝 **Notes**

- All archived files are preserved for reference
- Active files are clearly identified
- Backend v3 is the working version (buffer allocation fix)
- Full 30-second video successfully processed with YOLO11m
- Codebase is now clean and organized

---

**Last Updated:** October 12, 2025  
**Status:** ✅ Production Ready
