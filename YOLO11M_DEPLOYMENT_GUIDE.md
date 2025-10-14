# 🐝 YOLO11m Bee Detection - Deployment Guide

## ✅ Training Complete!

**Model Performance:**
- **mAP50:** 87.2% (Excellent!)
- **mAP50-95:** 54.0%
- **Training Time:** 2.2 hours on Google Colab T4 GPU

**Per-Class Results:**
- **Bee Detection:** 91.8% mAP50, 92% Recall
- **Pollen Detection:** 82.7% mAP50, 74.8% Recall

---

## 📦 Extracted Files

Location: `/Users/davidgassier/digital4ai/bee-monitoring-system/models/yolo11m/`

```
✅ yolo11m_bee_best.pt     (39 MB)  - PyTorch model
✅ yolo11m_bee_best.onnx   (77 MB)  - ONNX for Hailo compilation
✅ training_results.csv    (18 KB)  - Training metrics
```

---

## 🎯 Next Steps: Compile for Hailo-8L

### Step 1: Transfer ONNX to WSL

From your Mac, copy the ONNX model to WSL:

```bash
# Get your WSL IP (run in WSL)
ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1

# Transfer from Mac
scp /Users/davidgassier/digital4ai/bee-monitoring-system/models/yolo11m/yolo11m_bee_best.onnx \
    your-wsl-user@YOUR_WSL_IP:/path/to/hailo-dfc/models/
```

Or use Windows file system:

```bash
# From Mac, copy to Windows
# Then in WSL:
cp /mnt/c/Users/YourUser/Downloads/yolo11m_bee_best.onnx ~/hailo-dfc/models/
```

---

### Step 2: Compile with Hailo DFC (in WSL)

```bash
cd ~/hailo-dfc

# Create compilation config
cat > yolo11m_bee_config.yaml << 'EOF'
name: yolo11m_bee_detection
model_optimization_config:
  calibration:
    batch_size: 8
  compression:
    level: 2
normalization:
  mean: [0.0, 0.0, 0.0]
  std: [255.0, 255.0, 255.0]
input_resize:
  enabled: true
  height: 640
  width: 640
EOF

# Compile to HEF
hailo compiler \
    --input yolo11m_bee_best.onnx \
    --output yolo11m_bee.hef \
    --config yolo11m_bee_config.yaml \
    --optimization-level 2 \
    --hw-arch hailo8l \
    --allocator-script-filename allocator.py
```

**Expected compilation time:** 10-30 minutes

---

### Step 3: Validate HEF Model

```bash
# Check HEF info
hailo model-zoo info yolo11m_bee.hef

# Test inference (if you have test images)
hailo run yolo11m_bee.hef --input test_image.jpg
```

---

### Step 4: Deploy to Raspberry Pi

```bash
# From WSL, transfer to RPi
scp yolo11m_bee.hef pi@raspberrypi.local:/opt/bee-monitoring/models/

# SSH to RPi and test
ssh pi@raspberrypi.local

# On RPi
cd /opt/bee-monitoring
python3 scripts/test_hailo_model.py --model models/yolo11m_bee.hef
```

---

### Step 5: Update Detection Service

On Raspberry Pi, update the model path:

```bash
# Edit detection config
sudo nano /opt/bee-monitoring/config/detection.yaml

# Update model path:
model:
  path: /opt/bee-monitoring/models/yolo11m_bee.hef
  type: hailo
  size: 640
  confidence: 0.25  # Adjust based on testing
  iou: 0.6
  classes:
    - bee
    - pollen

# Restart detection service
sudo systemctl restart bee-detection
```

---

### Step 6: Test & Optimize

```bash
# Monitor detection performance
sudo journalctl -u bee-detection -f

# Test with live camera
curl http://raspberrypi.local/api/detect/start

# Check FPS and accuracy
curl http://raspberrypi.local/api/metrics
```

---

## 📊 Performance Comparison

| Model | Size | mAP50 | FPS (Hailo) | Training Time |
|-------|------|-------|-------------|---------------|
| YOLO11n | 6MB | 65% | ~60 FPS | 1 hour |
| **YOLO11m** | **77MB** | **87.2%** | **~30-40 FPS** | **2.2 hours** |
| YOLO11l | 150MB | ~90% | ~20 FPS | 4-6 hours |

**✅ YOLO11m is the sweet spot for Raspberry Pi + Hailo-8L!**

---

## 🔧 Troubleshooting

### Issue: Low FPS on RPi
**Solution:** Adjust batch size or enable async processing
```python
# In detection service
detector = HailoDetector(
    model_path="yolo11m_bee.hef",
    batch_size=4,  # Try 2, 4, or 8
    async_mode=True
)
```

### Issue: Too many false positives
**Solution:** Increase confidence threshold
```yaml
# In config/detection.yaml
confidence: 0.35  # Increase from 0.25
```

### Issue: Missing small bees
**Solution:** Lower confidence or use image preprocessing
```yaml
confidence: 0.20  # Lower threshold
preprocessing:
  sharpen: true
  contrast: 1.2
```

---

## 🚀 Next Enhancement: Tracking

Add ByteTrack or BoT-SORT for multi-object tracking:

```bash
# Install tracking library
pip3 install boxmot

# Update detection service
python3 scripts/add_tracking.py --tracker bytetrack
```

---

## 📈 Model Metrics Details

**Training Configuration:**
- Dataset: BeeMasterV2-1 (1,180 train, 346 val images)
- Epochs: 150 (early stopping at best performance)
- Batch size: 8
- Image size: 640x640
- GPU: Tesla T4 (Google Colab)
- Augmentation: HSV, flip, scale, translate, mosaic

**Final Metrics:**
- Precision: 85.1%
- Recall: 83.4%
- mAP50: 87.2%
- mAP50-95: 54.0%
- Inference speed: 9.0ms on T4 GPU

---

## ✅ Summary

1. ✅ Model trained successfully on Google Colab
2. ✅ ONNX exported for Hailo compilation
3. ⏳ Next: Compile to HEF in WSL
4. ⏳ Deploy to Raspberry Pi
5. ⏳ Test and optimize

**You're ready to compile for Hailo! 🚀**
