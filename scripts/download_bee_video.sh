#!/bin/bash
# Download bee monitoring video samples for testing

set -e

echo "=========================================="
echo "Bee Video Sample Downloader"
echo "=========================================="
echo ""

# Create videos directory
VIDEOS_DIR="/tmp/bee_videos"
mkdir -p "$VIDEOS_DIR"

echo "Videos will be saved to: $VIDEOS_DIR"
echo ""

# Option 1: Download from YouTube (requires yt-dlp)
download_youtube() {
    local url="$1"
    local output="$2"
    
    echo "Downloading from YouTube: $url"
    
    if command -v yt-dlp &> /dev/null; then
        # Download best quality up to 720p (good balance)
        yt-dlp -f "best[height<=720]" \
               --output "$output" \
               --no-playlist \
               --quiet \
               --progress \
               "$url"
        echo "✓ Downloaded: $output"
    else
        echo "⚠️  yt-dlp not installed. Install with: pip3 install yt-dlp"
        echo "   Or: brew install yt-dlp"
        return 1
    fi
}

# Option 2: Download sample videos directly
download_sample() {
    local url="$1"
    local output="$2"
    
    echo "Downloading sample: $url"
    curl -L "$url" -o "$output" --progress-bar
    echo "✓ Downloaded: $output"
}

echo "[1/3] Downloading test videos..."
echo ""

# Sample 1: Big Buck Bunny (for testing detection)
echo "1. Big Buck Bunny (test video):"
download_sample \
    "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" \
    "$VIDEOS_DIR/test_bunny.mp4"
echo ""

# Sample 2: Try to download explore.org bee cam clip (if URL is public)
echo "2. Bee monitoring samples:"
echo "   - For real bee footage, use yt-dlp with explore.org YouTube channel"
echo "   - Example: https://www.youtube.com/c/ExploreLiveCams"
echo ""

# Sample 3: Public domain bee videos
echo "3. Alternative bee video sources:"
echo "   - Pexels: https://www.pexels.com/search/videos/bees/"
echo "   - Pixabay: https://pixabay.com/videos/search/bees/"
echo ""

# If yt-dlp is installed, offer to download from YouTube
if command -v yt-dlp &> /dev/null; then
    echo "yt-dlp is installed!"
    echo ""
    echo "Download bee footage from YouTube? (y/n)"
    read -r response
    
    if [[ "$response" == "y" ]]; then
        echo "Enter YouTube URL (or press Enter to skip):"
        read -r youtube_url
        
        if [[ -n "$youtube_url" ]]; then
            download_youtube "$youtube_url" "$VIDEOS_DIR/bee_footage.mp4"
        fi
    fi
else
    echo "💡 Install yt-dlp to download from YouTube:"
    echo "   pip3 install yt-dlp"
    echo "   OR"
    echo "   brew install yt-dlp"
fi

echo ""
echo "=========================================="
echo "✓ Download complete!"
echo "=========================================="
echo ""
echo "Videos saved to: $VIDEOS_DIR"
ls -lh "$VIDEOS_DIR"
echo ""

echo "Test detection with:"
echo "  curl 'http://192.168.68.66/api/bee/ai/detect?stream_url=file://$VIDEOS_DIR/test_bunny.mp4&ai_backend=hailo&annotate=1' -o result.jpg"
echo ""
echo "Or copy to Pi and use local path:"
echo "  scp $VIDEOS_DIR/*.mp4 rpi:/tmp/"
echo "  ssh rpi"
echo "  curl 'http://localhost/api/bee/ai/detect?stream_url=file:///tmp/test_bunny.mp4&ai_backend=hailo&annotate=1' -o /tmp/result.jpg"
