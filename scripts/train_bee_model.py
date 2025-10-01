#!/usr/bin/env python3
"""
Train YOLO11n model for bee detection using Roboflow dataset.

Usage:
    python train_bee_model.py --data datasets/bee-detection/data.yaml
    python train_bee_model.py --roboflow-key YOUR_API_KEY --workspace workspace --project bee-detection
"""
import argparse
import torch
from ultralytics import YOLO
import os
from pathlib import Path

def download_roboflow_dataset(api_key: str, workspace: str, project: str, version: int = 1):
    """Download dataset from Roboflow"""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("Installing roboflow...")
        os.system("pip install roboflow")
        from roboflow import Roboflow
    
    rf = Roboflow(api_key=api_key)
    project_obj = rf.workspace(workspace).project(project)
    dataset = project_obj.version(version).download("yolov8")
    
    return dataset.location

def train_bee_model(data_yaml: str, epochs: int = 100, batch: int = 16, device: str = '0'):
    """Train YOLO11n on bee dataset"""
    
    # Check GPU
    if torch.cuda.is_available():
        print(f"✓ GPU available: {torch.cuda.get_device_name(0)}")
        print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("⚠️  No GPU detected, training on CPU (will be slow)")
        device = 'cpu'
    
    # Load pretrained YOLO11n model
    print("\nLoading YOLO11n pretrained model...")
    model = YOLO('yolo11n.pt')
    
    # Training configuration
    print(f"\nTraining configuration:")
    print(f"  Dataset: {data_yaml}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch}")
    print(f"  Device: {device}")
    print(f"  Image size: 640x640")
    
    # Train
    print("\n" + "="*50)
    print("Starting training...")
    print("="*50 + "\n")
    
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=640,
        batch=batch,
        device=device,
        patience=20,
        save=True,
        project='runs/bee-detection',
        name='yolo11n-bee',
        
        # Optimization for small objects (bees)
        close_mosaic=10,
        amp=True,  # Automatic mixed precision
        
        # Data augmentation optimized for bee detection
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,      # Slight rotation for variety
        translate=0.1,
        scale=0.5,
        fliplr=0.5,        # Horizontal flip OK
        flipud=0.0,        # No vertical flip (bees upright)
        mosaic=1.0,
    )
    
    # Validate
    print("\n" + "="*50)
    print("Validating model...")
    print("="*50 + "\n")
    
    metrics = model.val()
    
    # Results
    best_model_path = Path(results.save_dir) / 'weights' / 'best.pt'
    
    print("\n" + "="*50)
    print("✓ Training Complete!")
    print("="*50)
    print(f"\nBest model: {best_model_path}")
    print(f"mAP50: {metrics.box.map50:.3f}")
    print(f"mAP50-95: {metrics.box.map:.3f}")
    print(f"\nResults saved to: {results.save_dir}")
    
    # Export to ONNX
    print("\n" + "="*50)
    print("Exporting to ONNX...")
    print("="*50 + "\n")
    
    onnx_path = export_to_onnx(best_model_path)
    
    print("\n" + "="*50)
    print("✓ All Done!")
    print("="*50)
    print(f"\nPyTorch model: {best_model_path}")
    print(f"ONNX model: {onnx_path}")
    print(f"\nNext steps:")
    print(f"  1. Test model: yolo predict model={best_model_path} source=test_image.jpg")
    print(f"  2. Convert to HEF: ./scripts/convert_onnx_to_hef.sh {onnx_path}")
    print(f"  3. Deploy to Pi: See docs/TRAIN_BEE_MODEL.md")
    
    return best_model_path, onnx_path

def export_to_onnx(model_path: str):
    """Export trained model to ONNX format"""
    model = YOLO(model_path)
    
    onnx_path = model.export(
        format='onnx',
        imgsz=640,
        simplify=True,
        dynamic=False,
        opset=11,
    )
    
    print(f"✓ ONNX exported to: {onnx_path}")
    return onnx_path

def main():
    parser = argparse.ArgumentParser(description='Train YOLO11n for bee detection')
    
    # Data source options
    parser.add_argument('--data', type=str, help='Path to data.yaml file')
    parser.add_argument('--roboflow-key', type=str, help='Roboflow API key')
    parser.add_argument('--workspace', type=str, help='Roboflow workspace name')
    parser.add_argument('--project', type=str, help='Roboflow project name')
    parser.add_argument('--version', type=int, default=1, help='Dataset version')
    
    # Training options
    parser.add_argument('--epochs', type=int, default=100, help='Training epochs')
    parser.add_argument('--batch', type=int, default=16, help='Batch size')
    parser.add_argument('--device', type=str, default='0', help='Device (0 for GPU, cpu for CPU)')
    
    args = parser.parse_args()
    
    # Determine data source
    if args.data:
        data_yaml = args.data
    elif args.roboflow_key and args.workspace and args.project:
        print("Downloading dataset from Roboflow...")
        data_location = download_roboflow_dataset(
            args.roboflow_key,
            args.workspace,
            args.project,
            args.version
        )
        data_yaml = os.path.join(data_location, 'data.yaml')
        print(f"✓ Dataset downloaded to: {data_location}")
    else:
        print("Error: Either --data or Roboflow credentials required")
        print("\nExamples:")
        print("  python train_bee_model.py --data datasets/bee-detection/data.yaml")
        print("  python train_bee_model.py --roboflow-key KEY --workspace ws --project bee-detection")
        return
    
    # Verify data.yaml exists
    if not os.path.exists(data_yaml):
        print(f"Error: data.yaml not found: {data_yaml}")
        return
    
    # Train
    train_bee_model(data_yaml, args.epochs, args.batch, args.device)

if __name__ == '__main__':
    main()
