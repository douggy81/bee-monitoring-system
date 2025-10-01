# Raspberry Pi AI HAT+ (Hailo-8L) Implementation Guide

## Hardware Detected ✅
- **Device**: Hailo-8L (13 TOPS)
- **Firmware**: 4.20.0
- **HailoRT**: 4.20.0
- **HailoPlatform Python**: 4.20.0 installed

## Implementation Steps

### 1. Get YOLO11n HEF Model

**Option A: Use Pre-compiled Model from Hailo Model Zoo**
```bash
# Check if Hailo Model Zoo has YOLO11n
# https://github.com/hailo-ai/hailo_model_zoo
```

**Option B: Compile ONNX to HEF** (Requires Hailo Dataflow Compiler)
```bash
# The Hailo Dataflow Compiler typically runs on x86 Linux, not on Pi
# You may need to:
# 1. Use Hailo's cloud compilation service
# 2. Install compiler on a Linux workstation
# 3. Use pre-compiled YOLOv8n HEF (very similar to YOLO11n)
```

**Option C: Use YOLOv8n HEF** (Quick Start)
```bash
# Download pre-compiled YOLOv8n HEF from Hailo Model Zoo
cd /opt/bee-monitoring/src/api/models
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov8n.hef
```

### 2. Implement HailoRT Python Inference

The implementation requires:

#### **A. HEF Loading**
```python
from hailo_platform import HEF, Device, VDevice, InferVStreams

# Load HEF
hef = HEF(hef_path)
devices = Device.scan()
vdevice = VDevice()
network_group = vdevice.configure(hef)[0]
```

#### **B. Input Preprocessing**
```python
# YOLO requires:
# 1. Letterbox resize to 640x640
# 2. Normalize to [0, 1] or specific range
# 3. BGR -> RGB
# 4. NHWC -> NCHW format
# 5. Data type conversion (uint8 or float32)
```

#### **C. Inference with VStreams**
```python
# Create input/output vstreams
with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
    # Send frame
    infer_pipeline.send(preprocessed_frame)
    # Get results
    output = infer_pipeline.recv()
```

#### **D. Output Postprocessing**
```python
# YOLO output format: [batch, 84, 8400]
# - 84 = 4 bbox coords + 80 class scores
# - 8400 = detection candidates
# 
# Need to:
# 1. Parse output tensor
# 2. Apply confidence threshold
# 3. Apply NMS (Non-Maximum Suppression)
# 4. Map class IDs to names (COCO dataset)
# 5. Scale bbox coordinates back to original image size
```

### 3. Integration Steps

1. **Update `hailo_backend.py`**:
   - Add HEF loading in `initialize()`
   - Implement preprocessing helpers
   - Implement `infer_full()` with real inference
   - Add postprocessing (NMS, bbox scaling)

2. **Set Environment Variable**:
   ```bash
   # Add to /etc/systemd/system/bee-api.service
   Environment="HAILO_HEF=/opt/bee-monitoring/src/api/models/yolov8n.hef"
   ```

3. **Update Backend Selection**:
   ```python
   # In api/routes/bee_monitoring.py
   # Change auto selection to prefer Hailo when ready
   if ai_backend_sel == 'auto':
       backend = _get_hailo_backend() or _get_cpu_backend()
   ```

### 4. Testing

```python
# Test Hailo backend directly
from ai.hailo_backend import HailoBackend
import cv2

backend = HailoBackend(hef_path="/path/to/yolov8n.hef")
if backend.initialize():
    frame = cv2.imread("test.jpg")
    detections = backend.infer_full(frame)
    print(f"Found {len(detections)} objects")
```

### 5. Benchmarking

Expected performance:
- **CPU (ONNX)**: ~5-10 FPS @ 640x640
- **Hailo-8L**: ~30-60 FPS @ 640x640 (3-6x faster)
- **Power**: Lower power consumption vs CPU

## Quick Start: Use Existing YOLOv8n HEF

Since YOLOv8n and YOLO11n are very similar architecturally, you can start with YOLOv8n HEF:

```bash
# SSH to Pi
ssh digital4ai@192.168.68.66

# Download YOLOv8n HEF (if available in Model Zoo)
cd /tmp
# Check Hailo Model Zoo for pre-compiled models
# Or use rpicam-apps integration examples

# For now, the fastest path is to:
# 1. Check /opt/hailo or system examples
# 2. Look for pre-installed HEF files
find / -name "*.hef" 2>/dev/null | grep -E "(yolo|detect)"
```

## References

- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [HailoRT Python API Docs](https://hailo.ai/developer-zone/documentation/hailort-v4-20-0/)
- [Raspberry Pi AI HAT+ Guide](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)
