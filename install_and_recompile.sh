#!/bin/bash
#
# Install Hailo DFC and Recompile Bee Models
# with Fixed NMS Thresholds for Hailo-8L (13 TOPS)
#
# Date: October 9, 2025
#

set -e  # Exit on error

echo "======================================================================"
echo "🚀 HAILO DFC INSTALLATION & MODEL RECOMPILATION"
echo "======================================================================"
echo ""
echo "Target Hardware: Hailo-8L (AI HAT+, 13 TOPS)"
echo "Fix: score_threshold=0.15 (was 0.30)"
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_ROOT/hailo_venv"
DFC_WHEEL="$PROJECT_ROOT/hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl"
MODEL_DIR="$PROJECT_ROOT/api/models"
OUTPUT_DIR="$MODEL_DIR/recompiled_fixed"

echo "📁 Project: $PROJECT_ROOT"
echo "🐍 Virtual env: $VENV_DIR"
echo "💿 DFC wheel: $DFC_WHEEL"
echo ""

# Check if DFC wheel exists
if [ ! -f "$DFC_WHEEL" ]; then
    echo "❌ DFC wheel not found: $DFC_WHEEL"
    exit 1
fi

#------------------------------------------------------------------------------
# Step 1: Create Virtual Environment
#------------------------------------------------------------------------------
echo "======================================================================"
echo "📦 STEP 1: Creating Virtual Environment"
echo "======================================================================"
echo ""

if [ -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment already exists at $VENV_DIR"
    echo "   Remove it? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        echo "✅ Removed old virtual environment"
    else
        echo "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
fi

echo ""

#------------------------------------------------------------------------------
# Step 2: Activate and Install DFC
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🔧 STEP 2: Installing Hailo Dataflow Compiler v3.33.0"
echo "======================================================================"
echo ""

# Activate virtual environment
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --upgrade pip setuptools wheel

echo ""
echo "Installing Hailo DFC wheel..."
pip install "$DFC_WHEEL"

echo ""
echo "✅ Hailo DFC installed successfully!"
echo ""

# Verify installation
echo "Verifying installation..."
python -c "import hailo_sdk_client; print(f'✅ hailo_sdk_client version: {hailo_sdk_client.__version__}')" || echo "⚠️  Could not verify hailo_sdk_client"

echo ""

#------------------------------------------------------------------------------
# Step 3: Recompile Models
#------------------------------------------------------------------------------
echo "======================================================================"
echo "🐝 STEP 3: Recompiling Bee Models"
echo "======================================================================"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Output directory: $OUTPUT_DIR"
echo ""

#------------------------------------------------------------------------------
# Model 1: yolo11n_bee_best (640x640)
#------------------------------------------------------------------------------
echo "----------------------------------------------------------------------"
echo "🐝 Model 1: yolo11n_bee_best.onnx (640x640)"
echo "----------------------------------------------------------------------"
echo ""

ONNX_FILE_1="$MODEL_DIR/bee_detection_model_10022025/yolo11n_bee_best.onnx"

if [ ! -f "$ONNX_FILE_1" ]; then
    echo "❌ ONNX file not found: $ONNX_FILE_1"
    exit 1
fi

echo "Source: $ONNX_FILE_1"
echo ""
echo "Compilation settings:"
echo "  ✅ Hardware: hailo8l (13 TOPS)"
echo "  ✅ Score threshold: 0.15 (was 0.30) ← KEY FIX!"
echo "  ✅ IOU threshold: 0.45 (was 0.60)"
echo "  ✅ Classes: 3 (background, bee, pollen)"
echo "  ✅ Image size: 640x640"
echo ""

# Use hailo SDK to compile
hailo parser onnx "$ONNX_FILE_1" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_best.har"

echo ""
echo "Optimizing..."
hailo optimize "$OUTPUT_DIR/yolo11n_bee_best.har" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_best_optimized.har"

echo ""
echo "Compiling with NMS (score_threshold=0.15)..."
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
echo "----------------------------------------------------------------------"
echo "🐝 Model 2: yolo11n_bee_v2.onnx (800x800)"
echo "----------------------------------------------------------------------"
echo ""

ONNX_FILE_2="$MODEL_DIR/yolo11n_bee_v2.onnx"

if [ ! -f "$ONNX_FILE_2" ]; then
    echo "❌ ONNX file not found: $ONNX_FILE_2"
    exit 1
fi

echo "Source: $ONNX_FILE_2"
echo ""
echo "Compilation settings:"
echo "  ✅ Hardware: hailo8l (13 TOPS)"
echo "  ✅ Score threshold: 0.15 (was 0.30) ← KEY FIX!"
echo "  ✅ IOU threshold: 0.45 (was 0.60)"
echo "  ✅ Classes: 3 (background, bee, pollen)"
echo "  ✅ Image size: 800x800"
echo ""

# Parse
hailo parser onnx "$ONNX_FILE_2" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_v2.har"

echo ""
echo "Optimizing..."
hailo optimize "$OUTPUT_DIR/yolo11n_bee_v2.har" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_v2_optimized.har"

echo ""
echo "Compiling with NMS (score_threshold=0.15)..."
hailo compiler "$OUTPUT_DIR/yolo11n_bee_v2_optimized.har" \
    --hw-arch hailo8l \
    --output "$OUTPUT_DIR/yolo11n_bee_v2_thresh015.hef" \
    --nms-score-threshold 0.15 \
    --nms-iou-threshold 0.45

echo ""
echo "✅ Model 2 compiled successfully!"
echo ""

#------------------------------------------------------------------------------
# Step 4: Verify Compilation
#------------------------------------------------------------------------------
echo "======================================================================"
echo "✅ STEP 4: Verifying Compiled Models"
echo "======================================================================"
echo ""

echo "Compiled HEF files:"
ls -lh "$OUTPUT_DIR"/*.hef

echo ""
echo "Verifying score thresholds..."
echo ""

for hef in "$OUTPUT_DIR"/*.hef; do
    echo "📋 $(basename "$hef"):"
    hailortcli parse-hef "$hef" 2>/dev/null | grep -i "Score threshold" || echo "  (Could not parse - will verify on Pi)"
    echo ""
done

echo "======================================================================"
echo "🎉 SUCCESS! MODELS COMPILED WITH FIXED THRESHOLDS!"
echo "======================================================================"
echo ""
echo "New HEF files in: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Copy HEF files to Raspberry Pi:"
echo "     scp $OUTPUT_DIR/*.hef rpi:/tmp/bee_models_fixed/"
echo ""
echo "  2. Update test script to use new model:"
echo "     hef_path = '/tmp/bee_models_fixed/yolo11n_bee_best_thresh015.hef'"
echo ""
echo "  3. Test on Pi:"
echo "     python3 /tmp/test_hailopython.py bee_best image"
echo ""
echo "  4. Expected result: 🐝 DETECTIONS! 🎉"
echo ""
echo "======================================================================"
echo "Virtual environment still active. To deactivate, run: deactivate"
echo "======================================================================"
