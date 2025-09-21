# Run the conversion
python convert_to_onnx.py
# Install Hailo Model Zoo (if not already installed)
git clone https://github.com/hailo-ai/hailo_model_zoo.git
cd hailo_model_zoo
pip install -e .

# Convert ONNX to HEF
hailomz compile yolov8n.onnx \
    --hw-arch hailo8l \
    --output-dir /opt/bee-monitoring/models/ \
    --name bee_detection_v1