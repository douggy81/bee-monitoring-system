# Train Custom Bee Detection Model

Complete guide to train a YOLO11 model for bee detection using Roboflow datasets.

## Prerequisites

- ✅ Roboflow dataset with bounding boxes
- ✅ GPU (recommended) or Google Colab
- ✅ Python 3.8+
- ✅ Ultralytics YOLO11

## Training Pipeline

```
1. Download Dataset from Roboflow (YOLO format)
2. Train YOLO11n model on bee data
3. Export to ONNX format
4. Convert ONNX to HEF (Hailo format)
5. Deploy to Raspberry Pi
```

---

## Step 1: Download Roboflow Dataset

### Option A: Using Roboflow API

```python
from roboflow import Roboflow

# Initialize with your API key
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")

# Download dataset in YOLO format
project = rf.workspace("workspace-name").project("project-name")
dataset = project.version(1).download("yolov8")

print(f"Dataset downloaded to: {dataset.location}")
```

### Option B: Using Roboflow Export

1. Go to your Roboflow project
2. Click "Export" → Format: **YOLOv8**
3. Download the ZIP file
4. Extract to `datasets/bee-detection/`

### Expected Structure

```
datasets/bee-detection/
├── data.yaml           # Dataset config
├── train/
│   ├── images/
│   └── labels/        # YOLO format .txt files
├── valid/
│   ├── images/
│   └── labels/
└── test/              # Optional
    ├── images/
    └── labels/
```

---

## Step 2: Train YOLO11n Model

### Install Ultralytics

```bash
pip install ultralytics
```

### Training Script

Save as `train_bee_model.py`:

```python
from ultralytics import YOLO
import torch

# Check GPU availability
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

# Load YOLO11n model (nano - best for edge devices)
model = YOLO('yolo11n.pt')

# Train on bee dataset
results = model.train(
    data='datasets/bee-detection/data.yaml',
    epochs=100,              # Adjust based on dataset size
    imgsz=640,              # Image size (Hailo optimized)
    batch=16,               # Adjust based on GPU memory
    device=0,               # GPU device (0) or 'cpu'
    patience=20,            # Early stopping
    save=True,
    project='runs/bee-detection',
    name='yolo11n-bee',
    
    # Optimization for small objects (bees)
    close_mosaic=10,        # Disable mosaic for last N epochs
    amp=True,               # Automatic mixed precision
    
    # Data augmentation (adjust for your data)
    hsv_h=0.015,           # Hue augmentation
    hsv_s=0.7,             # Saturation augmentation
    hsv_v=0.4,             # Value augmentation
    degrees=0.0,           # Rotation (0 for top-down bee cams)
    translate=0.1,         # Translation
    scale=0.5,             # Scale augmentation
    fliplr=0.5,            # Horizontal flip probability
    flipud=0.0,            # Vertical flip (0 for bee landing)
    mosaic=1.0,            # Mosaic augmentation probability
)

# Validate
metrics = model.val()

print(f"\n✓ Training complete!")
print(f"Best model: {results.save_dir / 'weights' / 'best.pt'}")
print(f"mAP50: {metrics.box.map50:.3f}")
print(f"mAP50-95: {metrics.box.map:.3f}")
```

### Run Training

```bash
# On local machine with GPU
python train_bee_model.py

# Or on Google Colab (see Colab notebook below)
```

### Training Tips

**Small Dataset (< 500 images)**
- Use pretrained weights (YOLO11n.pt)
- More epochs (100-200)
- Strong augmentation

**Large Dataset (> 2000 images)**
- Can train from scratch
- Fewer epochs (50-100)
- Less augmentation

**For Bees Specifically**
- Disable vertical flip (bees always upright)
- Enable horizontal flip (symmetric)
- Lower rotation (±10° max)
- Focus on small object detection

---

## Step 3: Export to ONNX

After training completes:

