#!/usr/bin/env python3
"""Test Hailo inference with pure GStreamer (no hailo-apps framework)."""
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import cv2
import numpy as np
import time

def main():
    print("="*70)
    print("🎯 TESTING HAILO WITH PURE GSTREAMER")
    print("="*70)
    
    # Initialize GStreamer
    Gst.init(None)
    
    # Load test frame
    cap = cv2.VideoCapture("/tmp/your_bee_movie_120fps.mov")
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Failed to read frame")
        return 1
    
    print(f"✅ Loaded frame: {frame.shape}")
    
    # Resize to 640x640 and convert to RGB
    frame_resized = cv2.resize(frame, (640, 640))
    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    
    # Test with official model
    hef_path = "/usr/local/hailo/resources/models/hailo8l/yolov6n.hef"
    print(f"📦 Using HEF: {hef_path}")
    
    # Create pipeline: appsrc -> hailonet -> appsink
    pipeline_str = (
        f"appsrc name=source format=time is-live=true ! "
        f"video/x-raw,format=RGB,width=640,height=640,framerate=1/1 ! "
        f"hailonet hef-path={hef_path} is-active=true ! "
        f"appsink name=sink emit-signals=true sync=false max-buffers=1 drop=false"
    )
    
    print(f"\n🔧 Pipeline: {pipeline_str}\n")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        appsrc = pipeline.get_by_name('source')
        appsink = pipeline.get_by_name('sink')
        
        # No callback - we'll pull synchronously after EOS
        
        # Create main loop
        loop = GLib.MainLoop()
        
        # Handle bus messages
        def on_message(bus, message):
            t = message.type
            if t == Gst.MessageType.EOS:
                print("📬 Got EOS")
                loop.quit()
            elif t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print(f"❌ Error: {err}")
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
        
        print(f"📤 Pushing frame ({len(data)} bytes)...")
        start = time.time()
        appsrc.emit('push-buffer', buf)
        appsrc.emit('end-of-stream')
        
        # Run main loop with timeout
        GLib.timeout_add_seconds(5, lambda: loop.quit())
        loop.run()
        
        # Try to pull sample from appsink
        got_sample = False
        print("🔍 Pulling sample from appsink...")
        sample = appsink.emit('pull-sample')
        
        if sample:
            buffer = sample.get_buffer()
            print(f"✅ Got output buffer: {buffer.get_size()} bytes")
            print(f"⏱️  Inference time: {(time.time() - start)*1000:.1f}ms")
            print("\n🎉 SUCCESS! Hailo inference working with pure GStreamer!")
            got_sample = True
        else:
            print("⏱️  No sample available from appsink")
        
        # Cleanup
        pipeline.set_state(Gst.State.NULL)
        return 0 if got_sample else 1
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
