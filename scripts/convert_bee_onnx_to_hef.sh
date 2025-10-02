#!/bin/bash
# Convert trained bee ONNX model to Hailo HEF format

# Path to your trained ONNX model (from Colab download)
ONNX_MODEL="$1"

if [ -z "$ONNX_MODEL" ]; then
    echo "Usage: $0 <path_to_onnx_model>"
    echo ""
    echo "Example:"
    echo "  $0 ~/Downloads/bee_detection_model/yolo11n_bee_best.onnx"
    exit 1
fi

if [ ! -f "$ONNX_MODEL" ]; then
    echo "Error: ONNX model not found: $ONNX_MODEL"
    exit 1
fi

OUTPUT_DIR="$(dirname "$ONNX_MODEL")"
OUTPUT_HEF="${OUTPUT_DIR}/yolo11n_bee.hef"

echo "=========================================="
echo "Convert Bee ONNX to Hailo HEF"
echo "=========================================="
echo ""
echo "Input ONNX:  $ONNX_MODEL"
echo "Output HEF:  $OUTPUT_HEF"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not installed"
    echo "Install from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "Pulling Hailo Docker image (one-time setup)..."
docker pull hailo/hailo_sw_suite:latest

echo ""
echo "Converting ONNX to HEF (this may take 5-10 minutes)..."
echo ""

docker run --rm -it \
  -v "$(dirname "$ONNX_MODEL"):/workspace" \
  hailo/hailo_sw_suite:latest \
  hailo model optimize \
    --model-path "/workspace/$(basename "$ONNX_MODEL")" \
    --hw-arch hailo8l \
    --output-path "/workspace/yolo11n_bee.hef" \
    --performance

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ Conversion Complete!"
    echo "=========================================="
    echo ""
    echo "HEF model: $OUTPUT_HEF"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy to Pi:"
    echo "     scp $OUTPUT_HEF rpi:/tmp/"
    echo "     ssh rpi \"sudo mv /tmp/yolo11n_bee.hef /opt/bee-monitoring/src/api/models/\""
    echo ""
    echo "  2. Deploy labels:"
    echo "     scp ${OUTPUT_DIR}/labels_bee.json rpi:/tmp/"
    echo "     ssh rpi \"sudo mv /tmp/labels_bee.json /opt/bee-monitoring/src/api/models/\""
    echo ""
    echo "  3. Test detection:"
    echo "     curl 'http://192.168.68.66/api/bee/ai/detect?stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&ai_backend=hailo&annotate=1' -o result.jpg"
else
    echo ""
    echo "❌ Conversion failed"
    echo "Check error messages above"
    exit 1
fi
