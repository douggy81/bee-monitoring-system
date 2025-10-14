# 🔍 Model Organization Audit & Cleanup Plan

**Date:** October 13, 2025  
**Issue:** Multiple model versions scattered across directories causing confusion

---

## 📦 **Current Model Inventory**

### **On Raspberry Pi:**

#### `/opt/bee-monitoring/models/` (Project root models)
```
yolo11m_bee_best.hef        47M   ✅ TRAINED - Hailo format (87.2% mAP)
yolo11m_bee_best.onnx       77M   ❓ TRAINED - ONNX (BROKEN - detects 0 bees)
```

#### `/opt/bee-monitoring/models/yolo11m/` (Duplicate directory!)
```
yolo11m_bee_best.onnx       77M   ❓ DUPLICATE of above
```

#### `/opt/bee-monitoring/src/api/models/` (Old/legacy models)
```
yolo11n_bee.onnx            11M   ✅ OLD TRAINED - Works on CPU
yolo11n_bee_best--640x640_quant_hailort_multidevice_1.hef  11M  OLD
yolo11n_bee_v2--800x800_quant_hailort_multidevice_2.hef    11M  OLD
yolo11n_coco--640x640_quant_hailort_multidevice_1.hef      11M  COCO (not trained)
yolo11n.onnx                11M   ❌ COCO - Generic (not bee-specific)
```

### **On Mac (Development):**

#### `/Users/.../models/yolo11m/`
```
yolo11m_bee_best.hef        47M   ✅ TRAINED - Hailo format
yolo11m_bee_best.onnx       77M   ❓ TRAINED - ONNX (broken?)
yolo11m_bee_best.pt         39M   ✅ TRAINED - PyTorch source
```

---

## 🎯 **What's Working vs Broken**

### ✅ **WORKING:**
1. **`yolo11m_bee_best.hef`** (Hailo)
   - Location: `/opt/bee-monitoring/models/`
   - Backend: Hailo (hardware accelerated)
   - Status: ✅ Works great on Hailo
   - mAP: 87.2% (best accuracy)
   - Speed: Fast on Hailo

2. **`yolo11n_bee.onnx`** (Old CPU model)
   - Location: `/opt/bee-monitoring/src/api/models/`
   - Backend: CPU (ONNX Runtime)
   - Status: ✅ Works on CPU
   - mAP: ~65% (older, less accurate)
   - Speed: 3.8 FPS on Pi CPU

### ✅ **WORKING:**
3. **`yolo11m_bee_best.onnx`** (New CPU model)
   - Location: `/opt/bee-monitoring/models/`
   - Backend: CPU (ONNX Runtime)
   - Status: ✅ Works perfectly (33 avg bees/frame)
   - Note: Previous "0 detections" was due to ByteTrack script bug (fixed)

### ⚠️ **ISSUES:**
4. **Hailo backend segfaults** when used with ByteTrack script
   - Likely: Buffer allocation or threading issue
   - Needs: Investigation

---

## 🧹 **Reorganization Plan**

### **Phase 1: Clean Directory Structure**

#### **Proposed Structure:**
```
/opt/bee-monitoring/models/
├── production/              # Active production models
│   ├── yolo11m_bee_best.hef          # HAILO - Primary (87.2% mAP)
│   └── yolo11n_bee.onnx              # CPU fallback (65% mAP)
│
├── experimental/            # Models being tested
│   └── yolo11m_bee_best.onnx         # BROKEN - needs investigation
│
├── archived/                # Old/deprecated models
│   ├── yolo11n_bee_v2.hef
│   ├── yolo11n_bee_best.hef
│   └── yolo11n.onnx                  # COCO generic
│
└── source/                  # Source .pt files for re-export
    └── yolo11m_bee_best.pt
```

### **Phase 2: Backend Model Resolution**

#### **Update `hailo_backend.py`:**
```python
def _resolve_default_hef_path(self):
    # PRIORITY 1: Production YOLO11m
    production_hef = "/opt/bee-monitoring/models/production/yolo11m_bee_best.hef"
    if os.path.isfile(production_hef):
        return production_hef
    
    # PRIORITY 2: Fallback to archived models
    # ... (with clear comments)
```

