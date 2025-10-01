# Internet Livestream Demo Guide

This guide shows how to use external video streams (internet livestreams, YouTube, RTSP, etc.) as input for the bee monitoring system instead of the local Raspberry Pi camera.

## Quick Start

### 1. Using Stream URL Parameter

The simplest way is to use the `stream_url` parameter with the detection endpoint:

```bash
# Test with a livestream URL
curl "http://192.168.68.66/api/bee/ai/detect?ai_backend=hailo&stream_url=STREAM_URL&annotate=1" \
  -o detection.jpg

# Example with explore.org bee cam (M3U8 stream)
curl "http://192.168.68.66/api/bee/ai/detect?ai_backend=hailo&stream_url=https://explore.org/live-cams/bee-cam.m3u8&annotate=1" \
  -o bee_detection.jpg
```

### 2. Supported Stream Formats

The system supports any format that OpenCV's `VideoCapture` can handle:

- **HLS Streams** (.m3u8) - Most livestreaming platforms
- **RTSP Streams** (rtsp://) - IP cameras, security cameras
- **HTTP Video** (.mp4, .mjpg) - Direct video files
- **YouTube Streams** (requires yt-dlp)

## Example Bee Livestreams

### explore.org Bee Cameras

1. **Honey Bee Landing Zone Cam**
   - Page: https://explore.org/livecams/player/honey-bees/honey-bee-landing-zone-cam
   - To extract stream URL:
     ```bash
     # Manual method: Use browser dev tools (Network tab)
     # Or use the extraction script:
     python3 scripts/extract_explore_stream.py
     ```

2. **Direct M3U8 streams** (if available):
   ```bash
   # Once you have the .m3u8 URL from browser inspection:
   STREAM_URL="https://...file.m3u8"
   
   # Test detection
   curl "http://192.168.68.66/api/bee/ai/detect?stream_url=$STREAM_URL&ai_backend=hailo&annotate=1" \
     -o bee_test.jpg
   ```

### YouTube Livestreams

For YouTube streams, install `yt-dlp` on the Pi first:

```bash
ssh rpi
sudo pip3 install yt-dlp

# Then use YouTube URL directly:
```

```bash
YOUTUBE_URL="https://www.youtube.com/watch?v=YOUR_STREAM_ID"

curl "http://192.168.68.66/api/bee/ai/detect?stream_url=$YOUTUBE_URL&ai_backend=hailo" \
  | jq '.detections'
```

## Extracting Stream URLs

### Method 1: Browser Developer Tools

1. Open the livestream page in your browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Filter for `.m3u8` or `video`
5. Refresh the page
6. Look for the master playlist URL
7. Copy the URL and use it with `stream_url` parameter

### Method 2: Stream Extraction Script

```bash
# Use the provided script
python3 scripts/extract_explore_stream.py

# This will output the stream URL
```

### Method 3: youtube-dl / yt-dlp

```bash
# Install yt-dlp
pip3 install yt-dlp

# Extract stream URL
yt-dlp -g "https://www.youtube.com/watch?v=VIDEO_ID"

# Or get best quality
yt-dlp -f best -g "STREAM_URL"
```

## Testing Stream URLs

### Quick Test with ffplay

```bash
# Test if stream is accessible
ffplay "STREAM_URL"

# Or with VLC
vlc "STREAM_URL"
```

### Test with API

```bash
# Test stream connectivity
curl "http://192.168.68.66/api/stream/test?url=STREAM_URL" | jq

# Expected response:
{
  "success": true,
  "url": "...",
  "width": 1920,
  "height": 1080,
  "fps": 30.0
}
```

## Performance Considerations

### Stream Quality vs. Performance

- **Low resolution** (480p-720p): Best for real-time detection
- **High resolution** (1080p+): May need throttling

### Bandwidth

External streams consume bandwidth on your Pi:
- **480p**: ~1-2 Mbps
- **720p**: ~3-5 Mbps
- **1080p**: ~5-8 Mbps

### Latency

- Local camera: ~100-200ms
- Internet stream: 2-10 seconds (depending on source)

## Advanced Usage

### Continuous Stream Monitoring

```bash
# Monitor stream continuously (every 5 seconds)
while true; do
  curl -sS "http://192.168.68.66/api/bee/ai/detect?stream_url=STREAM_URL&ai_backend=hailo" \
    | jq '{detections: .detections | length, timestamp: .timestamp}'
  sleep 5
done
```

### Custom Stream Proxy

See `api/routes/stream_proxy.py` for advanced stream handling:

```python
# GET /api/stream/frame?url=STREAM_URL
# GET /api/stream/test?url=STREAM_URL
# GET /api/stream/info
# POST /api/stream/close
```

## Troubleshooting

### Stream Won't Open

1. **Check URL format**: Must be direct stream URL (not webpage)
2. **Test with ffplay**: `ffplay "STREAM_URL"`
3. **Check firewall**: Ensure Pi can access internet
4. **Check codecs**: Some streams need additional codecs

### Poor Detection Quality

1. **Check resolution**: Too high may slow down
2. **Check FPS**: Some streams have variable FPS
3. **Adjust confidence**: `?conf=0.15` for more detections
4. **Use Hailo backend**: `?ai_backend=hailo` for faster processing

### High Latency

- Internet streams have inherent delay (2-10s)
- For real-time monitoring, use local camera
- For demos/testing, internet streams are fine

## Examples

### Complete Demo Script

```bash
#!/bin/bash
# demo_livestream.sh

# Explore.org bee cam stream URL (you'll need to extract this)
STREAM_URL="https://stream-url-here.m3u8"

echo "Testing Hailo AI on livestream..."

# Single frame detection
echo "1. Single frame detection:"
curl -sS "http://192.168.68.66/api/bee/ai/detect?stream_url=$STREAM_URL&ai_backend=hailo&annotate=1" \
  -o frame1.jpg
echo "Saved to frame1.jpg"

# Get detection count
echo -e "\n2. Detection results:"
curl -sS "http://192.168.68.66/api/bee/ai/detect?stream_url=$STREAM_URL&ai_backend=hailo" \
  | jq '{backend, detection_count: (.detections | length), detections: .detections[:3]}'

# Continuous monitoring
echo -e "\n3. Continuous monitoring (Ctrl+C to stop):"
while true; do
  RESULT=$(curl -sS "http://192.168.68.66/api/bee/ai/detect?stream_url=$STREAM_URL&ai_backend=hailo")
  COUNT=$(echo $RESULT | jq '.detections | length')
  TIME=$(echo $RESULT | jq -r '.timestamp')
  echo "[$TIME] Detected: $COUNT objects"
  sleep 3
done
```

## Recommendations from Research

Based on analysis of Hailo and Ultralytics documentation:

### Performance Optimizations

1. **Use lower confidence thresholds** for bees (smaller objects)
   ```bash
   ?conf=0.15&iou=0.5
   ```

2. **Batch processing** for multiple frames (not yet implemented)
   - Could achieve 30-60 FPS with Hailo-8L

3. **Model fine-tuning** for bee-specific detection
   - See: hailo-ai/hailo_model_zoo for training pipeline
   - Custom HEF compilation: `api/models/convert_onnx_to_HEF.sh`

### Future Enhancements

From hailo-rpi5-examples repo:
- GStreamer pipelines for hardware-accelerated video processing
- Multi-stream support (multiple cameras)
- Object tracking (not just detection)
- Custom post-processing in C++ for even faster inference

From ultralytics docs:
- YOLO11 supports streaming mode natively
- Can use `stream=True` for continuous inference
- Supports URL sources out of the box

## Links

- Hailo RPi5 Examples: https://github.com/hailo-ai/hailo-rpi5-examples
- Ultralytics Docs: https://docs.ultralytics.com
- explore.org Bee Cams: https://explore.org/livecams/honey-bees
