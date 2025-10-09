#!/bin/bash
# Frame interpolation script for bee videos
# Doubles frame rate using motion-compensated interpolation

INPUT="$1"
OUTPUT="$2"
TARGET_FPS="${3:-120}"

if [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
    echo "Usage: $0 <input_video> <output_video> [target_fps]"
    echo ""
    echo "Interpolate video frames using motion estimation"
    echo ""
    echo "Arguments:"
    echo "  input_video  - Input video file"
    echo "  output_video - Output interpolated video"
    echo "  target_fps   - Target frame rate (default: 120)"
    echo ""
    echo "Examples:"
    echo "  # Interpolate to 120 FPS"
    echo "  $0 input.mov output_120fps.mov"
    echo ""
    echo "  # Interpolate to 240 FPS"
    echo "  $0 input.mov output_240fps.mov 240"
    echo ""
    exit 1
fi

echo "========================================"
echo "Frame Interpolation for Bee Tracking"
echo "========================================"
echo ""
echo "Input:      $INPUT"
echo "Output:     $OUTPUT"
echo "Target FPS: $TARGET_FPS"
echo ""
echo "This will take several minutes..."
echo ""

# Method 1: minterpolate (best quality, slower)
echo "[1/1] Interpolating frames with motion compensation..."
ffmpeg -i "$INPUT" \
  -filter:v "minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:fps=$TARGET_FPS'" \
  -c:v libx264 -crf 18 -preset medium \
  "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✓ Interpolation Complete!"
    echo "========================================"
    echo ""
    echo "Input:  $INPUT"
    ls -lh "$INPUT"
    echo ""
    echo "Output: $OUTPUT"
    ls -lh "$OUTPUT"
    echo ""
    echo "Now run ByteTrack on the interpolated video for better tracking!"
else
    echo ""
    echo "❌ Interpolation failed!"
    exit 1
fi
