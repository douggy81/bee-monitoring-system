#!/usr/bin/env python3
"""
Train YOLO11m (medium) model for bee detection using Roboflow dataset.

YOLO11m is ~3x larger than 11n but provides better accuracy for small objects.

Usage:
    python train_yolo11m_bee.py --roboflow-key YOUR_KEY --workspace WORKSPACE --project PROJECT
    python train_yolo11m_bee.py --data datasets/bee-detection/data.yaml
"""
import argparse
import torch
from ultralytics import YOLO
import os
from pathlib import Path
import time

def download_roboflow_dataset(api_key: str, workspace: str, project: str, version: int = 1):
    """Download dataset from Roboflow"""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("📦 Installing roboflow...")
        os.system("pip install roboflow")
        from roboflow import Roboflow
    
    print(f"\n📥 Downloading dataset from Roboflow...")
    print(f"   Workspace: {workspace}")
    print(f"   Project: {project}")
    print(f"   Version: {version}")
    
    rf = Roboflow(api_key=api_key)
    project_obj = rf.workspace(workspace).project(project)
    dataset = project_obj.version(version).download("yolov11")  # Use yolov11 format
    
    print(f"✅ Dataset downloaded to: {dataset.location}")
    return dataset.location

def train_yolo11m_bee(data_yaml: str, epochs: int = 100, imgsz: int = 640, batch: int = 16, device: str = '0'):
    """Train YOLO11m on bee dataset"""
    
    print("\n" + "="*70)
    print("🐝 YOLO11m BEE DETECTION TRAINING")
    print("="*70)
    
    # Check GPU
    if torch.cuda.is_available():
        print(f"\n✅ GPU available: {torch.cuda.get_device_name(0)}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        device = '0'
    elif torch.backends.mps.is_available():
        print(f"\n✅ Apple Silicon GPU (MPS) available")
        device = 'mps'
    else:
        print("\n⚠️  No GPU detected, training on CPU (will be VERY slow)")
        device = 'cpu'
    
    # Load pretrained YOLO11m model
    print("\n📦 Loading YOLO11m pretrained model...")
    model = YOLO('yolo11m.pt')  # Will auto-download if not present
    
    # Adjust batch size based on GPU memory
    if device != 'cpu':
        gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 16
        if gpu_mem_gb < 8:
            batch = 8
            print(f"⚠️  Low GPU memory detected, reducing batch size to {batch}")
        elif gpu_mem_gb >= 16:
            batch = 32
            print(f"✨ High GPU memory detected, increasing batch size to {batch}")
    
    # Training configuration
    print(f"\n🔧 Training configuration:")
    print(f"   Model: YOLO11m (medium)")
    print(f"   Dataset: {data_yaml}")
    print(f"   Epochs: {epochs}")
    print(f"   Image size: {imgsz}x{imgsz}")
    print(f"   Batch size: {batch}")
    print(f"   Device: {device}")
    
    # Train
    print("\n" + "="*70)
    print("🚀 Starting training...")
    print("="*70 + "\n")
    
    start_time = time.time()
    
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        patience=25,  # More patience for larger model
        save=True,
        project='runs/bee-detection',
        name='yolo11m-bee',
        exist_ok=True,
        
        # Optimization
        close_mosaic=10,
        amp=True,  # Automatic mixed precision
        
        # Learning rate schedule for YOLO11m
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        
        # Data augmentation optimized for bee detection
        hsv_h=0.015,      # Slight hue variation
        hsv_s=0.7,        # Saturation
        hsv_v=0.4,        # Value/brightness
        degrees=10.0,     # Slight rotation
        translate=0.1,    # Translation
        scale=0.5,        # Scale variation (important for bees at different distances)
        shear=0.0,        # No shear (bees have consistent shape)
        perspective=0.0,  # No perspective (top-down view)
        flipud=0.0,       # No vertical flip (bees are upright)
        fliplr=0.5,       # Horizontal flip OK
        mosaic=1.0,       # Mosaic augmentation
        mixup=0.0,        # No mixup for detection
        copy_paste=0.0,   # No copy-paste
        
        # Loss weights (default works well for YOLO11)
        box=7.5,
        cls=0.5,
        dfl=1.5,
    )
    
    training_time = time.time() - start_time
    
    # Validate
    print("\n" + "="*70)
    print("📊 Validating model...")
    print("="*70 + "\n")
    
    metrics = model.val()
    
    # Results
    best_model_path = Path(results.save_dir) / 'weights' / 'best.pt'
    last_model_path = Path(results.save_dir) / 'weights' / 'last.pt'
    
    print("\n" + "="*70)
    print("✅ TRAINING COMPLETE!")
    print("="*70)
    print(f"\n📊 Performance Metrics:")
    print(f"   mAP50: {metrics.box.map50:.3f}")
    print(f"   mAP50-95: {metrics.box.map:.3f}")
    print(f"   Precision: {metrics.box.mp:.3f}")
    print(f"   Recall: {metrics.box.mr:.3f}")
    
    print(f"\n⏱️  Training time: {training_time/60:.1f} minutes")
    print(f"\n💾 Models saved:")
    print(f"   Best: {best_model_path}")
    print(f"   Last: {last_model_path}")
    print(f"   Results: {results.save_dir}")
    
    # Export to ONNX for Hailo compilation
    print("\n" + "="*70)
    print("📦 Exporting to ONNX for Hailo...")
    print("="*70 + "\n")
    
    onnx_path = export_to_onnx(best_model_path, imgsz)
    
    # Summary
    print("\n" + "="*70)
    print("✅ ALL DONE!")
    print("="*70)
    print(f"\n📁 Output files:")
    print(f"   PyTorch: {best_model_path}")
    print(f"   ONNX: {onnx_path}")
    
    print(f"\n🚀 Next steps:")
    print(f"   1. Test model:")
    print(f"      yolo predict model={best_model_path} source=test_image.jpg")
    print(f"")
    print(f"   2. Compile for Hailo (on WSL):")
    print(f"      Transfer ONNX: scp {onnx_path} user@wsl-host:/path/")
    print(f"      Run: ./compile_yolo11m_bee.sh")
    print(f"")
    print(f"   3. Deploy to Raspberry Pi:")
    print(f"      scp model.hef rpi:/opt/bee-monitoring/src/api/models/")
    
    return best_model_path, onnx_path, metrics

