# create convert_to_onnx.py
from ultralytics import YOLO
import torch

# Load the model
model = YOLO('yolov8n.pt')

# Export to ONNX format
model.export(
    format='onnx',
    imgsz=640,  # Input image size
    optimize=True,
    half=False,  # Use FP32 for better compatibility
    dynamic=False,  # Static input size for Hailo
    simplify=True
)

print("Model exported to yolov8n.onnx")