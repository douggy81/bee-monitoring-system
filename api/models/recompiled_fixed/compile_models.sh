#!/bin/bash
set -e

echo "======================================================================"
echo "🐝 COMPILING BEE MODELS WITH FIXED THRESHOLDS"
echo "======================================================================"
echo ""

# Activate virtual environment
source /workspace/hailo_venv/bin/activate

echo "Hailo SDK info:"
python -c "import hailo_sdk_client; print(f'Version: {hailo_sdk_client.__version__}')"
echo ""

cd /models

#------------------------------------------------------------------------------
# Model 1: yolo11n_bee_best (640x640)
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🐝 Model 1: yolo11n_bee_best.onnx (640x640)"
echo "======================================================================"
echo ""

ONNX_1="bee_detection_model_10022025/yolo11n_bee_best.onnx"

if [ ! -f "$ONNX_1" ]; then
    echo "❌ ONNX not found: $ONNX_1"
    exit 1
fi

echo "Settings:"
echo "  ✅ Hardware: hailo8l"
echo "  ✅ Score threshold: 0.15 ← FIX (was 0.30)"
echo "  ✅ IOU threshold: 0.45"
echo "  ✅ Image size: 640x640"
echo ""

echo "Step 1/3: Parsing ONNX..."
hailo parser onnx "$ONNX_1" \
    --hw-arch hailo8l \
    --output /output/yolo11n_bee_best.har

echo ""
echo "Step 2/3: Optimizing..."
hailo optimize /output/yolo11n_bee_best.har \
    --hw-arch hailo8l \
    --output /output/yolo11n_bee_best_optimized.har

echo ""
echo "Step 3/3: Compiling with NMS..."
hailo compiler /output/yolo11n_bee_best_optimized.har \
    --hw-arch hailo8l \
    --output /output/yolo11n_bee_best_thresh015.hef \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45

echo ""
echo "✅ Model 1 compiled successfully!"
echo ""

#------------------------------------------------------------------------------
# Model 2: yolo11n_bee_v2 (800x800)
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🐝 Model 2: yolo11n_bee_v2.onnx (800x800)"
echo "======================================================================"
echo ""

ONNX_2="yolo11n_bee_v2.onnx"

if [ ! -f "$ONNX_2" ]; then
    echo "❌ ONNX not found: $ONNX_2"
    exit 1
fi

echo "Settings:"
echo "  ✅ Hardware: hailo8l"
echo "  ✅ Score threshold: 0.15 ← FIX (was 0.30)"
echo "  ✅ IOU threshold: 0.45"
echo "  ✅ Image size: 800x800"
echo ""

echo "Step 1/3: Parsing ONNX..."
hailo parser onnx "$ONNX_2" \
    --hw-arch hailo8l \
    --output /output/yolo11n_bee_v2.har

echo ""
echo "Step 2/3: Optimizing..."
hailo optimize /output/yolo11n_bee_v2.har \
    --hw-arch hailo8l \
    --output /output/yolo11n_bee_v2_optimized.har

echo ""
echo "Step 3/3: Compiling with NMS..."
hailo compiler /output/yolo11n_bee_v2_optimized.har \
    --hw-arch hailo8l \
    --output /output/yolo11n_bee_v2_thresh015.hef \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45

echo ""
echo "✅ Model 2 compiled successfully!"
echo ""

echo "======================================================================"
echo "🎉 COMPILATION COMPLETE!"
echo "======================================================================"
echo ""
ls -lh /output/*.hef
echo ""
