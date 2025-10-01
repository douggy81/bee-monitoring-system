#!/usr/bin/env python3
"""
Convert YOLO11n ONNX to Hailo HEF format for Raspberry Pi AI HAT+ (Hailo-8L).

This script provides multiple methods for HEF conversion:
1. Docker-based compilation (recommended for Mac/Windows)
2. Native compilation (if Hailo DFC is installed)
3. Instructions for Hailo's online compilation service

Pipeline: YOLO11n.pt → YOLO11n.onnx → YOLO11n.hef
"""
import os
import sys
import subprocess
import platform

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    models_dir = os.path.join(project_root, "api", "models")
    
    onnx_path = os.path.join(models_dir, "yolo11n.onnx")
    hef_path = os.path.join(models_dir, "yolo11n.hef")
    
    print("=" * 70)
    print("YOLO11n ONNX → HEF Conversion for Hailo-8L")
    print("=" * 70)
    print()
    
    # Check if ONNX exists
    if not os.path.exists(onnx_path):
        print(f"❌ ERROR: ONNX model not found at {onnx_path}")
        print("Run first: python3 scripts/download_yolov11n.py")
        sys.exit(1)
    
    # Check if HEF already exists
    if os.path.exists(hef_path):
        print(f"✓ HEF file already exists: {hef_path}")
        size_mb = os.path.getsize(hef_path) / (1024 * 1024)
        print(f"  Size: {size_mb:.1f} MB")
        print()
        overwrite = input("Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Keeping existing HEF. Exiting.")
            sys.exit(0)
        os.remove(hef_path)
    
    print(f"Input:  {onnx_path}")
    print(f"Output: {hef_path}")
    print()
    
    # Determine compilation method
    print("Available HEF Compilation Methods:")
    print()
    print("1. Docker-based (Recommended)")
    print("   - Works on Mac, Windows, Linux")
    print("   - Uses official Hailo Docker image")
    print("   - Requires Docker Desktop")
    print()
    print("2. Hailo Developer Zone (Cloud)")
    print("   - Upload ONNX to https://hailo.ai/developer-zone/")
    print("   - Use online compilation service")
    print("   - No local setup required")
    print()
    print("3. Native Compilation")
    print("   - Requires Hailo Dataflow Compiler installed")
    print("   - x86 Linux only")
    print()
    
    choice = input("Select method (1/2/3) [1]: ").strip() or "1"
    print()
    
    if choice == "1":
        compile_with_docker(onnx_path, hef_path)
    elif choice == "2":
        provide_cloud_instructions(onnx_path)
    elif choice == "3":
        compile_native(onnx_path, hef_path)
    else:
        print("Invalid choice")
        sys.exit(1)

def compile_with_docker(onnx_path, hef_path):
    """Compile using Hailo Docker image."""
    print("=" * 70)
    print("Docker-based HEF Compilation")
    print("=" * 70)
    print()
    
    # Check if Docker is available
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, check=True)
        print(f"✓ Docker found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ERROR: Docker not found")
        print()
        print("Install Docker Desktop:")
        print("  - Mac: https://docs.docker.com/desktop/install/mac-install/")
        print("  - Windows: https://docs.docker.com/desktop/install/windows-install/")
        print("  - Linux: https://docs.docker.com/engine/install/")
        sys.exit(1)
    
    print()
    print("=" * 70)
    print("IMPORTANT: Hailo Docker Image Setup")
    print("=" * 70)
    print()
    print("The Hailo Dataflow Compiler Docker image is available to registered developers.")
    print()
    print("Steps to get access:")
    print("1. Register at: https://hailo.ai/developer-zone/")
    print("2. Request access to the Hailo Dataflow Compiler")
    print("3. Download the Docker image or use their instructions")
    print()
    print("Typical Docker command structure:")
    print()
    print("  docker run --rm -v $(pwd):/workspace \\")
    print("    hailo/dataflow-compiler:latest \\")
    print("    hailo parser onnx --input-model-path /workspace/yolo11n.onnx \\")
    print("    --output-model-script /workspace/yolo11n_model_script.py \\")
    print("    --net-name yolo11n")
    print()
    print("  docker run --rm -v $(pwd):/workspace \\")
    print("    hailo/dataflow-compiler:latest \\")
    print("    hailo compiler --model-script-path /workspace/yolo11n_model_script.py \\")
    print("    --hw-arch hailo8l --output-path /workspace/yolo11n.hef")
    print()
    
    proceed = input("Have you set up the Hailo Docker image? (y/N): ").strip().lower()
    if proceed != 'y':
        print()
        print("Please set up Hailo Docker access first, then re-run this script.")
        sys.exit(0)
    
    # If user confirms, attempt compilation
    try_docker_compilation(onnx_path, hef_path)