```python
from ultralytics import YOLO

# Load best model
model = YOLO('runs/bee-detection/yolo11n-bee/weights/best.pt')

# Export to ONNX (optimized for Hailo)
model.export(
    format='onnx',
    imgsz=640,
    simplify=True,
    dynamic=False,          # Static shapes for Hailo
    opset=11,              # ONNX opset version
)

print("✓ ONNX model exported!")
print(f"Location: runs/bee-detection/yolo11n-bee/weights/best.onnx")
```

Or use CLI:

```bash
yolo export model=runs/bee-detection/yolo11n-bee/weights/best.pt format=onnx imgsz=640 simplify=True
```

---

## Step 4: Convert ONNX to HEF (Hailo Format)

### Prerequisites on Mac/Linux

```bash
# Install Hailo Dataflow Compiler (requires Docker)
docker pull hailo/hailo_sw_suite:latest
```

### Conversion Script

Save as `convert_bee_model_to_hef.sh`:

```bash
#!/bin/bash
# Convert trained bee model to Hailo HEF format

ONNX_MODEL="runs/bee-detection/yolo11n-bee/weights/best.onnx"
OUTPUT_HEF="api/models/yolo11n_bee_detection.hef"

# Run Hailo Dataflow Compiler in Docker
docker run --rm -it \
  -v $(pwd):/workspace \
  hailo/hailo_sw_suite:latest \
  hailo model optimize \
    --model-path /workspace/$ONNX_MODEL \
    --hw-arch hailo8l \
    --output-path /workspace/$OUTPUT_HEF \
    --performance \
    --calibration-dataset /workspace/datasets/bee-detection/valid/images

echo "✓ HEF model created: $OUTPUT_HEF"
```

### Run Conversion

```bash
chmod +x convert_bee_model_to_hef.sh
./convert_bee_model_to_hef.sh
```

### Alternative: Use Hailo Model Zoo

```bash
# Clone Hailo Model Zoo
git clone https://github.com/hailo-ai/hailo_model_zoo.git
cd hailo_model_zoo

# Convert YOLO ONNX to HEF
python hailo_model_zoo/main.py optimize \
  --model-path ../runs/bee-detection/yolo11n-bee/weights/best.onnx \
  --hw-arch hailo8l \
  --performance
```

---

## Step 5: Deploy to Raspberry Pi

### Update Labels File

Create `api/models/labels_bee_detection.json`:

```json
{
  "0": "bee"
}
```

Or if you have multiple classes:

```json
{
  "0": "bee",
  "1": "wasp",
  "2": "bumblebee"
}
```

### Update Model Metadata

Create `api/models/yolo11n_bee_detection.json`:

```json
{
  "ConfigVersion": 11,
  "Checksum": "AUTO_GENERATED",
  "DEVICE": [{
    "DeviceType": "HAILO8L",
    "RuntimeAgent": "HAILORT"
  }],
  "PRE_PROCESS": [{
    "InputN": 1,
    "InputH": 640,
    "InputW": 640,
    "InputC": 3,
    "InputQuantEn": true
  }],
  "MODEL_PARAMETERS": [{
    "ModelPath": "yolo11n_bee_detection.hef"
  }],
  "POST_PROCESS": [{
    "OutputPostprocessType": "DetectionYoloHailo",
    "OutputNumClasses": 1,
    "LabelsPath": "labels_bee_detection.json"
  }]
}
```

### Deploy to Pi

```bash
# Copy model files to Pi
scp api/models/yolo11n_bee_detection.hef \
    api/models/yolo11n_bee_detection.json \
    api/models/labels_bee_detection.json \
    rpi:/tmp/

# Install on Pi
ssh rpi "sudo mv /tmp/yolo11n_bee_detection.* /opt/bee-monitoring/src/api/models/ && \
         sudo mv /tmp/labels_bee_detection.json /opt/bee-monitoring/src/api/models/ && \
         sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/src/api/models/yolo11n_bee_detection.* && \
         sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/src/api/models/labels_bee_detection.json"
```

