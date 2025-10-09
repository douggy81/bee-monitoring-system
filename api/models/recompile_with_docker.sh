#!/bin/bash
#
# Recompile Bee Models with Hailo Docker Container
# 
# This uses the official Hailo Docker image to compile models
# with CORRECTED NMS thresholds (0.15 instead of 0.30)
#
# Date: October 9, 2025
#

set -e

echo "======================================================================"
echo "🐝 RECOMPILING BEE MODELS WITH HAILO DOCKER"
echo "======================================================================"
echo ""
echo "Issue: Original models had score_threshold=0.30 (too high!)"
echo "Fix: Recompiling with score_threshold=0.15"
echo ""

# Get absolute path to this script's directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Model directory: $SCRIPT_DIR"
echo ""

# Create output directory
OUTPUT_DIR="$SCRIPT_DIR/recompiled_fixed"
mkdir -p "$OUTPUT_DIR"

echo "📦 Output directory: $OUTPUT_DIR"
echo ""

# Pull Hailo Docker image
echo "🐳 Checking for Hailo Docker image..."
if ! docker images | grep -q "hailo-model-zoo"; then
    echo "Pulling Hailo Model Zoo Docker image (this may take a few minutes)..."
    docker pull ghcr.io/hailo-ai/hailo-model-zoo:latest
else
    echo "✅ Hailo image already available"
fi
echo ""

#------------------------------------------------------------------------------
# Create compilation script to run inside Docker
#------------------------------------------------------------------------------
cat > "$OUTPUT_DIR/compile_inside_docker.sh" << 'DOCKER_SCRIPT'
#!/bin/bash
set -e

echo "======================================================================"
echo "🔧 COMPILING MODELS INSIDE DOCKER CONTAINER"
echo "======================================================================"
echo ""

cd /workspace

# Check for ONNX files
if [ ! -f "bee_detection_model_10022025/yolo11n_bee_best.onnx" ]; then
    echo "❌ yolo11n_bee_best.onnx not found!"
    exit 1
fi

if [ ! -f "yolo11n_bee_v2.onnx" ]; then
    echo "❌ yolo11n_bee_v2.onnx not found!"
    exit 1
fi

#------------------------------------------------------------------------------
# Compile Model 1: yolo11n_bee_best (640x640)
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🐝 Model 1: yolo11n_bee_best (640x640)"
echo "======================================================================"
echo ""
echo "Settings:"
echo "  Score threshold: 0.15 ← KEY FIX (was 0.30)"
echo "  IOU threshold: 0.45"
echo "  Classes: 3"
echo ""

hailomz compile bee_detection_model_10022025/yolo11n_bee_best.onnx \
    yolov8n \
    --hw-arch hailo8l \
    --ckpt bee_detection_model_10022025/yolo11n_bee_best.onnx \
    --calib-path /local_drive/hailo_model_zoo/hailo_model_zoo/cfg/alls/generic/yolov8n.alls \
    --yaml /local_drive/hailo_model_zoo/hailo_model_zoo/cfg/networks/yolov8n.yaml \
    --classes 3 \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45 \
    --output-dir /workspace/recompiled_fixed \
    --results-dir /workspace/recompiled_fixed \
    --name yolo11n_bee_best_thresh015

echo "✅ Model 1 compiled!"
echo ""

#------------------------------------------------------------------------------
# Compile Model 2: yolo11n_bee_v2 (800x800)
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🐝 Model 2: yolo11n_bee_v2 (800x800)"
echo "======================================================================"
echo ""
echo "Settings:"
echo "  Score threshold: 0.15 ← KEY FIX (was 0.30)"
echo "  IOU threshold: 0.45"
echo "  Classes: 3"
echo "  Image size: 800x800"
echo ""

hailomz compile yolo11n_bee_v2.onnx \
    yolov8n \
    --hw-arch hailo8l \
    --ckpt yolo11n_bee_v2.onnx \
    --calib-path /local_drive/hailo_model_zoo/hailo_model_zoo/cfg/alls/generic/yolov8n.alls \
    --yaml /local_drive/hailo_model_zoo/hailo_model_zoo/cfg/networks/yolov8n.yaml \
    --classes 3 \
    --resize 800 800 \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45 \
    --output-dir /workspace/recompiled_fixed \
    --results-dir /workspace/recompiled_fixed \
    --name yolo11n_bee_v2_thresh015

echo "✅ Model 2 compiled!"
echo ""
echo "======================================================================"
echo "🎉 COMPILATION COMPLETE!"
echo "======================================================================"
DOCKER_SCRIPT

chmod +x "$OUTPUT_DIR/compile_inside_docker.sh"

#------------------------------------------------------------------------------
# Run Docker container
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🐳 STARTING DOCKER CONTAINER"
echo "======================================================================"
echo ""

docker run --rm -it \
    -v "$SCRIPT_DIR:/workspace" \
    ghcr.io/hailo-ai/hailo-model-zoo:latest \
    bash /workspace/recompiled_fixed/compile_inside_docker.sh

echo ""
echo "======================================================================"
echo "🎉 SUCCESS!"
echo "======================================================================"
echo ""
echo "New HEF files are in:"
echo "  $OUTPUT_DIR"
echo ""
echo "Compiled HEF files:"
find "$OUTPUT_DIR" -name "*.hef" -exec ls -lh {} \;
echo ""
echo "Next steps:"
echo "  1. Copy HEF files to Raspberry Pi:"
echo "     scp $OUTPUT_DIR/*.hef rpi:/tmp/bee_models_fixed/"
echo ""
echo "  2. Test with:"
echo "     python3 test_hailopython.py bee_best image"
echo ""
echo "Expected: 🐝 DETECTIONS!!! 🎉"
echo "======================================================================"
