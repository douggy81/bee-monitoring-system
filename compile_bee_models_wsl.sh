#!/bin/bash
#
# Hailo Model Compilation Script for WSL2
# Production-ready compilation pipeline for bee detection models
#
# Target: Hailo-8L (13 TOPS)
# Author: Digital4AI
# Date: October 10, 2025
#

set -e

#==============================================================================
# CONFIGURATION - Adjust these parameters as needed
#==============================================================================

# Hardware architecture
HW_ARCH="hailo8l"

# NMS Configuration (these will be applied via model script)
NMS_SCORE_THRESHOLD=0.15    # Lower = more detections (was 0.30, causing 0 detections)
NMS_IOU_THRESHOLD=0.45      # Lower = less duplicate suppression (was 0.60)
NMS_MAX_PROPOSALS=1000      # Maximum proposals before NMS

# Model optimization level
OPTIMIZATION_LEVEL="max"    # Options: "0", "1", "2", "max"

# Calibration settings
CALIB_METHOD="random"       # Options: "random" or path to calibration dataset
CALIB_SIZE=64               # Number of calibration images (default: 64)

# Output directory
OUTPUT_DIR="output"

# Models to compile
declare -A MODELS=(
    ["yolo11n_bee_best"]="yolo11n_bee_best.onnx"
    ["yolo11n_bee_v2"]="yolo11n_bee_v2.onnx"
)

#==============================================================================
# SETUP
#==============================================================================

echo "======================================================================"
echo "🐝 HAILO BEE MODEL COMPILATION PIPELINE"
echo "======================================================================"
echo ""
echo "Configuration:"
echo "  Hardware: $HW_ARCH (13 TOPS)"
echo "  NMS Score Threshold: $NMS_SCORE_THRESHOLD"
echo "  NMS IOU Threshold: $NMS_IOU_THRESHOLD"
echo "  Optimization Level: $OPTIMIZATION_LEVEL"
echo "  Calibration: $CALIB_METHOD ($CALIB_SIZE images)"
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

# Verify Hailo SDK
echo "Verifying Hailo SDK..."
python -c "import hailo_sdk_client; print(f'✅ Hailo DFC v{hailo_sdk_client.__version__}')" || {
    echo "❌ Hailo SDK not installed!"
    exit 1
}

echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo "📁 Output directory: $OUTPUT_DIR"
echo ""

# Start logging
LOG_FILE="compilation_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "📝 Logging to: $LOG_FILE"
echo ""

#==============================================================================
# FUNCTION: Create Model Script for NMS Configuration
#==============================================================================

create_model_script() {
    local model_name=$1
    local script_path="$OUTPUT_DIR/${model_name}_model_script.alls"
    
    cat > "$script_path" << EOF
# Model Script for $model_name
# NMS Configuration for Bee Detection

# Configure NMS post-processing
nms_postprocess(
    nms_config(
        score_threshold=$NMS_SCORE_THRESHOLD,
        iou_threshold=$NMS_IOU_THRESHOLD,
        max_proposals_per_class=$NMS_MAX_PROPOSALS
    )
)

# Set performance optimization level
performance_param(compiler_optimization_level=$OPTIMIZATION_LEVEL)

# Normalization (if needed)
# normalization1 = normalization([0.0, 0.0, 0.0], [255.0, 255.0, 255.0])
EOF
    
    echo "$script_path"
}

#==============================================================================
# FUNCTION: Compile Single Model
#==============================================================================

