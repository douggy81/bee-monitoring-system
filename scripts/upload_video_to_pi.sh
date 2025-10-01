#!/bin/bash
# Upload video file to Pi for demo/testing

if [ -z "$1" ]; then
    echo "Usage: $0 <video_file> [video_name]"
    echo ""
    echo "Example:"
    echo "  $0 ~/Downloads/bee_video.mp4"
    echo "  $0 bee_footage.mp4 my_bees.mp4"
    echo ""
    exit 1
fi

VIDEO_FILE="$1"
VIDEO_NAME="${2:-$(basename "$VIDEO_FILE")}"
PI_HOST="${PI_HOST:-rpi}"

if [ ! -f "$VIDEO_FILE" ]; then
    echo "Error: Video file not found: $VIDEO_FILE"
    exit 1
fi

echo "=========================================="
echo "Upload Video to Raspberry Pi"
echo "=========================================="
echo ""
echo "Video file: $VIDEO_FILE"
echo "Video name: $VIDEO_NAME"
echo "Pi host:    $PI_HOST"
echo ""

# Upload to Pi
echo "[1/3] Uploading to Pi..."
scp "$VIDEO_FILE" "$PI_HOST:/tmp/$VIDEO_NAME"

# Move to videos directory with correct permissions
echo "[2/3] Setting up on Pi..."
ssh "$PI_HOST" "sudo mkdir -p /opt/bee-monitoring/videos && \
                sudo mv /tmp/$VIDEO_NAME /opt/bee-monitoring/videos/ && \
                sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/videos/$VIDEO_NAME && \
                sudo chmod 644 /opt/bee-monitoring/videos/$VIDEO_NAME"

# Verify
echo "[3/3] Verifying..."
ssh "$PI_HOST" "ls -lh /opt/bee-monitoring/videos/$VIDEO_NAME"

echo ""
echo "✓ Upload complete!"
echo ""
echo "Test detection with:"
echo "  curl 'http://\$(hostname -I | awk '{print \$1}')/api/bee/ai/detect?stream_url=/opt/bee-monitoring/videos/$VIDEO_NAME&ai_backend=hailo&annotate=1' -o result.jpg"
echo ""
echo "Or from Pi:"
echo "  ssh $PI_HOST"
echo "  curl 'http://localhost/api/bee/ai/detect?stream_url=/opt/bee-monitoring/videos/$VIDEO_NAME&ai_backend=hailo&annotate=1' -o /tmp/result.jpg"
