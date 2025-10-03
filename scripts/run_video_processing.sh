#!/bin/bash
# Helper script to process bee video on Raspberry Pi

PI_HOST="${PI_HOST:-rpi}"
INPUT_VIDEO="$1"
OUTPUT_VIDEO="$2"
BACKEND="${3:-hailo}"
CONF="${4:-0.25}"

if [ -z "$INPUT_VIDEO" ] || [ -z "$OUTPUT_VIDEO" ]; then
    echo "Usage: $0 <input_video> <output_video> [backend] [confidence]"
    echo ""
    echo "Process a bee video with detection overlay on the Raspberry Pi"
    echo ""
    echo "Arguments:"
    echo "  input_video   - Path to input video on Pi (e.g., /opt/bee-monitoring/videos/your_bee_video.mov)"
    echo "  output_video  - Path for output video on Pi (e.g., /tmp/bee_output.mp4)"
    echo "  backend       - Detection backend: hailo (default) or cpu"
    echo "  confidence    - Confidence threshold (default: 0.25)"
    echo ""
    echo "Examples:"
    echo "  # Process with Hailo backend (fastest)"
    echo "  $0 /opt/bee-monitoring/videos/your_bee_video.mov /tmp/output.mp4"
    echo ""
    echo "  # Process with CPU backend"
    echo "  $0 /opt/bee-monitoring/videos/your_bee_video.mov /tmp/output.mp4 cpu"
    echo ""
    echo "  # Lower confidence to detect more bees"
    echo "  $0 /opt/bee-monitoring/videos/your_bee_video.mov /tmp/output.mp4 hailo 0.15"
    echo ""
    echo "  # Process first 300 frames only (testing)"
    echo "  ssh $PI_HOST 'cd /opt/bee-monitoring/src && python3 scripts/process_bee_video_local.py /opt/bee-monitoring/videos/your_bee_video.mov /tmp/output.mp4 --max-frames 300'"
    echo ""
    exit 1
fi

echo "=========================================="
echo "Bee Video Processing"
echo "=========================================="
echo ""
echo "Input:      $INPUT_VIDEO"
echo "Output:     $OUTPUT_VIDEO"
echo "Backend:    $BACKEND"
echo "Confidence: $CONF"
echo "Pi Host:    $PI_HOST"
echo ""

# Deploy script to Pi
echo "[1/3] Deploying processing script to Pi..."
scp scripts/process_bee_video_local.py "$PI_HOST:/tmp/"
ssh "$PI_HOST" "sudo install -o bee-monitor -g bee-monitor -m 0755 /tmp/process_bee_video_local.py /opt/bee-monitoring/src/scripts/"
echo "✓ Script deployed"
echo ""

# Run processing on Pi
echo "[2/3] Processing video on Pi (this may take a while)..."
echo ""
ssh "$PI_HOST" "cd /opt/bee-monitoring/src && python3 scripts/process_bee_video_local.py '$INPUT_VIDEO' '$OUTPUT_VIDEO' --backend $BACKEND --conf $CONF"

if [ $? -eq 0 ]; then
    echo ""
    echo "[3/3] Downloading processed video..."
    OUTPUT_BASENAME=$(basename "$OUTPUT_VIDEO")
    scp "$PI_HOST:$OUTPUT_VIDEO" "./$OUTPUT_BASENAME"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "✓ Processing Complete!"
        echo "=========================================="
        echo ""
        echo "Output video saved to: ./$OUTPUT_BASENAME"
        echo ""
        echo "Opening video..."
        open "./$OUTPUT_BASENAME" 2>/dev/null || echo "Open ./$OUTPUT_BASENAME to view"
    else
        echo "Failed to download video. It's still on the Pi at: $OUTPUT_VIDEO"
    fi
else
    echo ""
    echo "❌ Processing failed. Check error messages above."
    exit 1
fi