def try_docker_compilation(onnx_path, hef_path):
    """Attempt Docker-based compilation."""
    models_dir = os.path.dirname(onnx_path)
    model_script_path = os.path.join(models_dir, "yolo11n_model_script.py")
    
    print()
    print("Running Hailo parser...")
    
    # Parse ONNX
    parse_cmd = [
        "docker", "run", "--rm",
        "-v", f"{models_dir}:/workspace",
        "hailo/dataflow-compiler:latest",
        "hailo", "parser", "onnx",
        "--input-model-path", "/workspace/yolo11n.onnx",
        "--output-model-script", "/workspace/yolo11n_model_script.py",
        "--net-name", "yolo11n"
    ]
    
    try:
        subprocess.run(parse_cmd, check=True)
        print("✓ ONNX parsing complete")
    except subprocess.CalledProcessError as e:
        print(f"❌ Parser failed: {e}")
        print()
        print("If the image is not found, you may need to:")
        print("1. Pull it: docker pull hailo/dataflow-compiler:latest")
        print("2. Or use the correct image name from Hailo documentation")
        sys.exit(1)
    
    print()
    print("Running Hailo compiler...")
    
    # Compile to HEF
    compile_cmd = [
        "docker", "run", "--rm",
        "-v", f"{models_dir}:/workspace",
        "hailo/dataflow-compiler:latest",
        "hailo", "compiler",
        "--model-script-path", "/workspace/yolo11n_model_script.py",
        "--model-name", "yolo11n",
        "--hw-arch", "hailo8l",
        "--output-path", "/workspace/yolo11n.hef",
        "--batch-size", "1"
    ]
    
    try:
        subprocess.run(compile_cmd, check=True)
        print("✓ HEF compilation complete")
        print_success(hef_path)
    except subprocess.CalledProcessError as e:
        print(f"❌ Compiler failed: {e}")
        sys.exit(1)

def compile_native(onnx_path, hef_path):
    """Compile using native Hailo DFC installation."""
    print("=" * 70)
    print("Native HEF Compilation")
    print("=" * 70)
    print()
    
    # Check for hailo command
    try:
        result = subprocess.run(["hailo", "--version"], capture_output=True, text=True, check=True)
        print(f"✓ Hailo DFC found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ERROR: Hailo Dataflow Compiler not found")
        print()
        print("Install from: https://hailo.ai/developer-zone/")
        print("Requires x86 Linux")
        sys.exit(1)
    
    models_dir = os.path.dirname(onnx_path)
    model_script_path = os.path.join(models_dir, "yolo11n_model_script.py")
    
    print()
    print("Parsing ONNX model...")
    parse_cmd = [
        "hailo", "parser", "onnx",
        "--input-model-path", onnx_path,
        "--output-model-script", model_script_path,
        "--net-name", "yolo11n"
    ]
    
    subprocess.run(parse_cmd, check=True)
    print("✓ ONNX parsing complete")
    
    print()
    print("Compiling to HEF (this may take several minutes)...")
    compile_cmd = [
        "hailo", "compiler",
        "--model-script-path", model_script_path,
        "--model-name", "yolo11n",
        "--hw-arch", "hailo8l",
        "--output-path", hef_path,
        "--batch-size", "1"
    ]
    
    subprocess.run(compile_cmd, check=True)
    print("✓ HEF compilation complete")
    print_success(hef_path)

def provide_cloud_instructions(onnx_path):
    """Provide instructions for cloud-based compilation."""
    print("=" * 70)
    print("Hailo Developer Zone Cloud Compilation")
    print("=" * 70)
    print()
    print("Steps:")
    print()
    print("1. Go to: https://hailo.ai/developer-zone/")
    print()
    print("2. Sign in or create an account")
    print()
    print("3. Navigate to the Model Zoo or Compilation Service")
    print()
    print(f"4. Upload your ONNX model: {onnx_path}")
    print()
    print("5. Select target: Hailo-8L (13 TOPS)")
    print()
    print("6. Configure:")
    print("   - Input size: 640x640")
    print("   - Batch size: 1")
    print("   - Optimization: Standard")
    print()
    print("7. Download the compiled yolo11n.hef file")
    print()
    print("8. Place it in: api/models/yolo11n.hef")
    print()
    print("=" * 70)

def print_success(hef_path):
    """Print success message and deployment instructions."""
    if os.path.exists(hef_path):
        size_mb = os.path.getsize(hef_path) / (1024 * 1024)
        print()
        print("=" * 70)
        print("✓ HEF Compilation Successful!")
        print("=" * 70)
        print(f"\nOutput: {hef_path}")
        print(f"Size: {size_mb:.1f} MB")
        print()
        print("Deploy to Raspberry Pi:")
        print(f"  scp {hef_path} digital4ai@192.168.68.66:/home/digital4ai/")
        print("  ssh digital4ai@192.168.68.66")
        print("  sudo install -o bee-monitor -g bee-monitor -m 0644 ~/yolo11n.hef /opt/bee-monitoring/src/api/models/")
        print("  sudo systemctl restart bee-api")
        print()
        print("The system will automatically use Hailo backend when HEF is available.")
        print()

if __name__ == "__main__":
    main()
