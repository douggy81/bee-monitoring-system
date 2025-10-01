# YOLO Model Pipeline: Training → Deployment

Complete pipeline for training, converting, and deploying YOLO models on Raspberry Pi AI HAT+ (Hailo-8L).

## Pipeline Overview

```
Custom Training → PyTorch (.pt) → ONNX (.onnx) → Hailo HEF (.hef) → Deployment
                       ↓              ↓              ↓
                   Ultralytics    Standard      Hailo-8L      Raspberry Pi
                                  Format      Optimized       AI HAT+
```

## Step 1: Model Training (Optional)

### Using Ultralytics YOLO11

```python
from ultralytics import YOLO

# Start with pretrained YOLO11n
model = YOLO('yolo11n.pt')

# Train on custom bee dataset
results = model.train(
    data='bee_dataset.yaml',  # Your custom dataset config
    epochs=100,
    imgsz=640,
    batch=16,
    name='yolo11n_bees'
)

# Save trained model
model.save('yolo11n_bees.pt')
```

### Dataset Format (YOLO)

```yaml
# bee_dataset.yaml
path: /path/to/bee/dataset
train: images/train
val: images/val

# Classes
names:
  0: bee
  1: queen
  2: drone
  3: pollen
```

## Step 2: PT → ONNX Conversion

### Using Our Script (Automated)

```bash
# For pretrained YOLO11n
python3 scripts/download_yolov11n.py

# For custom trained model
python3 scripts/download_yolov11n.py --model /path/to/yolo11n_bees.pt
```

### Manual Conversion

```python
from ultralytics import YOLO

# Load your model
model = YOLO('yolo11n_bees.pt')

# Export to ONNX
model.export(
    format='onnx',
    imgsz=640,
    simplify=True,
    opset=12  # Compatible with Hailo
)
```

**Output**: `yolo11n_bees.onnx`

## Step 3: ONNX → HEF Conversion

### Using Our Script

```bash
python3 scripts/convert_yolo11n_to_hef.py
```

### Method 1: Docker (Recommended for Mac/Windows)

**Prerequisites**:
1. Install Docker Desktop
2. Register at https://hailo.ai/developer-zone/
3. Get access to Hailo Dataflow Compiler Docker image

```bash
# Pull Hailo DFC image (requires registration)
docker pull hailo/dataflow-compiler:latest

# Parse ONNX
docker run --rm -v $(pwd)/api/models:/workspace \
  hailo/dataflow-compiler:latest \
  hailo parser onnx \
  --input-model-path /workspace/yolo11n.onnx \
  --output-model-script /workspace/yolo11n_model_script.py \
  --net-name yolo11n

# Compile to HEF
docker run --rm -v $(pwd)/api/models:/workspace \
  hailo/dataflow-compiler:latest \
  hailo compiler \
  --model-script-path /workspace/yolo11n_model_script.py \
  --hw-arch hailo8l \
  --output-path /workspace/yolo11n.hef \
  --batch-size 1
```

### Method 2: Hailo Developer Zone (Cloud)

1. Go to https://hailo.ai/developer-zone/
2. Upload your ONNX model
3. Select target: **Hailo-8L** (13 TOPS)
4. Configure:
   - Input: 640x640
   - Batch: 1
   - Optimization: Standard
5. Download compiled HEF

### Method 3: Native Compilation (Linux x86 only)

```bash
# Install Hailo Dataflow Compiler
# Download from https://hailo.ai/developer-zone/

# Parse
hailo parser onnx \
  --input-model-path api/models/yolo11n.onnx \
  --output-model-script api/models/yolo11n_model_script.py \
  --net-name yolo11n

# Compile
hailo compiler \
  --model-script-path api/models/yolo11n_model_script.py \
  --hw-arch hailo8l \
  --output-path api/models/yolo11n.hef \
  --batch-size 1
```

**Output**: `yolo11n.hef` (~10-30 MB, optimized for Hailo-8L)

## Step 4: Deploy to Raspberry Pi

```bash
# Copy HEF to Pi
scp api/models/yolo11n.hef digital4ai@192.168.68.66:/home/digital4ai/

# SSH to Pi
ssh digital4ai@192.168.68.66

# Install HEF
sudo install -o bee-monitor -g bee-monitor -m 0644 \
  ~/yolo11n.hef /opt/bee-monitoring/src/api/models/

# Set environment variable
sudo systemctl edit bee-api
# Add:
# [Service]
# Environment="HAILO_HEF=/opt/bee-monitoring/src/api/models/yolo11n.hef"

# Restart service
sudo systemctl restart bee-api

# Verify
curl http://localhost/api/bee/ai/status | jq
```

## Step 5: Test & Benchmark

```bash
# Test Hailo backend
curl "http://192.168.68.66/api/bee/camera/stream?ai=1&ai_backend=hailo"

# Benchmark
python3 scripts/benchmark_backends.py
```

### Expected Performance

| Backend | FPS (640x640) | Power | Latency |
|---------|---------------|-------|---------|
| CPU (ONNX) | 5-10 FPS | High | ~100-200ms |
| Hailo-8L | 30-60 FPS | Low | ~16-33ms |

## Model Update Workflow

### For Pretrained Models

```bash
# 1. Download latest YOLO11n
python3 scripts/download_yolov11n.py

# 2. Convert to HEF
python3 scripts/convert_yolo11n_to_hef.py

# 3. Deploy
scp api/models/yolo11n.hef digital4ai@192.168.68.66:~/
ssh digital4ai@192.168.68.66 'sudo install -o bee-monitor -g bee-monitor -m 0644 ~/yolo11n.hef /opt/bee-monitoring/src/api/models/ && sudo systemctl restart bee-api'
```

### For Custom Trained Models

```bash
# 1. Train model
python3 train_custom_yolo.py

# 2. Export to ONNX
python3 -c "from ultralytics import YOLO; YOLO('runs/train/exp/weights/best.pt').export(format='onnx')"

# 3. Move ONNX
mv runs/train/exp/weights/best.onnx api/models/yolo11n_custom.onnx

# 4. Convert to HEF
python3 scripts/convert_yolo11n_to_hef.py  # Update script to use yolo11n_custom.onnx

# 5. Deploy
scp api/models/yolo11n_custom.hef digital4ai@192.168.68.66:~/
```

## Troubleshooting

### ONNX Export Issues

```python
# If export fails, try different opset
model.export(format='onnx', opset=11)  # or 13

# Or with dynamic shapes disabled
model.export(format='onnx', dynamic=False)
```

### HEF Compilation Issues

- **Error: Unsupported op**: Some ONNX ops may not be supported by Hailo
  - Solution: Simplify model or use supported YOLO variant
  
- **Error: Calibration required**: Some models need calibration dataset
  - Solution: Provide representative images for quantization

### Deployment Issues

- **HEF not loading**: Check file permissions and path
- **Low FPS**: Verify HEF is being used (not CPU fallback)
- **Wrong detections**: Ensure preprocessing matches training

## References

- [Ultralytics YOLO11 Docs](https://docs.ultralytics.com/)
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [ONNX Documentation](https://onnx.ai/)
