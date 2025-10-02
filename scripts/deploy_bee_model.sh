#!/bin/bash
# Complete deployment script for trained bee detection model

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_bee_detection_model.zip>"
    echo ""
    echo "This script will:"
    echo "  1. Extract the trained model"
    echo "  2. Convert ONNX to HEF (Hailo format)"
    echo "  3. Deploy to Raspberry Pi"
    echo "  4. Update backend to use bee model"
    echo "  5. Test detection"
    echo ""
    echo "Example:"
    echo "  $0 ~/Downloads/bee_detection_model.zip"
    exit 1
fi

ZIP_FILE="$1"
PI_HOST="${PI_HOST:-rpi}"

if [ ! -f "$ZIP_FILE" ]; then
    echo "Error: Zip file not found: $ZIP_FILE"
    exit 1
fi

echo "=========================================="
echo "Bee Detection Model Deployment"
echo "=========================================="
echo ""

# Step 1: Extract
EXTRACT_DIR="/tmp/bee_model_deploy"
echo "[1/6] Extracting model..."
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"
unzip -q "$ZIP_FILE" -d "$EXTRACT_DIR"
echo "✓ Extracted to: $EXTRACT_DIR"
echo ""

# Step 2: Convert ONNX to HEF
echo "[2/6] Converting ONNX to HEF (this may take 5-10 minutes)..."
ONNX_FILE="$EXTRACT_DIR/yolo11n_bee_best.onnx"

if [ ! -f "$ONNX_FILE" ]; then
    echo "Error: ONNX file not found in zip"
    exit 1
fi

./scripts/convert_bee_onnx_to_hef.sh "$ONNX_FILE"
echo ""

# Step 3: Copy to api/models
echo "[3/6] Copying to api/models/..."
cp "$EXTRACT_DIR/yolo11n_bee.hef" api/models/
cp "$EXTRACT_DIR/labels_bee.json" api/models/
echo "✓ Models copied to api/models/"
echo ""

# Step 4: Deploy to Pi
echo "[4/6] Deploying to Raspberry Pi..."
scp api/models/yolo11n_bee.hef \
    api/models/labels_bee.json \
    "$PI_HOST:/tmp/"

ssh "$PI_HOST" "sudo mv /tmp/yolo11n_bee.hef /tmp/labels_bee.json /opt/bee-monitoring/src/api/models/ && \
                sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/src/api/models/yolo11n_bee.* && \
                sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/src/api/models/labels_bee.json"
echo "✓ Deployed to Pi"
echo ""

# Step 5: Update backend
echo "[5/6] Updating backend to use bee model..."

# Backup current backend
ssh "$PI_HOST" "sudo cp /opt/bee-monitoring/src/ai/hailo_backend.py /opt/bee-monitoring/src/ai/hailo_backend.py.bak"

# Update to prioritize bee model
cat > /tmp/backend_patch.py << 'EOF'
# Add bee model to HEF candidates
import sys
input_file = sys.argv[1]
with open(input_file, 'r') as f:
    content = f.read()

# Find the hef_candidates list and add bee model
if 'yolo11n_bee.hef' not in content:
    content = content.replace(
        'hef_candidates = [',
        'hef_candidates = [\n        os.path.join(models_dir, "yolo11n_bee.hef"),'
    )
    
with open(input_file, 'w') as f:
    f.write(content)
EOF

scp /tmp/backend_patch.py ai/hailo_backend.py "$PI_HOST:/tmp/"
ssh "$PI_HOST" "python3 /tmp/backend_patch.py /tmp/hailo_backend.py && \
                sudo install -o bee-monitor -g bee-monitor -m 0644 /tmp/hailo_backend.py /opt/bee-monitoring/src/ai/ && \
                sudo systemctl restart bee-api && \
                sleep 4"
echo "✓ Backend updated and restarted"
echo ""

# Step 6: Test detection
echo "[6/6] Testing bee detection..."
echo ""

curl -sS "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&\
ai_backend=hailo&\
annotate=1" -o /tmp/bee_test_result.jpg

if [ $? -eq 0 ]; then
    echo "✓ Detection test successful!"
    echo ""
    
    # Get results
    RESULT=$(curl -sS "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&\
ai_backend=hailo")
    
    echo "Detection results:"
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
    
    echo ""
    echo "Annotated image saved to: /tmp/bee_test_result.jpg"
    echo "Opening..."
    open /tmp/bee_test_result.jpg 2>/dev/null || echo "(Open /tmp/bee_test_result.jpg manually)"
else
    echo "❌ Detection test failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Your custom bee detection model is now running on Hailo-8L!"
echo ""
echo "Test commands:"
echo "  # Detection with your bee video"
echo "  curl 'http://192.168.68.66/api/bee/ai/detect?stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&ai_backend=hailo&annotate=1' -o result.jpg"
echo ""
echo "  # JSON results"
echo "  curl 'http://192.168.68.66/api/bee/ai/detect?stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&ai_backend=hailo' | jq"
echo ""
echo "Files deployed:"
echo "  - api/models/yolo11n_bee.hef"
echo "  - api/models/labels_bee.json"
echo "  - Updated: ai/hailo_backend.py"
echo ""
echo "Training results in: $EXTRACT_DIR"
