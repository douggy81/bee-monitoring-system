#!/usr/bin/env python3
"""
Test Hailo inference using hailopython element.

This uses hailopython which calls our Python module with processed results.
"""
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import cv2

def main():
    print("="*70)
    print("🎯 TESTING HAILOPYTHON APPROACH")
    print("="*70)
    
    # Initialize GStreamer
    Gst.init(None)
    print("✅ GStreamer initialized")
    
    # Load test frame
    cap = cv2.VideoCapture("/tmp/your_bee_movie_120fps.mov")
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Failed to read frame")
        return 1
    
    h_orig, w_orig = frame.shape[:2]
    print(f"✅ Loaded frame: {frame.shape}")
    
    # Test with COCO model first to verify pipeline works
    # If COCO detects things, then bee models have compilation issues
    import sys
    model_choice = sys.argv[1] if len(sys.argv) > 1 else "coco"
    
    if model_choice == "official":
        hef_path = "/usr/local/hailo/resources/models/hailo8l/yolov6n.hef"
        input_size = 640
        print("🏢 Testing with OFFICIAL Hailo YOLOv6n model")
    elif model_choice == "coco":
        hef_path = "/opt/bee-monitoring/src/api/models/yolo11n_coco--640x640_quant_hailort_multidevice_1.hef"
        input_size = 640
        print("🧪 Testing with COCO model (80 classes)")
    elif model_choice == "bee_best":
        hef_path = "/opt/bee-monitoring/src/api/models/yolo11n_bee_best--640x640_quant_hailort_multidevice_1.hef"
        input_size = 640
        print("🐝 Testing with bee_best model (3 classes)")
    else:
        hef_path = "/tmp/bee_model/yolo11n_bee_v2--800x800_quant_hailort_multidevice_2.hef"
        input_size = 800
        print("🐝 Testing with bee_v2 model (3 classes)")
    
    # Python module path
    python_module = "/tmp/hailo_python_module.py"
    
    print(f"📦 HEF: {hef_path}")
    print(f"🐍 Python module: {python_module}")
    
    # Test with image or video
    test_input = sys.argv[2] if len(sys.argv) > 2 else "image"
    
    if test_input == "image":
        source = "filesrc location=/tmp/test_street.jpg ! jpegdec ! "
        print("🖼️  Testing with street image (has people, cars, etc.)")
    else:
        source = "filesrc location=/tmp/your_bee_movie_120fps.mov ! decodebin ! "
        print("🎬 Testing with bee video")
    
    # Create pipeline with hailopython
    pipeline_str = (
        f"{source}"
        f"videoconvert ! videoscale ! "
        f"video/x-raw,format=RGB,width={input_size},height={input_size} ! "
        f"hailonet hef-path={hef_path} is-active=true ! "
        f"hailopython module={python_module} ! "
        f"queue ! fakesink"
    )
    
    print(f"\n🔧 Pipeline:\n{pipeline_str}\n")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print("✅ Pipeline created")
        
        # Create main loop
        loop = GLib.MainLoop()
        
        def on_message(bus, message):
            t = message.type
            if t == Gst.MessageType.EOS:
                print("\n📬 End of stream")
                loop.quit()
            elif t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print(f"\n❌ Pipeline error: {err}")
                print(f"   Debug: {debug}")
                loop.quit()
            return True
        
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', on_message)
        
        # Start pipeline
        print("▶️  Starting pipeline...")
        pipeline.set_state(Gst.State.PLAYING)
        
        # Run for 5 seconds for image, 30 for video
        timeout = 5 if test_input == "image" else 30
        GLib.timeout_add_seconds(timeout, lambda: loop.quit())
        
        print("🔄 Processing frames...\n")
        loop.run()
        
        # Cleanup
        pipeline.set_state(Gst.State.NULL)
        
        print("\n" + "="*70)
        print("✅ Test complete")
        print("="*70)
        return 0
        
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
