from ultralytics import YOLO

# Re-export YOLOv8n to ONNX with opset 11 for IR v10 compatibility
# This ensures compatibility with the Pi's onnxruntime build
model = YOLO('yolov8n.pt')
model.export(
    format='onnx',
    imgsz=640,
    opset=11,          # opset 11 -> IR v10 compatible
    optimize=True,
    half=False,        # Use FP32 for compatibility
    dynamic=False,     # Static input size
    simplify=True,
)
print("Model exported to yolov8n.onnx (IR v10 compatible)")