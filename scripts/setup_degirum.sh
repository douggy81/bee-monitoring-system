#!/bin/bash
# Setup Degirum backend on Raspberry Pi

TOKEN="$1"

if [ -z "$TOKEN" ]; then
    echo "Usage: $0 <degirum_token>"
    echo "Example: $0 dg_xxxxx..."
    exit 1
fi

echo "Setting up Degirum backend on Raspberry Pi..."
echo ""

# Create systemd override directory
ssh digital4ai@192.168.68.66 "sudo mkdir -p /etc/systemd/system/bee-api.service.d/"

# Create override file with Degirum environment variables
ssh digital4ai@192.168.68.66 "sudo tee /etc/systemd/system/bee-api.service.d/degirum.conf > /dev/null << EOF
[Service]
# Degirum PySDK Configuration
Environment=\"DEGIRUM_TOKEN=$TOKEN\"
Environment=\"DEGIRUM_MODEL=yolo11n_bee_monitoring\"
Environment=\"DEGIRUM_DEVICE=AUTO\"
EOF
"

echo "✓ Systemd override created"
echo ""

# Reload systemd
ssh digital4ai@192.168.68.66 "sudo systemctl daemon-reload"
echo "✓ Systemd reloaded"
echo ""

# Restart service
ssh digital4ai@192.168.68.66 "sudo systemctl restart bee-api"
echo "✓ Service restarted"
echo ""

# Wait for service to start
sleep 3

# Check status
echo "Checking AI backend status..."
ssh digital4ai@192.168.68.66 "curl -sS http://localhost/api/bee/ai/status | jq '{ready, runtime, degirum: .degirum}'"

echo ""
echo "Setup complete!"
echo "Test with: curl 'http://192.168.68.66/api/bee/ai/detect?ai_backend=degirum&annotate=1'"
