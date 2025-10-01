# Degirum Manual Setup Guide

## Current Status

✅ **Degirum PySDK installed** on Raspberry Pi (v0.18.3)  
✅ **Token configured** in systemd service  
✅ **Backend code ready** and deployed  
⏳ **Model upload needed** - Manual web upload required  

## Why Manual Upload?

The Degirum Python SDK version on Pi (0.18.3) doesn't support direct model upload via API. Model compilation needs to be done through Degirum's web interface.

## Step-by-Step Model Upload

### 1. Access Degirum Platform

Go to the Degirum dashboard/portal. Common URLs:
- https://degirum.ai/
- https://app.degirum.com/
- https://cloud.degirum.ai/

Login with your account associated with token: `dg_FTiZyQ7AxrRLV1bceuGYCAvX76dq1g67sxa6H`

### 2. Upload YOLO11n Model

**Location of your model**:
```
/Users/davidgassier/digital4ai/bee-monitoring-system/api/models/yolo11n.onnx
Size: 10.2 MB
```

**Upload Settings**:
- **Model Name**: `yolo11n_bee_monitoring` (EXACT - used in code)
- **Model Type**: Object Detection / YOLO
- **Framework**: ONNX
- **Target Device**: Hailo-8L (13 TOPS)
- **Input Size**: 640x640
- **Batch Size**: 1
- **Optimization**: Standard or Balanced

### 3. Wait for Compilation

Compilation typically takes 5-30 minutes depending on:
- Model complexity
- Queue length
- Optimization level

You'll receive notification when ready.

### 4. Verify Model in Zoo

Once compiled, verify the model appears in your model zoo with:
- Name: `yolo11n_bee_monitoring`
- Status: Ready/Available
- Device: Hailo-8L

## Test Degirum Backend

Once model is uploaded and compiled:

### Check Backend Status

```bash
curl "http://192.168.68.66/api/bee/ai/status" | jq '{
  ready,
  runtime,
  backends: .backends,
  degirum: .degirum
}'
```

**Expected Output** (after model is ready):
```json
{
  "ready": true,
  "runtime": "cloud",  // or "hailo" if using local inference
  "backends": {
    "degirum": true,   // ← Should be true
    "cpu": true,
    "hailo": true
  },
  "degirum": {
    "degirum_available": true,
    "degirum_version": "0.18.3",
    "model_name": "yolo11n_bee_monitoring",
    "device": "AUTO",
    "runtime": "cloud",
    "ready": true
  }
}
```

### Test Detection

```bash
# Single frame detection
curl "http://192.168.68.66/api/bee/ai/detect?ai_backend=degirum&annotate=1" \
  -o test_degirum.jpg

# Check the image
open test_degirum.jpg
```

### Test AI Overlay on Stream

```bash
# Via dashboard: http://192.168.68.66
# - Go to Camera tab
# - Click "Show AI Detections"
# - Backend will auto-select Degirum (highest priority)

# Via API:
curl "http://192.168.68.66/api/bee/camera/stream?ai=1&ai_backend=degirum" \
  --max-time 5 -o test_stream.jpg
```

## Troubleshooting

### Model Not Found

**Error**: `Model 'yolo11n_bee_monitoring' not found`

**Solution**:
1. Check exact model name in Degirum dashboard
2. If different, update environment variable:
   ```bash
   ssh digital4ai@192.168.68.66
   sudo systemctl edit bee-api
   # Change: Environment="DEGIRUM_MODEL=actual_model_name"
   sudo systemctl daemon-reload
   sudo systemctl restart bee-api
   ```

### Connection Error

**Error**: `Failed to connect to Degirum`

**Solution**:
1. Verify token is correct in systemd
2. Check Pi has internet connection:
   ```bash
   ssh digital4ai@192.168.68.66
   ping -c 3 degirum.ai
   ```
3. Check service logs:
   ```bash
   sudo journalctl -u bee-api -f | grep -i degirum
   ```

### Slow Inference

**Symptom**: Detection takes >1 second

**Causes**:
- Using cloud inference instead of local Hailo
- Network latency

**Solution**: Force local Hailo:
```bash
ssh digital4ai@192.168.68.66
sudo systemctl edit bee-api
# Change: Environment="DEGIRUM_DEVICE=HAILO"
sudo systemctl restart bee-api
```

## Alternative: Use Existing Models

If upload is taking too long, you can test with Degirum's pre-trained models:

```python
# Edit: /opt/bee-monitoring/src/ai/degirum_backend.py
# Line 215: Change model_name default to:
model_name = os.environ.get('DEGIRUM_MODEL', 'yolov8n')  # Use pre-trained yolov8n
```

Then restart:
```bash
sudo systemctl restart bee-api
```

## Performance Expectations

| Backend | FPS | Latency | Location |
|---------|-----|---------|----------|
| CPU (ONNX) | 5-10 | 100-200ms | Local |
| Degirum Cloud | 10-20 | 50-100ms | Cloud + Network |
| Degirum Local (Hailo) | 30-60 | 16-33ms | Local on Hailo |

**Best Performance**: `DEGIRUM_DEVICE=HAILO` with local inference

## Next Steps After Upload

1. ✅ Upload model via Degirum web interface
2. ✅ Wait for compilation (5-30 minutes)
3. ✅ Test with commands above
4. ✅ Benchmark performance
5. ✅ Compare CPU vs Degirum speeds
6. ✅ Train custom bee model (future)
7. ✅ Upload custom model same way

## Support

If you need help:
- Degirum documentation: https://docs.degirum.ai/
- Degirum support: support@degirum.com
- Check service logs: `sudo journalctl -u bee-api -f`
