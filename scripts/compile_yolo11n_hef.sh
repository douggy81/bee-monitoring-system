#!/bin/bash
# Compile YOLO11n ONNX to Hailo HEF format for Raspberry Pi AI HAT+ (Hailo-8L)
#
# Requirements:
# - Hailo Dataflow Compiler (hailo)
# - yolo11n.onnx model
#
# Usage: ./compile_yolo11n_hef.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_ROOT/api/models"
ONNX_PATH="$MODELS_DIR/yolo11n.onnx"
HEF_PATH="$MODELS_DIR/yolo11n.hef"

echo "=============================================="
echo "YOLO11n Hailo HEF Compilation"
echo "=============================================="
echo ""

# Check if ONNX model exists
if [ ! -f "$ONNX_PATH" ]; then
    echo "ERROR: ONNX model not found at $ONNX_PATH"
    echo "Run: python3 scripts/download_yolov11n.py"
    exit 1
fi

echo "Input:  $ONNX_PATH"
echo "Output: $HEF_PATH"
echo ""

# Check if HEF already exists
if [ -f "$HEF_PATH" ]; then
    echo "HEF file already exists. Remove it to recompile:"
    echo "  rm $HEF_PATH"
    exit 0
fi

# Hailo Model Zoo has pre-compiled configs for YOLO models
# We'll use hailo parser with YOLO11n (similar to YOLOv8)
echo "Compiling ONNX to HEF (this may take several minutes)..."
echo ""

# Basic compilation command for YOLO11n
# Optimize for Hailo-8L (13 TOPS on AI HAT+)
hailo parser onnx \
    --input-model-path "$ONNX_PATH" \
    --output-model-script "$MODELS_DIR/yolo11n_model_script.py" \
    --net-name yolo11n

hailo compiler \
    --model-script-path "$MODELS_DIR/yolo11n_model_script.py" \
    --model-name yolo11n \
    --hw-arch hailo8l \
    --output-path "$HEF_PATH" \
    --batch-size 1

if [ -f "$HEF_PATH" ]; then
    echo ""
    echo "✓ HEF compilation successful!"
    echo "  Output: $HEF_PATH"
    echo "  Size: $(du -h "$HEF_PATH" | cut -f1)"
    echo ""
    echo "To deploy to Raspberry Pi:"
    echo "  scp $HEF_PATH digital4ai@192.168.68.66:/home/digital4ai/"
    echo "  ssh digital4ai@192.168.68.66"
    echo "  sudo install -o bee-monitor -g bee-monitor -m 0644 ~/yolo11n.hef /opt/bee-monitoring/src/api/models/"
    echo "  sudo systemctl restart bee-api"
else
    echo "ERROR: HEF compilation failed"
    exit 1
fi
