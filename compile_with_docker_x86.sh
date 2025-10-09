#!/bin/bash
#
# Compile Bee Models using Docker x86_64 Environment
# For Apple Silicon Macs (runs x86_64 via emulation)
#
# Date: October 9, 2025
#

set -e

echo "======================================================================"
echo "🐝 HAILO MODEL COMPILATION - Docker x86_64"
echo "======================================================================"
echo ""
echo "Hardware: Apple M3 (ARM64) → Running x86_64 via Docker emulation"
echo "Target: Hailo-8L (13 TOPS)"
echo "Fix: score_threshold=0.15 (was 0.30)"
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
MODEL_DIR="$PROJECT_ROOT/api/models"
OUTPUT_DIR="$MODEL_DIR/recompiled_fixed"
DFC_WHEEL="hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl"

echo "📁 Project: $PROJECT_ROOT"
echo "📦 Models: $MODEL_DIR"
echo "💾 Output: $OUTPUT_DIR"
echo ""

# Check if DFC wheel exists
if [ ! -f "$PROJECT_ROOT/$DFC_WHEEL" ]; then
    echo "❌ DFC wheel not found: $PROJECT_ROOT/$DFC_WHEEL"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "🐳 Creating Dockerfile..."

# Create Dockerfile
cat > "$PROJECT_ROOT/Dockerfile.hailo" << 'DOCKERFILE'
FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    unzip \
    graphviz \
    graphviz-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /workspace

# Copy DFC wheel
COPY hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl /workspace/

# Create virtual environment and install DFC
RUN python3 -m venv /workspace/hailo_venv && \
    . /workspace/hailo_venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl

# Install hailortcli (if available in the wheel)
RUN . /workspace/hailo_venv/bin/activate && \
    pip list | grep hailo || true

# Set up environment
ENV PATH="/workspace/hailo_venv/bin:$PATH"

CMD ["/bin/bash"]
DOCKERFILE

echo "✅ Dockerfile created"
echo ""

echo "🔨 Building Docker image (this may take a few minutes)..."
docker build --platform linux/amd64 -t hailo-compiler -f "$PROJECT_ROOT/Dockerfile.hailo" "$PROJECT_ROOT"

echo ""
echo "✅ Docker image built successfully!"
echo ""

#------------------------------------------------------------------------------
# Create compilation script
#------------------------------------------------------------------------------
cat > "$OUTPUT_DIR/compile_models.sh" << 'COMPILE_SCRIPT'
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
COMPILE_SCRIPT

chmod +x "$OUTPUT_DIR/compile_models.sh"

echo "======================================================================"
echo "🚀 RUNNING COMPILATION IN DOCKER"
echo "======================================================================"
echo ""
echo "⚠️  This will take 2-3 hours. The process includes:"
echo "   1. Parsing ONNX models"
echo "   2. Optimizing for Hailo-8L"
echo "   3. Compiling with NMS (threshold=0.15)"
echo ""
echo "You can monitor progress in the terminal..."
echo ""

# Run Docker container with compilation
docker run --rm -it \
    --platform linux/amd64 \
    -v "$MODEL_DIR:/models" \
    -v "$OUTPUT_DIR:/output" \
    hailo-compiler \
    bash /output/compile_models.sh

echo ""
echo "======================================================================"
echo "🎉 SUCCESS! MODELS COMPILED!"
echo "======================================================================"
echo ""
echo "Compiled HEF files:"
ls -lh "$OUTPUT_DIR"/*.hef
echo ""
echo "Next steps:"
echo "  1. Copy to Raspberry Pi:"
echo "     scp $OUTPUT_DIR/*.hef rpi:/tmp/bee_models_fixed/"
echo ""
echo "  2. Test on Pi:"
echo "     python3 /tmp/test_hailopython.py bee_best image"
echo ""
echo "  3. Expected: 🐝 DETECTIONS! 🎉"
echo ""
echo "======================================================================"