### Update Backend to Use New Model

Modify `ai/hailo_backend.py` to use the bee model:

```python
def _resolve_default_hef_path(self) -> Optional[str]:
    """Find default HEF file."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, os.pardir))
    models_dir = os.path.join(root, "api", "models")
    
    # Look for bee detection model first
    hef_candidates = [
        os.path.join(models_dir, "yolo11n_bee_detection.hef"),
        os.path.join(models_dir, "yolo11n_coco--640x640_quant_hailort_multidevice_1.hef"),
        os.path.join(models_dir, "yolo11n.hef"),
    ]
    
    for hef in hef_candidates:
        if os.path.isfile(hef):
            return hef
    return None
```

### Test Bee Detection

```bash
# Test with your bee video
curl "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&\
ai_backend=hailo&\
annotate=1" -o bee_detected.jpg

# View results
curl "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&\
ai_backend=hailo" | jq
```

---

## Google Colab Training (No GPU Needed!)

Use this Colab notebook to train without local GPU:

```python
# Colab Notebook: Train Bee Detection Model

# 1. Install Ultralytics
!pip install ultralytics roboflow

# 2. Download dataset
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("your-workspace").project("bee-detection")
dataset = project.version(1).download("yolov8")

# 3. Train YOLO11n
from ultralytics import YOLO
model = YOLO('yolo11n.pt')

results = model.train(
    data=f'{dataset.location}/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    device=0,
    project='bee-model'
)

# 4. Export to ONNX
model.export(format='onnx', imgsz=640, simplify=True)

# 5. Download trained model
from google.colab import files
files.download('bee-model/train/weights/best.pt')
files.download('bee-model/train/weights/best.onnx')
```

---

## Training Checklist

- [ ] Download Roboflow dataset (YOLO format)
- [ ] Install Ultralytics: `pip install ultralytics`
- [ ] Train model: `python train_bee_model.py`
- [ ] Export to ONNX: `yolo export model=best.pt format=onnx`
- [ ] Convert to HEF: `./convert_bee_model_to_hef.sh`
- [ ] Create labels JSON
- [ ] Deploy to Pi
- [ ] Test with bee video
- [ ] Celebrate! 🎉

---

## Expected Performance

**YOLO11n on Hailo-8L (13 TOPS)**
- Inference: ~30-60 FPS
- Latency: ~16-33ms per frame
- Accuracy: mAP50 > 0.85 (with good dataset)

**Dataset Requirements**
- Minimum: 300 images
- Recommended: 1000+ images
- Ideal: 2000+ images with variety

**Training Time**
- Google Colab (T4 GPU): ~30-60 minutes (100 epochs)
- Local GPU (RTX 3080): ~15-30 minutes
- CPU: ~4-8 hours (not recommended)

---

## Troubleshooting

### Low mAP Score
- Increase training epochs
- Add more training data
- Adjust augmentation parameters
- Verify label quality

### Overfitting
- Reduce model complexity (use YOLO11n)
- Add data augmentation
- Use early stopping
- Get more training data

### Slow Inference on Pi
- Model already optimized (YOLO11n)
- Hailo should give 30-60 FPS
- Check HEF conversion settings

---

## Next Steps After Training

1. **Validate on test set**: Ensure good accuracy
2. **Test on Pi**: Verify HEF conversion worked
3. **Benchmark FPS**: Measure real-world performance
4. **Fine-tune thresholds**: Adjust conf/IOU for best results
5. **Deploy to production**: Update default model
6. **Monitor performance**: Track detection accuracy over time

---

## References

- Ultralytics YOLO11: https://docs.ultralytics.com
- Hailo Model Zoo: https://github.com/hailo-ai/hailo_model_zoo
- Roboflow: https://roboflow.com
- Training Guide: https://docs.ultralytics.com/modes/train/
