#!/bin/bash
# 
# Recompile Bee YOLO11 Models with CORRECTED NMS Thresholds
# 
# ROOT CAUSE: Original models compiled with score_threshold=0.30 (too high!)
# FIX: Recompile with score_threshold=0.15 (will detect more bees)
#
# Date: October 9, 2025
# 

set -e  # Exit on error

echo "======================================================================"
echo "🐝 RECOMPILING BEE MODELS WITH FIXED NMS THRESHOLDS"
echo "======================================================================"
echo ""
echo "Original issue: score_threshold=0.30 filtered out all detections"
echo "New setting: score_threshold=0.15 (standard for small object detection)"
echo ""

# Check if hailomz is available
if ! command -v hailomz &> /dev/null; then
    echo "❌ hailomz not found!"
    echo ""
    echo "Please install Hailo Model Zoo:"
    echo "  git clone https://github.com/hailo-ai/hailo_model_zoo.git"
    echo "  cd hailo_model_zoo"
    echo "  pip install -e ."
    echo ""
    exit 1
fi

echo "✅ hailomz found: $(which hailomz)"
echo ""

# Model directory
MODEL_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📁 Model directory: $MODEL_DIR"
echo ""

# Create output directory for new HEF files
OUTPUT_DIR="$MODEL_DIR/recompiled_fixed_threshold"
mkdir -p "$OUTPUT_DIR"
echo "📦 Output directory: $OUTPUT_DIR"
echo ""

#------------------------------------------------------------------------------
# Model 1: yolo11n_bee_best (640x640)
#------------------------------------------------------------------------------
echo "======================================================================
🔄 Compiling Model 1: yolo11n_bee_best.onnx
======================================================================"

ONNX_FILE="$MODEL_DIR/bee_detection_model_10022025/yolo11n_bee_best.onnx"

if [ ! -f "$ONNX_FILE" ]; then
    echo "❌ ONNX file not found: $ONNX_FILE"
    exit 1
fi

echo "Source: $ONNX_FILE"
echo ""
echo "Settings:"
echo "  - Score threshold: 0.15 (was 0.30)"
echo "  - IOU threshold: 0.45 (was 0.60)"
echo "  - Classes: 3 (background, bee, pollen)"
echo "  - Image size: 640x640"
echo ""

hailomz compile "$ONNX_FILE" \
    --hw-arch hailo8l \
    --output-dir "$OUTPUT_DIR" \
    --name "yolo11n_bee_best_fixed" \
    --classes 3 \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45 \
    --performance

echo "✅ yolo11n_bee_best compiled successfully!"
echo ""

#------------------------------------------------------------------------------
# Model 2: yolo11n_bee_v2 (800x800)
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🔄 Compiling Model 2: yolo11n_bee_v2.onnx"
echo "======================================================================"

ONNX_FILE="$MODEL_DIR/yolo11n_bee_v2.onnx"

if [ ! -f "$ONNX_FILE" ]; then
    echo "❌ ONNX file not found: $ONNX_FILE"
    exit 1
fi

echo "Source: $ONNX_FILE"
echo ""
echo "Settings:"
echo "  - Score threshold: 0.15 (was 0.30)"
echo "  - IOU threshold: 0.45 (was 0.60)"
echo "  - Classes: 3 (background, bee, pollen)"
echo "  - Image size: 800x800"
echo ""

hailomz compile "$ONNX_FILE" \
    --hw-arch hailo8l \
    --output-dir "$OUTPUT_DIR" \
    --name "yolo11n_bee_v2_fixed" \
    --classes 3 \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45 \
    --performance

echo "✅ yolo11n_bee_v2 compiled successfully!"
echo ""

#------------------------------------------------------------------------------
# Summary
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🎉 COMPILATION COMPLETE!"
echo "======================================================================"
echo ""
echo "New HEF files created in:"
echo "  $OUTPUT_DIR"
echo ""
echo "Files:"
ls -lh "$OUTPUT_DIR"/*.hef
echo ""
echo "Next steps:"
echo "  1. Copy new HEF files to Raspberry Pi"
echo "  2. Update paths in test scripts"
echo "  3. Run test_hailopython.py to verify detections work!"
echo ""
echo "Expected result: DETECTIONS! 🐝🎉"
echo "======================================================================"
