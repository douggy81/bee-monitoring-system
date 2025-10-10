#!/bin/bash
#
# Hailo Model Compilation Script for WSL2
# Recompile bee models with fixed NMS thresholds
#
# Target: Hailo-8L (13 TOPS)
# Fix: score_threshold=0.15 (was 0.30)
# Date: October 10, 2025
#

set -e

echo "======================================================================"
echo "🐝 COMPILING BEE MODELS WITH HAILO DFC"
echo "======================================================================"
echo ""
echo "Target Hardware: Hailo-8L (13 TOPS)"
echo "Fix: score_threshold=0.15 (was 0.30)"
echo ""

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "hailo_venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source hailo_venv/bin/activate
    else
        echo "❌ Virtual environment not found!"
        echo "Please run: python3 -m venv hailo_venv && source hailo_venv/bin/activate"
        exit 1
    fi
fi

# Verify Hailo SDK is installed
echo "Verifying Hailo SDK..."
python -c "import hailo_sdk_client; print(f'✅ Hailo DFC v{hailo_sdk_client.__version__}')" || {
    echo "❌ Hailo SDK not installed!"
    echo "Please install: pip install hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl"
    exit 1
}

echo ""

# Create output directory
OUTPUT_DIR="output"
mkdir -p "$OUTPUT_DIR"

echo "📁 Output directory: $OUTPUT_DIR"
echo ""

# Start logging
LOG_FILE="compilation.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "📝 Logging to: $LOG_FILE"
echo ""
echo "======================================================================"
echo "🐝 Model 1: yolo11n_bee_best.onnx (640x640)"
echo "======================================================================"
echo ""

ONNX_1="yolo11n_bee_best.onnx"

if [ ! -f "$ONNX_1" ]; then
    echo "❌ ONNX file not found: $ONNX_1"
    exit 1
fi

echo "Source: $ONNX_1"
echo "Size: $(du -h $ONNX_1 | cut -f1)"
echo ""
echo "Settings:"
echo "  ✅ Hardware: hailo8l (13 TOPS)"
echo "  ✅ Score threshold: 0.15 ← FIX (was 0.30)"
echo "  ✅ IOU threshold: 0.45 (was 0.60)"
echo "  ✅ Classes: 3 (background, bee, pollen)"
echo "  ✅ Image size: 640x640"
echo ""

echo "----------------------------------------------------------------------"
echo "Step 1/3: Parsing ONNX → HAR"
echo "----------------------------------------------------------------------"
echo "⏱️  This will take 30-60 minutes..."
echo ""

hailo parser onnx "$ONNX_1" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_best.har"

echo ""
echo "✅ Parsing complete!"
echo ""

echo "----------------------------------------------------------------------"
echo "Step 2/3: Optimizing HAR"
echo "----------------------------------------------------------------------"
echo "⏱️  This will take 30-60 minutes..."
echo ""

hailo optimize "$OUTPUT_DIR/yolo11n_bee_best.har" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_best_optimized.har"

echo ""
echo "✅ Optimization complete!"
echo ""

echo "----------------------------------------------------------------------"
echo "Step 3/3: Compiling to HEF with NMS"
echo "----------------------------------------------------------------------"
echo "⏱️  This will take 30-60 minutes..."
echo ""

hailo compiler "$OUTPUT_DIR/yolo11n_bee_best_optimized.har" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_best_thresh015.hef" \
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
    echo "❌ ONNX file not found: $ONNX_2"
    exit 1
fi

echo "Source: $ONNX_2"
echo "Size: $(du -h $ONNX_2 | cut -f1)"
echo ""
echo "Settings:"
echo "  ✅ Hardware: hailo8l (13 TOPS)"
echo "  ✅ Score threshold: 0.15 ← FIX (was 0.30)"
echo "  ✅ IOU threshold: 0.45 (was 0.60)"
echo "  ✅ Classes: 3 (background, bee, pollen)"
echo "  ✅ Image size: 800x800"
echo ""

echo "----------------------------------------------------------------------"
echo "Step 1/3: Parsing ONNX → HAR"
echo "----------------------------------------------------------------------"
echo "⏱️  This will take 30-60 minutes..."
echo ""

hailo parser onnx "$ONNX_2" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_v2.har"

echo ""
echo "✅ Parsing complete!"
echo ""

echo "----------------------------------------------------------------------"
echo "Step 2/3: Optimizing HAR"
echo "----------------------------------------------------------------------"
echo "⏱️  This will take 30-60 minutes..."
echo ""

hailo optimize "$OUTPUT_DIR/yolo11n_bee_v2.har" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_v2_optimized.har"

echo ""
echo "✅ Optimization complete!"
echo ""

echo "----------------------------------------------------------------------"
echo "Step 3/3: Compiling to HEF with NMS"
echo "----------------------------------------------------------------------"
echo "⏱️  This will take 30-60 minutes..."
echo ""

hailo compiler "$OUTPUT_DIR/yolo11n_bee_v2_optimized.har" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_v2_thresh015.hef" \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45

echo ""
echo "✅ Model 2 compiled successfully!"
echo ""

#------------------------------------------------------------------------------
# Summary
#------------------------------------------------------------------------------

echo "======================================================================"
echo "🎉 COMPILATION COMPLETE!"
echo "======================================================================"
echo ""
echo "Compiled HEF files:"
ls -lh "$OUTPUT_DIR"/*.hef
echo ""
echo "Intermediate files (can delete to save space):"
ls -lh "$OUTPUT_DIR"/*.har
echo ""

# Verify with hailo parse-hef if available
if command -v hailortcli &> /dev/null; then
    echo "----------------------------------------------------------------------"
    echo "✅ Verifying Compiled Models"
    echo "----------------------------------------------------------------------"
    echo ""
    
    for hef in "$OUTPUT_DIR"/*.hef; do
        echo "📋 $(basename "$hef"):"
        hailortcli parse-hef "$hef" 2>/dev/null | grep -i "Score threshold" || echo "  (hailortcli parse not available - will verify on Pi)"
        echo ""
    done
fi

echo "======================================================================"
echo "📤 NEXT STEPS"
echo "======================================================================"
echo ""
echo "1. Copy HEF files to Windows:"
echo "   cp $OUTPUT_DIR/*.hef /mnt/c/Users/<YOUR_USERNAME>/Downloads/"
echo ""
echo "2. Transfer to your Mac/Raspberry Pi"
echo ""
echo "3. Copy to Raspberry Pi:"
echo "   scp $OUTPUT_DIR/*.hef rpi:/tmp/bee_models_fixed/"
echo ""
echo "4. Test on Pi:"
echo "   python3 /tmp/test_hailopython.py bee_best image"
echo ""
echo "5. Expected result: 🐝 DETECTIONS! 🎉"
echo ""
echo "======================================================================"
echo "Compilation completed at: $(date)"
echo "======================================================================"
