# Quick Start: Train Custom Bee Detection Model

You have Roboflow datasets with bee bounding boxes. Here's how to train YOLO11 and deploy to your Raspberry Pi with Hailo-8L.

## TL;DR - Fast Track

```bash
# 1. Install dependencies
pip install ultralytics roboflow

# 2. Train (with Roboflow download)
python scripts/train_bee_model.py \
  --roboflow-key YOUR_API_KEY \
  --workspace your-workspace \
  --project bee-detection \
  --epochs 100 \
  --batch 16

# 3. Deploy (see below)
```

---

## Step 1: Get Your Roboflow API Key

1. Go to https://roboflow.com
2. Settings → API Key
3. Copy your API key

---

## Step 2: Train the Model

### Option A: Automatic Download from Roboflow (Easiest!)

```bash
python scripts/train_bee_model.py \
  --roboflow-key YOUR_ROBOFLOW_API_KEY \
  --workspace your-workspace-name \
  --project bee-detection-project \
  --epochs 100 \
  --batch 16
```

**This will:**
- Download your dataset
- Train YOLO11n model
- Export to ONNX
- Save to `runs/bee-detection/yolo11n-bee/`

### Option B: Use Pre-Downloaded Dataset

```bash
# If you already exported dataset from Roboflow:
python scripts/train_bee_model.py \
  --data datasets/bee-detection/data.yaml \
  --epochs 100 \
  --batch 16
```

### Training Time

- **GPU (T4/V100)**: ~30-60 minutes
- **Google Colab**: ~45 minutes (free tier)
- **CPU**: ~4-8 hours (not recommended)

### Expected Output

```
✓ Training Complete!
Best model: runs/bee-detection/yolo11n-bee/weights/best.pt
ONNX model: runs/bee-detection/yolo11n-bee/weights/best.onnx
mAP50: 0.850
```

---

## Step 3: Convert ONNX to HEF (Hailo Format)

### Prerequisites

```bash
# Install Hailo Dataflow Compiler (one-time setup)
docker pull hailo/hailo_sw_suite:latest
```

### Convert

Use the existing conversion script (modify for your model):

```bash
# Edit api/models/convert_onnx_to_HEF.sh
# Change ONNX_PATH to your trained model:
ONNX_PATH="runs/bee-detection/yolo11n-bee/weights/best.onnx"

# Run conversion
./api/models/convert_onnx_to_HEF.sh
```

**Or manual conversion:**

```bash
docker run --rm -it \
  -v $(pwd):/workspace \
  hailo/hailo_sw_suite:latest \
  hailo model optimize \
    --model-path /workspace/runs/bee-detection/yolo11n-bee/weights/best.onnx \
    --hw-arch hailo8l \
    --output-path /workspace/api/models/yolo11n_bee.hef \
    --performance
```

This creates: `api/models/yolo11n_bee.hef`

---

## Step 4: Create Model Metadata

### Create Labels File

`api/models/labels_bee.json`:

```json
{
  "0": "bee"
}
```

Or for multiple classes (adjust to your dataset):

```json
{
  "0": "bee",
  "1": "wasp",
  "2": "bumblebee"
}
```

### Create Model Config

`api/models/yolo11n_bee.json`:

```json
{
  "ConfigVersion": 11,
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
    "ModelPath": "yolo11n_bee.hef"
  }],
  "POST_PROCESS": [{
    "OutputPostprocessType": "DetectionYoloHailo",
    "OutputNumClasses": 1,
    "LabelsPath": "labels_bee.json"
  }]
}
```

---

## Step 5: Deploy to Raspberry Pi

```bash
# Copy model files to Pi
scp api/models/yolo11n_bee.hef \
    api/models/yolo11n_bee.json \
    api/models/labels_bee.json \
    rpi:/tmp/

# Install on Pi
ssh rpi "sudo mv /tmp/yolo11n_bee.* /opt/bee-monitoring/src/api/models/ && \
         sudo mv /tmp/labels_bee.json /opt/bee-monitoring/src/api/models/ && \
         sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/src/api/models/yolo11n_bee.*"
```

---

## Step 6: Update Backend to Use Bee Model

Edit `ai/hailo_backend.py`:

