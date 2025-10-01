#!/bin/bash
# Test livestream integration with the bee monitoring system

PI_HOST="${1:-192.168.68.66}"

echo "=============================================="
echo "Livestream Integration Test"
echo "=============================================="
echo ""

# Test 1: Local camera (baseline)
echo "[1/3] Testing local camera baseline..."
curl -sS "http://${PI_HOST}/api/bee/ai/detect?ai_backend=hailo" | jq '{backend, detection_count: (.detections | length)}'
echo ""

# Test 2: Sample video URL (if available)
echo "[2/3] Testing with sample stream URL..."
echo "Note: You'll need to provide a valid stream URL"
echo ""
echo "Example test stream URLs:"
echo "  - Big Buck Bunny (MP4): http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
echo "  - Test RTSP stream: rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
echo ""

# If you have a stream URL, uncomment and modify:
# STREAM_URL="http://your-stream-url-here.m3u8"
# curl -sS "http://${PI_HOST}/api/bee/ai/detect?ai_backend=hailo&stream_url=${STREAM_URL}" \
#   | jq '{backend, detection_count: (.detections | length), first_detection: .detections[0]}'

echo "[3/3] How to get explore.org bee cam stream:"
echo "  1. Visit: https://explore.org/livecams/player/honey-bees/honey-bee-landing-zone-cam"
echo "  2. Open browser DevTools (F12) -> Network tab"
echo "  3. Filter for '.m3u8'"
echo "  4. Reload page and copy the M3U8 URL"
echo "  5. Test with:"
echo "     curl 'http://${PI_HOST}/api/bee/ai/detect?stream_url=STREAM_URL&ai_backend=hailo&annotate=1' -o test.jpg"
echo ""

echo "✓ Test complete!"
echo ""
echo "Next steps:"
echo "  1. Extract stream URL from explore.org (see instructions above)"
echo "  2. Test detection: curl 'http://${PI_HOST}/api/bee/ai/detect?stream_url=URL&annotate=1' -o bee.jpg"
echo "  3. View docs: cat docs/LIVESTREAM_DEMO.md"
