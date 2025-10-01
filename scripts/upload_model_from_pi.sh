#!/bin/bash
# Upload YOLO11n from Mac to Pi, then upload to Degirum Cloud from Pi

set -e

TOKEN="$1"
if [ -z "$TOKEN" ]; then
    TOKEN="dg_FTiZyQ7AxrRLV1bceuGYCAvX76dq1g67sxa6H"
fi

echo "=============================================="
echo "Upload YOLO11n to Degirum Cloud"
echo "=============================================="
echo ""

# Step 1: Copy ONNX model to Pi
echo "[1/4] Copying YOLO11n ONNX to Raspberry Pi..."
scp api/models/yolo11n.onnx digital4ai@192.168.68.66:/home/digital4ai/
echo "✓ Model copied"
echo ""

# Step 2: Create upload script on Pi
echo "[2/4] Creating upload script on Pi..."
ssh digital4ai@192.168.68.66 "cat > /home/digital4ai/upload_to_degirum.py << 'SCRIPT_EOF'
#!/usr/bin/env python3
import os
import sys

try:
    import degirum as dg
    print(f'Degirum SDK version: {dg.__version__}')
except ImportError:
    print('ERROR: Degirum not installed')
    sys.exit(1)

token = '$TOKEN'
model_path = '/home/digital4ai/yolo11n.onnx'
model_name = 'yolo11n_bee_monitoring'

print('')
print('Connecting to Degirum Cloud...')
try:
    # Connect to cloud with proper zoo URL
    # Degirum cloud zoo URL
    zoo_url = 'https://cs.degirum.com'
    zoo = dg.connect(zoo_url, token=token)
    print('✓ Connected to Degirum Cloud')
    print('')
    
    # Check if model exists
    print(f'Uploading model: {model_name}')
    print('This may take 5-15 minutes...')
    print('')
    
    # Load/upload model for Hailo-8L
    # The exact API method depends on Degirum version
    # Try different approaches:
    
    try:
        # Method 1: Direct load with local file
        model = zoo.load_model(
            model_name=model_name,
            model_path=model_path,
            device='hailo8l',
        )
        print('✓ Model uploaded using load_model()')
    except Exception as e1:
        print(f'Method 1 failed: {e1}')
        try:
            # Method 2: Load from URL or zoo
            model = zoo.load_model(model_name)
            print('✓ Model already exists in zoo')
        except Exception as e2:
            print(f'Method 2 failed: {e2}')
            print('')
            print('Manual upload required:')
            print('1. Go to: https://degirum.ai/')
            print('2. Upload: /home/digital4ai/yolo11n.onnx')
            print('3. Name: yolo11n_bee_monitoring')
            print('4. Target: Hailo-8L')
            sys.exit(1)
    
    print('')
    print('=' * 50)
    print('✓ Success! Model ready')
    print('=' * 50)
    print('')
    print(f'Model name: {model_name}')
    print('Target: Hailo-8L')
    print('')
    print('Test on Pi:')
    print('  curl \"http://localhost/api/bee/ai/status\" | jq .degirum')
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
SCRIPT_EOF
"

echo "✓ Script created"
echo ""

# Step 3: Run upload script on Pi (use venv python)
echo "[3/4] Running upload script on Pi..."
echo ""
ssh digital4ai@192.168.68.66 "/opt/bee-monitoring/venv/bin/python3 /home/digital4ai/upload_to_degirum.py"

# Step 4: Restart service and test
echo ""
echo "[4/4] Restarting bee-api service..."
ssh digital4ai@192.168.68.66 "sudo systemctl restart bee-api && sleep 3"
echo "✓ Service restarted"
echo ""

echo "Testing Degirum backend..."
ssh digital4ai@192.168.68.66 "curl -sS http://localhost/api/bee/ai/status | jq '{ready, runtime, backends, degirum}'"

echo ""
echo "=============================================="
echo "✓ Upload Complete!"
echo "=============================================="
echo ""
echo "Test AI detection:"
echo "  curl 'http://192.168.68.66/api/bee/ai/detect?ai_backend=degirum&annotate=1' -o test.jpg"
echo ""