```python
def _resolve_default_hef_path(self) -> Optional[str]:
    """Find default HEF file."""
    models_dir = os.path.join(root, "api", "models")
    
    # Prioritize bee detection model
    hef_candidates = [
        os.path.join(models_dir, "yolo11n_bee.hef"),          # ← Add this
        os.path.join(models_dir, "yolo11n_coco--640x640_quant_hailort_multidevice_1.hef"),
    ]
    
    for hef in hef_candidates:
        if os.path.isfile(hef):
            return hef
    return None
```

Deploy the change:

```bash
scp ai/hailo_backend.py rpi:/home/digital4ai/deploy_cascade/
ssh rpi "sudo install -o bee-monitor -g bee-monitor -m 0644 \
  /home/digital4ai/deploy_cascade/hailo_backend.py \
  /opt/bee-monitoring/src/ai/ && \
  sudo systemctl restart bee-api"
```

---

## Step 7: Test Bee Detection!

```bash
# Test with your bee video
curl "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&\
ai_backend=hailo&\
annotate=1" -o bee_detected.jpg

# View results
open bee_detected.jpg

# Get detection data
curl "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&\
ai_backend=hailo" | jq '{
  detection_count: (.detections | length),
  bees: .detections
}'
```

**Expected output:**
```json
{
  "detection_count": 15,
  "bees": [
    {
      "bbox": [120, 45, 35, 28],
      "confidence": 0.87,
      "class_id": 0,
      "class_name": "bee"
    },
    ...
  ]
}
```

---

## Google Colab Training (No GPU Needed)

If you don't have a GPU, use Google Colab for free!

### 1. Open Colab
https://colab.research.google.com

### 2. Create New Notebook

### 3. Copy This Code

```python
# Install dependencies
!pip install ultralytics roboflow

# Download dataset from Roboflow
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")
project = rf.workspace("your-workspace").project("bee-detection")
dataset = project.version(1).download("yolov8")

# Train YOLO11n
from ultralytics import YOLO
model = YOLO('yolo11n.pt')

results = model.train(
    data=f'{dataset.location}/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    device=0,  # GPU
    project='bee-model',
    name='train'
)

# Validate
metrics = model.val()
print(f"mAP50: {metrics.box.map50:.3f}")

# Export to ONNX
model.export(format='onnx', imgsz=640, simplify=True)

# Download trained model
from google.colab import files
files.download('bee-model/train/weights/best.pt')
files.download('bee-model/train/weights/best.onnx')
```

### 4. Run All Cells

After training (~45 min), download `best.onnx` to your Mac.

---

## Troubleshooting

### "No GPU available"
→ Use Google Colab or reduce batch size to 8

### "CUDA out of memory"
→ Reduce batch size: `--batch 8` or `--batch 4`

### "Data.yaml not found"
→ Check your dataset path or Roboflow credentials

### Low mAP score
→ Train longer (200 epochs) or get more data

### HEF conversion fails
→ Ensure ONNX model is simplified (`simplify=True`)

---

## What You Need

### Required
- ✅ Roboflow account with bee dataset
- ✅ Python 3.8+
- ✅ GPU (or Google Colab)
- ✅ Docker (for HEF conversion)

### Your Roboflow Info
```bash
# Fill these in:
ROBOFLOW_API_KEY="your_key_here"
WORKSPACE="your_workspace"
PROJECT="bee-detection"
```

---

## Complete Command Sequence

```bash
# 1. Train model
python scripts/train_bee_model.py \
  --roboflow-key $ROBOFLOW_API_KEY \
  --workspace $WORKSPACE \
  --project $PROJECT \
  --epochs 100

# 2. Convert to HEF
./api/models/convert_onnx_to_HEF.sh

# 3. Create labels
echo '{"0": "bee"}' > api/models/labels_bee.json

# 4. Deploy to Pi
scp api/models/yolo11n_bee.* rpi:/tmp/
ssh rpi "sudo mv /tmp/yolo11n_bee.* /opt/bee-monitoring/src/api/models/"

# 5. Test
curl "http://192.168.68.66/api/bee/ai/detect?stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&ai_backend=hailo&annotate=1" -o result.jpg
```

---

## Expected Timeline

1. **Setup** (5 min) - Install dependencies
2. **Training** (30-60 min) - Train YOLO11n
3. **Conversion** (10 min) - ONNX to HEF
4. **Deploy** (5 min) - Copy to Pi
5. **Test** (2 min) - Run detection

**Total: ~1-2 hours from start to working bee detection!**

---

## Full Documentation

See `docs/TRAIN_BEE_MODEL.md` for complete details.

---

**Ready to start? Run the training command with your Roboflow credentials!** 🐝🚀
