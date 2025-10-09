#!/usr/bin/env python3
"""
COMPLETE Hailo Inference - Tensor Extraction + YOLO Post-Processing.

Must run in hailo-rpi5-examples venv to access hailo module.
"""
import sys
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import cv2
import numpy as np
import time
import logging

# Import hailo module (from hailo-rpi5-examples venv)
try:
    import hailo
    HAILO_AVAILABLE = True
except ImportError:
    print("⚠️  hailo module not available - must run in hailo-rpi5-examples venv")
    HAILO_AVAILABLE = False

# Add project to path
sys.path.insert(0, "/opt/bee-monitoring/src")
from ai.hailo_yolo_postprocess import BeeYOLOPostProcessor

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def extract_raw_tensor_from_buffer(buffer):
    """
    Extract raw tensor data directly from buffer memory.
    
    When using hailonet without hailofilter, the output is raw tensor data
    in the buffer, not ROI metadata.
    """
    try:
        # Get buffer size
        size = buffer.get_size()
        
        # Map buffer to access memory
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            logger.error("Failed to map buffer")
            return None
        
        try:
            # Extract raw data as numpy array
            data = np.frombuffer(map_info.data, dtype=np.uint8)
            logger.debug(f"Extracted raw buffer: size={size}, data_shape={data.shape}")
            
            # For YOLO models, the output is typically a single tensor
            # We'll need to reshape based on model output shape
            # For now, return as-is and we'll reshape in post-processing
            return {'output': data}
            
        finally:
            buffer.unmap(map_info)
        
    except Exception as e:
        logger.error(f"Failed to extract raw tensor: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_tensors_from_buffer(buffer):
    """
    Extract tensors from GStreamer buffer.
    
    Tries ROI metadata first (if hailofilter was used),
    falls back to raw buffer extraction.
    """
    if not HAILO_AVAILABLE:
        return extract_raw_tensor_from_buffer(buffer)
    
    try:
        # Try to get ROI metadata (requires hailofilter)
        roi = hailo.get_roi_from_buffer(buffer)
        
        if roi is None:
            logger.debug("No ROI metadata, extracting raw buffer")
            return extract_raw_tensor_from_buffer(buffer)
        
        # Get all tensors from ROI
        raw_tensors = roi.get_tensors()
        
        if len(raw_tensors) == 0:
            logger.debug("No tensors in ROI, extracting raw buffer")
            return extract_raw_tensor_from_buffer(buffer)
        
        # Convert to dictionary
        tensors = {}
        for t in raw_tensors:
            layer_name = t.name()
            tensor = roi.get_tensor(layer_name)
            tensor_np = np.array(tensor, copy=False)  # Use original memory
            tensors[layer_name] = tensor_np
            logger.debug(f"Extracted tensor '{layer_name}': shape={tensor_np.shape}, dtype={tensor_np.dtype}")
        
        return tensors
        
    except Exception as e:
        logger.debug(f"ROI extraction failed, trying raw buffer: {e}")
        return extract_raw_tensor_from_buffer(buffer)


def main():
    if not HAILO_AVAILABLE:
        print("="*70)
        print("❌ ERROR: hailo module not available")
        print("="*70)
        print("This script must run in hailo-rpi5-examples venv:")
        print("  cd /tmp/hailo-rpi5-examples")
        print("  source setup_env.sh")
        print("  python3 /tmp/hailo_inference_complete.py")
        return 1
    
    print("="*70)
    print("🎯 COMPLETE HAILO INFERENCE TEST")
    print("="*70)
    print("✅ hailo module available")
    print("✅ Tensor extraction ready")
    print("✅ YOLO post-processing ready")
    print("="*70 + "\n")
    
    # Initialize GStreamer
    Gst.init(None)
    
    # Load test frame
    video_path = "/tmp/your_bee_movie_120fps.mov"
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return 1
    
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Failed to read frame")
        return 1
    
    h_orig, w_orig = frame.shape[:2]
    print(f"✅ Loaded frame: {frame.shape}")
    
    # Resize to 640x640 and convert to RGB
    frame_resized = cv2.resize(frame, (640, 640))
    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    
    # Test with official YOLOv6n model first
    hef_path = "/usr/local/hailo/resources/models/hailo8l/yolov6n.hef"
    print(f"📦 Using HEF: {hef_path}")
    
    # Initialize YOLO post-processor
    yolo_processor = BeeYOLOPostProcessor(
        img_dims=(640, 640),
        nms_iou_thresh=0.45,
        score_threshold=0.25,
        num_classes=80,  # COCO has 80 classes
        meta_arch="yolo_v5"  # YOLOv6 similar to v5
    )
    print("✅ YOLO post-processor initialized\n")
    
    # Create GStreamer pipeline
    # hailonet outputs raw tensors in the buffer
    pipeline_str = (
        f"appsrc name=source format=time is-live=true ! "
        f"video/x-raw,format=RGB,width=640,height=640,framerate=1/1 ! "
        f"hailonet hef-path={hef_path} is-active=true ! "
        f"identity name=probe ! "
        f"queue ! "
        f"appsink name=sink emit-signals=true sync=false max-buffers=2"
    )
    
    print(f"🔧 Pipeline: {pipeline_str}\n")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        appsrc = pipeline.get_by_name('source')
        appsink = pipeline.get_by_name('sink')
        
        detections = []
        inference_start = None
        
        def pad_probe_callback(pad, info):
            """Pad probe callback - triggered when data flows through."""
            nonlocal detections, inference_start
            
            try:
                buffer = info.get_buffer()
                if not buffer:
                    return Gst.PadProbeReturn.OK
                
                print(f"✅ Got buffer via pad probe: {buffer.get_size()} bytes")
                
                # STEP 1: Extract tensors using hailo module
                print("🔍 Extracting tensors...")
                tensors = extract_tensors_from_buffer(buffer)
                
                if tensors is None or len(tensors) == 0:
                    print("❌ No tensors extracted")
                    return Gst.PadProbeReturn.OK
                
                print(f"✅ Extracted {len(tensors)} tensors:")
                for name, tensor in tensors.items():
                    print(f"   - {name}: shape={tensor.shape}, dtype={tensor.dtype}")
                
                # STEP 2: Post-process with YOLO
                print("🔧 Applying YOLO post-processing...")
                dets = yolo_processor.process_tensors(tensors, w_orig, h_orig)
                
                if inference_start:
                    inference_time = (time.time() - inference_start) * 1000
                    print(f"⏱️  Total inference time: {inference_time:.1f}ms")
                
                print(f"✅ Got {len(dets)} detections after post-processing")
                
                if len(dets) > 0:
                    print("\n📋 Detections:")
                    for i, det in enumerate(dets[:10]):  # Show first 10
                        bbox = det['bbox']
                        conf = det['confidence']
                        cls_name = det['class_name']
                        print(f"   {i+1}. {cls_name}: conf={conf:.3f}, bbox={bbox}")
                
                detections.extend(dets)
                
            except Exception as e:
                print(f"❌ Error in pad probe: {e}")
                import traceback
                traceback.print_exc()
            
            return Gst.PadProbeReturn.OK
        
        # Add pad probe to identity element (after hailonet)
        identity = pipeline.get_by_name('probe')
        identity_src_pad = identity.get_static_pad('src')
        identity_src_pad.add_probe(Gst.PadProbeType.BUFFER, pad_probe_callback)
        
        print("✅ Pad probe added to identity element (after hailonet)")
        
        #  Also add to appsink for debugging
        sink_pad = appsink.get_static_pad('sink')
        def sink_probe(pad, info):
            print("🔍 Data reached appsink!")
            return Gst.PadProbeReturn.OK
        sink_pad.add_probe(Gst.PadProbeType.BUFFER, sink_probe)
        
        # Create main loop
        loop = GLib.MainLoop()
        
        def on_message(bus, message):
            t = message.type
            if t == Gst.MessageType.EOS:
                print("\n📬 Got EOS")
                loop.quit()
            elif t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print(f"❌ Pipeline error: {err}")
                print(f"   Debug: {debug}")
                loop.quit()
            return True
        
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', on_message)
        
        # Start pipeline
        pipeline.set_state(Gst.State.PLAYING)
        print("▶️  Pipeline started")
        
        # Push frame
        data = frame_rgb.tobytes()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        buf.pts = 0
        buf.duration = Gst.SECOND
        
        print(f"📤 Pushing frame ({len(data)} bytes)...\n")
        inference_start = time.time()
        appsrc.emit('push-buffer', buf)
        appsrc.emit('end-of-stream')
        
        # Run main loop with timeout
        GLib.timeout_add_seconds(10, lambda: loop.quit())
        loop.run()
        
        # Cleanup
        pipeline.set_state(Gst.State.NULL)
        
        print(f"\n{'='*70}")
        if len(detections) > 0:
            print(f"🎉 SUCCESS! Complete Hailo inference pipeline working!")
            print(f"📊 Total detections: {len(detections)}")
            print(f"✅ Tensor extraction: WORKING")
            print(f"✅ YOLO post-processing: WORKING")
            print(f"✅ End-to-end pipeline: WORKING")
            print(f"{'='*70}")
            return 0
        else:
            print(f"⚠️  Pipeline ran but no detections found")
            print(f"   (May need to adjust confidence threshold or check model)")
            print(f"{'='*70}")
            return 1
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