compile_model() {
    local model_name=$1
    local onnx_file=$2
    
    echo "======================================================================"
    echo "🐝 Compiling: $model_name"
    echo "======================================================================"
    echo ""
    
    if [ ! -f "$onnx_file" ]; then
        echo "❌ ONNX file not found: $onnx_file"
        return 1
    fi
    
    echo "Source: $onnx_file"
    echo "Size: $(du -h $onnx_file | cut -f1)"
    echo ""
    
    # File paths
    local har_path="$OUTPUT_DIR/${model_name}.har"
    local optimized_har="$OUTPUT_DIR/${model_name}_optimized.har"
    local hef_file="$OUTPUT_DIR/${model_name}.hef"
    local model_script=$(create_model_script "$model_name")
    
    echo "📋 Model script created: $model_script"
    echo ""
    
    #--------------------------------------------------------------------------
    # Step 1: Parse ONNX to HAR
    #--------------------------------------------------------------------------
    
    echo "----------------------------------------------------------------------"
    echo "Step 1/3: Parsing ONNX → HAR"
    echo "----------------------------------------------------------------------"
    echo "⏱️  Estimated time: 30 seconds"
    echo ""
    
    hailo parser onnx "$onnx_file" \
        --hw-arch "$HW_ARCH" \
        --har-path "$har_path" \
        -y
    
    echo ""
    echo "✅ Parsing complete: $har_path"
    echo ""
    
    #--------------------------------------------------------------------------
    # Step 2: Optimize (Quantization)
    #--------------------------------------------------------------------------
    
    echo "----------------------------------------------------------------------"
    echo "Step 2/3: Optimizing (Quantization)"
    echo "----------------------------------------------------------------------"
    echo "⏱️  Estimated time: 1-2 minutes"
    echo ""
    
    if [ "$CALIB_METHOD" = "random" ]; then
        hailo optimize "$har_path" \
            --hw-arch "$HW_ARCH" \
            --use-random-calib-set \
            --output-har-path "$optimized_har"
    else
        hailo optimize "$har_path" \
            --hw-arch "$HW_ARCH" \
            --calib-set-path "$CALIB_METHOD" \
            --output-har-path "$optimized_har"
    fi
    
    echo ""
    echo "✅ Optimization complete: $optimized_har"
    echo ""
    
    #--------------------------------------------------------------------------
    # Step 3: Compile to HEF
    #--------------------------------------------------------------------------
    
    echo "----------------------------------------------------------------------"
    echo "Step 3/3: Compiling to HEF"
    echo "----------------------------------------------------------------------"
    echo "⏱️  Estimated time: 3-5 minutes"
    echo ""
    
    hailo compiler "$optimized_har" \
        --hw-arch "$HW_ARCH" \
        --model-script "$model_script" \
        --output-dir "$OUTPUT_DIR/"
    
    echo ""
    echo "✅ Compilation complete!"
    echo ""
    
    # Find the generated HEF file
    local generated_hef=$(find "$OUTPUT_DIR" -name "${model_name}*.hef" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")
    
    if [ -n "$generated_hef" ]; then
        echo "📦 HEF file: $generated_hef"
        echo "   Size: $(du -h "$generated_hef" | cut -f1)"
        echo ""
    else
        echo "⚠️  HEF file not found (may be named differently)"
    fi
}

#==============================================================================
# MAIN COMPILATION LOOP
#==============================================================================

COMPILED_COUNT=0
FAILED_COUNT=0

START_TIME=$(date +%s)

for model_name in "${!MODELS[@]}"; do
    onnx_file="${MODELS[$model_name]}"
    
    if compile_model "$model_name" "$onnx_file"; then
        ((COMPILED_COUNT++))
    else
        ((FAILED_COUNT++))
        echo "❌ Failed to compile $model_name"
    fi
    
    echo ""
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

#==============================================================================
# SUMMARY
#==============================================================================

echo "======================================================================"
echo "🎉 COMPILATION COMPLETE"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  ✅ Successfully compiled: $COMPILED_COUNT models"
echo "  ❌ Failed: $FAILED_COUNT models"
echo "  ⏱️  Total time: $(($DURATION / 60))m $(($DURATION % 60))s"
echo ""

echo "Compiled HEF files:"
find "$OUTPUT_DIR" -name "*.hef" -type f -exec ls -lh {} \;
echo ""

echo "Configuration used:"
echo "  NMS Score Threshold: $NMS_SCORE_THRESHOLD"
echo "  NMS IOU Threshold: $NMS_IOU_THRESHOLD"
echo "  Optimization Level: $OPTIMIZATION_LEVEL"
echo ""

echo "======================================================================"
echo "📤 NEXT STEPS"
echo "======================================================================"
echo ""
echo "1. Copy HEF files to Windows:"
echo "   cp $OUTPUT_DIR/*.hef /mnt/c/Users/david/Downloads/"
echo ""
echo "2. Transfer to Raspberry Pi:"
echo "   scp $OUTPUT_DIR/*.hef rpi:/tmp/bee_models_fixed/"
echo ""
echo "3. Test on Raspberry Pi:"
echo "   python3 /tmp/test_hailopython.py"
echo ""
echo "4. Verify NMS settings (on Pi):"
echo "   hailortcli parse-hef <model>.hef | grep threshold"
echo ""
echo "======================================================================"
echo "Log saved to: $LOG_FILE"
echo "======================================================================"
