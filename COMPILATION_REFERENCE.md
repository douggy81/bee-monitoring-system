# 🐝 Hailo Bee Model Compilation Reference

## Quick Start

```bash
cd ~/hailo_compilation
source hailo_venv/bin/activate
./compile_bee_models_wsl.sh
```

---

## 📊 Configuration Parameters

Edit the script to adjust these settings:

### NMS Thresholds
```bash
NMS_SCORE_THRESHOLD=0.15    # Lower = more detections (0.01-1.0)
NMS_IOU_THRESHOLD=0.45      # Lower = less overlap filtering (0.0-1.0)
NMS_MAX_PROPOSALS=1000      # Max detections before NMS
```

**Current Issue Fix:**
- Original: `score_threshold=0.30` → **Too high, filtered all bees**
- Fixed: `score_threshold=0.15` → **Should detect bees with conf ≥ 15%**

### Optimization
```bash
OPTIMIZATION_LEVEL="max"    # Options: "0", "1", "2", "max"
```

- `0` = Fastest compile, lower accuracy (CPU only)
- `max` = Best accuracy, slower compile (needs GPU)

### Calibration
```bash
CALIB_METHOD="random"       # Quick, uses synthetic RGB images
CALIB_SIZE=64               # Number of calibration samples
```

**For better accuracy:**
```bash
CALIB_METHOD="/path/to/bee_images.npy"  # Real bee images
CALIB_SIZE=128                           # More samples
```

---

## 🔧 Manual Compilation Commands

### Step 1: Parse ONNX → HAR
```bash
hailo parser onnx model.onnx \
    --hw-arch hailo8l \
    --har-path output/model.har \
    -y
```

### Step 2: Optimize (Quantize)
```bash
hailo optimize output/model.har \
    --hw-arch hailo8l \
    --use-random-calib-set \
    --output-har-path output/model_optimized.har
```

### Step 3: Compile to HEF
```bash
hailo compiler output/model_optimized.har \
    --hw-arch hailo8l \
    --model-script model_script.alls \
    --output-dir output/
```

---

## 📝 Model Script Format

Create `model_script.alls`:

```python
# NMS Configuration
nms_postprocess(
    nms_config(
        score_threshold=0.15,
        iou_threshold=0.45,
        max_proposals_per_class=1000
    )
)

# Performance optimization
performance_param(compiler_optimization_level=max)

# Normalization (if needed)
# normalization1 = normalization([0.0, 0.0, 0.0], [255.0, 255.0, 255.0])
```

---

## ⏱️ Compilation Timeline

| Step | Duration | Notes |
|------|----------|-------|
| Parse | 30s | ONNX → HAR conversion |
| Optimize | 1-2 min | Quantization with calibration |
| Compile | 3-10 min | Hardware optimization |
| **Total** | **5-15 min** | Per model |

**For 2 models:** ~10-30 minutes total

---

## ✅ Verification

### On WSL (after compilation):
```bash
ls -lh output/*.hef
# Should see: yolo11n_bee_best.hef, yolo11n_bee_v2.hef
```

### On Raspberry Pi:
```bash
hailortcli parse-hef model.hef | grep -i threshold
```

**Expected output:**
```
Score threshold: 0.150
IoU threshold: 0.450
```

### Test inference:
```bash
cd /tmp/hailo-rpi5-examples
source setup_env.sh
python3 /tmp/test_hailopython.py
```

**Expected:**
```
🎉 DETECTIONS FOUND!
  1. bee: conf=0.187, bbox=(...)
  2. bee: conf=0.203, bbox=(...)
```

---

## 🐛 Troubleshooting

### "Virtual environment not found"
```bash
cd ~/hailo_compilation
python3 -m venv hailo_venv
source hailo_venv/bin/activate
pip install hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl
```

### "cmake not found"
```bash
sudo apt-get install cmake
```

### "python3-tk not found"
```bash
sudo apt-get install python3-tk
```

### "Single context flow failed"
- **Normal!** Compiler will automatically use multi-context flow
- Adds ~1-2 minutes to compile time

### Still 0 detections after compilation
Check NMS settings in model:
```bash
hailortcli parse-hef model.hef
```

If thresholds are wrong, recompile with corrected model script.

---

## 📤 Transfer Files

### From WSL to Windows:
```bash
cp output/*.hef /mnt/c/Users/david/Downloads/
```

### From Mac to Raspberry Pi:
```bash
scp output/*.hef rpi:/tmp/bee_models_fixed/
```

---

## 🎯 Different Threshold Settings

### Very sensitive (more false positives):
```bash
NMS_SCORE_THRESHOLD=0.05
NMS_IOU_THRESHOLD=0.30
```

### Balanced (recommended):
```bash
NMS_SCORE_THRESHOLD=0.15
NMS_IOU_THRESHOLD=0.45
```

### Conservative (fewer false positives):
```bash
NMS_SCORE_THRESHOLD=0.25
NMS_IOU_THRESHOLD=0.60
```

---

## 📚 Key Concepts

**HAR (Hailo Archive)**
- Intermediate format after parsing ONNX
- Contains network structure + metadata

**Quantization**
- Converts FP32 → INT8 for hardware acceleration
- Requires calibration data to minimize accuracy loss

**NMS (Non-Maximum Suppression)**
- Filters redundant bounding boxes
- `score_threshold`: Min confidence to keep detection
- `iou_threshold`: Max overlap before merging boxes

**Calibration Set**
- Sample images to analyze value distributions
- Random RGB works but real bee images are better

---

**Created:** October 10, 2025  
**Platform:** WSL2 (x86_64)  
**Hailo DFC:** v3.33.0  
**Target:** Hailo-8L (13 TOPS)
