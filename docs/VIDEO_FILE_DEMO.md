# Video File Demo Guide

**Best Practice: Use video files instead of live streams for demos!**

Video files are more reliable than internet streams because:
- ✅ No expiration issues (streaming URLs expire quickly)
- ✅ No network latency or buffering
- ✅ Repeatable testing on same content
- ✅ Works offline
- ✅ Can process frame-by-frame

## Quick Start

### 1. Download a Bee Video

```bash
# Option A: Use yt-dlp to download from YouTube
pip3 install yt-dlp

# Download explore.org bee cam recording
yt-dlp -f "best[height<=720]" \
       -o bee_footage.mp4 \
       "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

# Option B: Download from Pexels/Pixabay (free stock videos)
curl -L "https://example.com/bee-video.mp4" -o bee_video.mp4

# Option C: Use test video
curl -L "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" \
     -o test_video.mp4
```

### 2. Copy to Raspberry Pi

```bash
# Create videos directory on Pi
ssh rpi "sudo mkdir -p /opt/bee-monitoring/videos"

# Copy video file
scp bee_video.mp4 rpi:/tmp/

# Move to correct location with proper permissions
ssh rpi "sudo mv /tmp/bee_video.mp4 /opt/bee-monitoring/videos/ && \
         sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/videos/bee_video.mp4"
```

### 3. Run Detection

```bash
# Single frame detection
curl "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/bee_video.mp4&\
ai_backend=hailo&\
annotate=1" -o detection.jpg

# JSON results
curl "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/bee_video.mp4&\
ai_backend=hailo" | jq
```

## Complete Workflow Script

Save this as `demo_video.sh`:

```bash
#!/bin/bash
# Complete video file demo workflow

VIDEO_NAME="bee_demo.mp4"
VIDEO_URL="YOUR_VIDEO_URL_HERE"
PI_HOST="192.168.68.66"

echo "=== Video File Demo Workflow ==="
echo ""

# Step 1: Download video
echo "[1/4] Downloading video..."
curl -L "$VIDEO_URL" -o "/tmp/$VIDEO_NAME" --progress-bar

# Step 2: Copy to Pi
echo "[2/4] Copying to Raspberry Pi..."
scp "/tmp/$VIDEO_NAME" "rpi:/tmp/"

# Step 3: Set up on Pi with correct permissions
echo "[3/4] Setting up on Pi..."
ssh rpi "sudo mkdir -p /opt/bee-monitoring/videos && \
         sudo mv /tmp/$VIDEO_NAME /opt/bee-monitoring/videos/ && \
         sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/videos/$VIDEO_NAME"

# Step 4: Run detection
echo "[4/4] Running Hailo AI detection..."
curl -sS "http://$PI_HOST/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/$VIDEO_NAME&\
ai_backend=hailo&\
annotate=1" -o detection_result.jpg

echo ""
echo "✓ Complete! Results saved to: detection_result.jpg"
echo ""

# Show detection stats
echo "Detection results:"
curl -sS "http://$PI_HOST/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/$VIDEO_NAME&\
ai_backend=hailo" | jq '{
  backend: .backend,
  detection_count: (.detections | length),
  classes: [.detections[].class_name] | unique
}'
```

## Finding Bee Videos

### YouTube Channels

1. **explore.org Live Cams**
   - Channel: https://www.youtube.com/c/ExploreLiveCams
   - Has bee cam recordings and highlights

2. **Search for bee monitoring videos**
   ```bash
   # Search YouTube
   yt-dlp "ytsearch:bee hive monitoring camera"
   
   # Download first result
   yt-dlp -f "best[height<=720]" "ytsearch1:bee hive monitoring"
   ```

### Free Stock Video Sites

1. **Pexels Videos**
   - https://www.pexels.com/search/videos/bees/
   - Free to download, no attribution required

2. **Pixabay Videos**
   - https://pixabay.com/videos/search/bees/
   - Free for commercial use

3. **Videvo**
   - https://www.videvo.net/free-stock-video-footage/bees/
   - Free HD videos

## Process Multiple Frames

To process multiple frames from a video (not just first frame):

```python
import cv2
import requests
import base64
import json

video_path = "/opt/bee-monitoring/videos/bee_video.mp4"
cap = cv2.VideoCapture(video_path)

frame_count = 0
detections_per_frame = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # Process every 30th frame (1 per second at 30fps)
    if frame_count % 30 == 0:
        # Encode frame
        _, buffer = cv2.imencode('.jpg', frame)
        
        # Send to API (would need to add frame upload endpoint)
        # Or save frames and process individually
        
        print(f"Frame {frame_count} processed")
    
    frame_count += 1

cap.release()
```

## Troubleshooting

### Video File Won't Open

**Issue**: `Failed to open stream: /path/to/video.mp4`

**Solution**: Check permissions
```bash
# Ensure bee-monitor user can read the file
ssh rpi "sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/videos/*.mp4"
ssh rpi "sudo chmod 644 /opt/bee-monitoring/videos/*.mp4"
```

### Video Format Not Supported

**Issue**: OpenCV can't decode the video

**Solution**: Convert to compatible format
```bash
# Convert to H.264 MP4 (widely compatible)
ffmpeg -i input.mov -c:v libx264 -c:a aac -movflags +faststart output.mp4
```

### File Too Large

**Issue**: Video file is very large

**Solution**: Reduce resolution/bitrate
```bash
# Compress to 720p
ffmpeg -i input.mp4 -vf scale=-1:720 -c:v libx264 -crf 23 output.mp4
```

## Performance Comparison

### Stream URL (Problems)
- ❌ URLs expire quickly
- ❌ Network latency (2-10s)
- ❌ Buffering issues
- ❌ Authentication issues

### Video File (Recommended!)
- ✅ Always available
- ✅ No latency
- ✅ Repeatable
- ✅ Offline capable
- ✅ Frame-perfect control

## Example: Complete Demo with Real Bee Footage

```bash
#!/bin/bash
# Demo with actual bee footage

# 1. Download bee hive video from Pexels
echo "Downloading bee hive video..."
curl -L "https://player.vimeo.com/external/[VIDEO_ID].hd.mp4" \
     -o bee_hive.mp4

# 2. Upload to Pi
scp bee_hive.mp4 rpi:/tmp/
ssh rpi "sudo mv /tmp/bee_hive.mp4 /opt/bee-monitoring/videos/ && \
         sudo chown bee-monitor:bee-monitor /opt/bee-monitoring/videos/bee_hive.mp4"

# 3. Run Hailo AI detection
echo "Running AI detection on bee footage..."
curl "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/bee_hive.mp4&\
ai_backend=hailo&\
conf=0.15&\
annotate=1" -o bee_detection.jpg

echo "✓ Saved annotated image to: bee_detection.jpg"

# 4. Show results
curl -sS "http://192.168.68.66/api/bee/ai/detect?\
stream_url=/opt/bee-monitoring/videos/bee_hive.mp4&\
ai_backend=hailo&\
conf=0.15" | jq
```

## Recommended Videos

Current test video on Pi:
```bash
/opt/bee-monitoring/videos/test_video.mp4  # Big Buck Bunny (151MB)
```

For bee-specific demos, download:
1. Bee hive entrance monitoring footage
2. Bee foraging on flowers
3. Beehive internal camera footage

All available from free stock video sites!
