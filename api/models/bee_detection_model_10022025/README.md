# Bee Detection Model - Training Results

## Model Performance
- mAP50: 0.589
- mAP50-95: 0.329
- Precision: 0.589
- Recall: 0.549

## Files
- `yolo11n_bee_best.pt` - PyTorch model (for testing)
- `yolo11n_bee_best.onnx` - ONNX model (for Hailo conversion)
- `labels_bee.json` - Class labels
- `training_results.png` - Training metrics
- `confusion_matrix.png` - Confusion matrix

## Deployment to Raspberry Pi

1. Convert ONNX to HEF (on your Mac):
   ```bash
   # Edit convert_onnx_to_HEF.sh to use yolo11n_bee_best.onnx
   ./api/models/convert_onnx_to_HEF.sh
   ```

2. Deploy to Pi:
   ```bash
   scp yolo11n_bee.hef labels_bee.json rpi:/tmp/
   ssh rpi "sudo mv /tmp/yolo11n_bee.* /opt/bee-monitoring/src/api/models/"
   ```

3. Test:
   ```bash
   curl "http://192.168.68.66/api/bee/ai/detect?stream_url=/opt/bee-monitoring/videos/your_bee_video.mov&ai_backend=hailo&annotate=1" -o result.jpg
   ```

## Classes Detected
{
  "0": "0",
  "1": "bee",
  "2": "pollen"
}
