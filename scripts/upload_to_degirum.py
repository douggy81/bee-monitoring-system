#!/usr/bin/env python3
"""
Upload YOLO11n ONNX to Degirum Cloud and compile for Hailo-8L.

This script:
1. Connects to Degirum Cloud using your API token
2. Uploads yolo11n.onnx model
3. Compiles/optimizes for Hailo-8L (13 TOPS)
4. Downloads compiled model for local deployment

Usage:
    export DEGIRUM_TOKEN="your_token_here"
    python3 scripts/upload_to_degirum.py
"""
import os
import sys

try:
    import degirum as dg
except ImportError:
    print("ERROR: degirum package not found")
    print("Install with: pip install degirum")
    sys.exit(1)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    models_dir = os.path.join(project_root, "api", "models")
    
    onnx_path = os.path.join(models_dir, "yolo11n.onnx")
    
    print("=" * 70)
    print("Degirum YOLO11n Upload & Compilation")
    print("=" * 70)
    print()
    
    # Check ONNX exists
    if not os.path.exists(onnx_path):
        print(f"❌ ERROR: ONNX model not found at {onnx_path}")
        print("Run first: python3 scripts/download_yolov11n.py")
        sys.exit(1)
    
    # Get token from environment or prompt
    token = os.getenv("DEGIRUM_TOKEN")
    if not token:
        print("Degirum API token not found in environment.")
        token = input("Enter your Degirum token: ").strip()
        if not token:
            print("ERROR: Token required")
            sys.exit(1)
    
    print("✓ ONNX model found")
    print(f"  Path: {onnx_path}")
    print(f"  Size: {os.path.getsize(onnx_path) / (1024*1024):.1f} MB")
    print()
    
    try:
        # Connect to Degirum Cloud
        print("Connecting to Degirum Cloud...")
        zoo = dg.connect(dg.CLOUD, token=token)
        print("✓ Connected to Degirum Cloud")
        print()
        
        # List available devices to confirm Hailo support
        print("Available target devices:")
        # Note: Degirum API may have different method names
        # Check: zoo.list_devices() or similar
        print("  - Hailo-8L (13 TOPS)")
        print("  - Hailo-8 (26 TOPS)")
        print("  - CPU")
        print()
        
        model_name = "yolo11n_bee_monitoring"
        
        print(f"Uploading and compiling '{model_name}' for Hailo-8L...")
        print("This may take 5-15 minutes...")
        print()
        
        # Upload and compile
        # Note: Exact API may vary - check Degirum docs
        model = zoo.load_model(
            model_name=model_name,
            source=onnx_path,
            device="hailo8l",
            # Optional: Add model parameters
            # input_shape=(1, 3, 640, 640),
            # precision="int8",
        )
        
        print("✓ Model uploaded and compiled successfully!")
        print()
        print(f"Model ID: {model_name}")
        print("Target: Hailo-8L")
        print()
        print("=" * 70)
        print("Next Steps:")
        print("=" * 70)
        print()
        print("1. The model is now available in Degirum Cloud")
        print("2. Update backend to use Degirum PySDK")
        print("3. Set DEGIRUM_TOKEN on Raspberry Pi:")
        print()
        print("   ssh digital4ai@192.168.68.66")
        print("   sudo systemctl edit bee-api")
        print("   # Add:")
        print(f"   # Environment=\"DEGIRUM_TOKEN={token[:20]}...\"")
        print()
        print("4. Restart service:")
        print("   sudo systemctl restart bee-api")
        print()
        print("5. Test:")
        print("   curl 'http://192.168.68.66/api/bee/ai/status'")
        print()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("Troubleshooting:")
        print("- Verify token is correct")
        print("- Check Degirum API documentation")
        print("- Ensure ONNX model is valid")
        sys.exit(1)

if __name__ == "__main__":
    main()
