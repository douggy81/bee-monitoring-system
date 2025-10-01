#!/usr/bin/env python3
"""
Download YOLO11n model and export to ONNX format.
Requires: pip install ultralytics>=8.3.0
"""
import os
import sys

try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: ultralytics not found. Install with: pip install 'ultralytics>=8.3.0'")
    sys.exit(1)

def main():
    # Output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    models_dir = os.path.join(project_root, "api", "models")
    os.makedirs(models_dir, exist_ok=True)
    
    pt_path = os.path.join(models_dir, "yolo11n.pt")
    onnx_path = os.path.join(models_dir, "yolo11n.onnx")
    
    print("=" * 60)
    print("YOLO11n Model Download and Export")
    print("=" * 60)
    
    # Download YOLOv11n if not exists
    if not os.path.exists(pt_path):
        print(f"\n[1/2] Downloading YOLO11n to {pt_path}...")
        try:
            model = YOLO("yolo11n.pt")
            # Save to our models directory
            model.export(format="pytorch")
            # Move to correct location if needed
            if os.path.exists("yolo11n.pt") and not os.path.exists(pt_path):
                os.rename("yolo11n.pt", pt_path)
        except Exception as e:
            print(f"ERROR downloading YOLOv11n: {e}")
            print("\nTrying alternative approach...")
            # Try loading which will auto-download
            model = YOLO("yolo11n")  # Will download from ultralytics
            model.save(pt_path)
    else:
        print(f"\n[1/2] YOLO11n already exists at {pt_path}")
        model = YOLO(pt_path)
    
    # Export to ONNX
    if not os.path.exists(onnx_path):
        print(f"\n[2/2] Exporting to ONNX format: {onnx_path}...")
        try:
            model.export(
                format="onnx",
                imgsz=640,
                simplify=True,
                opset=12,  # Compatible with ONNXRuntime 1.22.1
            )
            # Move exported file to correct location
            exported_onnx = pt_path.replace(".pt", ".onnx")
            if os.path.exists(exported_onnx) and not os.path.exists(onnx_path):
                os.rename(exported_onnx, onnx_path)
            print(f"✓ ONNX export successful: {onnx_path}")
        except Exception as e:
            print(f"ERROR exporting to ONNX: {e}")
            sys.exit(1)
    else:
        print(f"\n[2/2] ONNX model already exists at {onnx_path}")
    
    print("\n" + "=" * 60)
    print("✓ YOLO11n setup complete!")
    print("=" * 60)
    print(f"\nPyTorch model: {pt_path}")
    print(f"ONNX model:    {onnx_path}")
    print("\nNext: Convert ONNX to HEF for Hailo AI HAT+")
    print(f"  Run: python3 scripts/convert_yolo11n_to_hef.py")
    print("\nOr deploy ONNX to Raspberry Pi for CPU inference:")
    print(f"  scp {onnx_path} digital4ai@192.168.68.66:/home/digital4ai/")
    print("  ssh digital4ai@192.168.68.66")
    print("  sudo install -o bee-monitor -g bee-monitor -m 0644 ~/yolo11n.onnx /opt/bee-monitoring/src/api/models/")
    print("  sudo systemctl restart bee-api")

if __name__ == "__main__":
    main()