#### **Update `cpu_backend.py`:**
```python
def _resolve_default_model_path(self):
    # PRIORITY 1: Production CPU model (working)
    production_onnx = "/opt/bee-monitoring/models/production/yolo11n_bee.onnx"
    if os.path.isfile(production_onnx):
        return production_onnx
    
    # PRIORITY 2: Experimental (may be broken)
    experimental_onnx = "/opt/bee-monitoring/models/experimental/yolo11m_bee_best.onnx"
    if os.path.isfile(experimental_onnx):
        logger.warning("Using experimental ONNX model - may not work correctly")
        return experimental_onnx
```

### **Phase 3: Model Testing Protocol**

Create: `/opt/bee-monitoring/scripts/test_model.py`
```python
"""
Test a model file to verify it works correctly.
Usage: python3 test_model.py --model <path> --backend <hailo|cpu>
"""
# Test detection on sample frames
# Verify output format
# Report mAP and FPS
```

### **Phase 4: Documentation**

Create: `/opt/bee-monitoring/models/README.md`
```markdown
# Bee Detection Models

## Production Models
- yolo11m_bee_best.hef - Use with Hailo backend (87.2% mAP)
- yolo11n_bee.onnx - Use with CPU backend (65% mAP)

## Model Selection Guide
- Hailo available? → Use yolo11m_bee_best.hef
- CPU only? → Use yolo11n_bee.onnx
- Need best accuracy? → Use yolo11m_bee_best.hef on Hailo
```

---

## ⚠️ **Known Issues to Fix**

### **Issue 1: YOLO11m ONNX Export**
**Problem:** `yolo11m_bee_best.onnx` detects 0 bees  
**Possible causes:**
1. Export preprocessing mismatch (BGR vs RGB, normalization)
2. Class ID mapping issue
3. Input size mismatch (640x640 vs 800x800)
4. NMS threshold too high

**Fix options:**
```bash
# Option A: Re-export from PyTorch with correct settings
yolo export model=yolo11m_bee_best.pt format=onnx imgsz=640 opset=12

# Option B: Debug current export
python3 scripts/debug_onnx_model.py yolo11m_bee_best.onnx
```

### **Issue 2: Hailo Segfault in ByteTrack**
**Problem:** Segmentation fault when using Hailo backend with ByteTrack  
**Possible causes:**
1. Buffer allocation issue (seen before)
2. Threading conflict with ByteTrack
3. Memory leak from repeated infer calls

**Fix options:**
- Test Hailo backend standalone (without ByteTrack)
- Add buffer pre-allocation
- Investigate threading locks

---

## 🚀 **Immediate Action Items**

### **Priority 1: Stabilize What Works**
1. ✅ Keep `yolo11m_bee_best.hef` for Hailo (working)
2. ✅ Keep `yolo11n_bee.onnx` for CPU (working)
3. 📝 Document which scripts use which models
4. 🧹 Move old models to `archived/`

### **Priority 2: Fix YOLO11m ONNX**
1. Debug why it detects 0 bees
2. Re-export from PyTorch if needed
3. Test on sample frames

### **Priority 3: Fix Hailo Segfault**
1. Test Hailo backend in isolation
2. Add better error handling
3. Check buffer allocation

---

## 📊 **Current Script → Model Mapping**

### **Detection Scripts:**
```
process_video_clean.py
├─ Backend: hailo → yolo11m_bee_best.hef ✅
└─ Backend: cpu → yolo11n_bee.onnx ✅ (fallback to wrong location)

process_video_with_health_metrics.py
├─ Backend: hailo → yolo11m_bee_best.hef ✅
└─ Backend: cpu → yolo11n_bee.onnx ✅
```

### **Tracking Scripts:**
```
process_bee_bytetrack_with_metadata.py
├─ Backend: hailo → yolo11m_bee_best.hef ❌ SEGFAULT
└─ Backend: cpu → yolo11m_bee_best.onnx ❌ DETECTS 0
                  → yolo11n_bee.onnx ✅ (should use this)
```

---

## ✅ **Next Steps**

**Immediate (today):**
1. Reorganize models into new directory structure
2. Update backend path resolution
3. Test detection scripts with both backends
4. Document model usage

**Short-term (this week):**
1. Debug YOLO11m ONNX export
2. Fix Hailo segfault in ByteTrack
3. Create model testing script

**Long-term:**
1. Retrain with more data if needed
2. Optimize Hailo model in Colab
3. Add model versioning system

---

**Status:** Ready to reorganize and stabilize 🎯