def export_to_onnx(model_path: str, imgsz: int = 640):
    """Export trained model to ONNX format for Hailo compilation"""
    print(f"📦 Loading model from: {model_path}")
    model = YOLO(model_path)
    
    onnx_filename = Path(model_path).stem + '.onnx'
    
    print(f"🔄 Exporting to ONNX...")
    print(f"   Format: ONNX")
    print(f"   Image size: {imgsz}")
    print(f"   Dynamic: False (required for Hailo)")
    print(f"   Opset: 11")
    
    onnx_path = model.export(
        format='onnx',
        imgsz=imgsz,
        simplify=True,
        dynamic=False,  # Static shape required for Hailo
        opset=11,       # Compatible with Hailo DFC
    )
    
    # Get file size
    file_size_mb = os.path.getsize(onnx_path) / (1024 * 1024)
    
    print(f"✅ ONNX exported successfully!")
    print(f"   Path: {onnx_path}")
    print(f"   Size: {file_size_mb:.1f} MB")
    
    return onnx_path

def main():
    parser = argparse.ArgumentParser(
        description='Train YOLO11m for bee detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download from Roboflow and train
  python train_yolo11m_bee.py --roboflow-key YOUR_KEY --workspace myworkspace --project bee-detection
  
  # Train from local dataset
  python train_yolo11m_bee.py --data datasets/bee-detection/data.yaml
  
  # Custom training parameters
  python train_yolo11m_bee.py --data data.yaml --epochs 150 --imgsz 800 --batch 8
        """
    )
    
    # Data source options
    parser.add_argument('--data', type=str, help='Path to data.yaml file')
    parser.add_argument('--roboflow-key', type=str, help='Roboflow API key')
    parser.add_argument('--workspace', type=str, help='Roboflow workspace name')
    parser.add_argument('--project', type=str, help='Roboflow project name')
    parser.add_argument('--version', type=int, default=1, help='Dataset version (default: 1)')
    
    # Training options
    parser.add_argument('--epochs', type=int, default=100, help='Training epochs (default: 100)')
    parser.add_argument('--imgsz', type=int, default=640, help='Image size (640 or 800, default: 640)')
    parser.add_argument('--batch', type=int, default=16, help='Batch size (default: 16, auto-adjusted for GPU)')
    parser.add_argument('--device', type=str, default='0', help='Device: 0 for GPU, mps for Apple Silicon, cpu for CPU')
    
    args = parser.parse_args()
    
    # Determine data source
    if args.data:
        data_yaml = args.data
        print(f"📂 Using local dataset: {data_yaml}")
    elif args.roboflow_key and args.workspace and args.project:
        data_location = download_roboflow_dataset(
            args.roboflow_key,
            args.workspace,
            args.project,
            args.version
        )
        data_yaml = os.path.join(data_location, 'data.yaml')
    else:
        print("❌ Error: Either --data or Roboflow credentials required")
        print("\nExamples:")
        print("  python train_yolo11m_bee.py --data datasets/bee-detection/data.yaml")
        print("  python train_yolo11m_bee.py --roboflow-key KEY --workspace ws --project bee-detection")
        parser.print_help()
        return
    
    # Verify data.yaml exists
    if not os.path.exists(data_yaml):
        print(f"❌ Error: data.yaml not found: {data_yaml}")
        return
    
    print(f"✅ Dataset configuration: {data_yaml}")
    
    # Train
    try:
        train_yolo11m_bee(
            data_yaml=data_yaml,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Training failed: {e}")
        raise

if __name__ == '__main__':
    main()
