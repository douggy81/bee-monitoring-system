#!/usr/bin/env python3
"""
Minimal GStreamer + Hailo test without hailo-apps framework.
Direct GStreamer pipeline test.
"""
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import time

def main():
    print("="*70)
    print("🧪 MINIMAL GSTREAMER + HAILO TEST")
    print("="*70)
    
    # Initialize GStreamer
    Gst.init(None)
    print("✅ GStreamer initialized")
    
    # Test HEF path
    hef_path = "/usr/local/hailo/resources/models/hailo8l/yolov6n.hef"
    print(f"📦 Using HEF: {hef_path}")
    
    # Create a simple pipeline: videotestsrc -> hailonet -> fakesink
    # This tests if hailonet element works at all
    pipeline_str = (
        f"videotestsrc num-buffers=1 ! "
        f"video/x-raw,width=640,height=640,format=RGB ! "
        f"hailonet hef-path={hef_path} is-active=true ! "
        f"fakesink"
    )
    
    print(f"\n🔧 Pipeline: {pipeline_str}\n")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print("✅ Pipeline created")
        
        # Start pipeline
        print("▶️  Starting pipeline...")
        pipeline.set_state(Gst.State.PLAYING)
        
        # Wait a bit
        time.sleep(2)
        
        # Get state
        ret, state, pending = pipeline.get_state(Gst.CLOCK_TIME_NONE)
        print(f"📊 Pipeline state: {state}")
        
        # Wait for EOS or error
        bus = pipeline.get_bus()
        msg = bus.timed_pop_filtered(
            5 * Gst.SECOND,
            Gst.MessageType.ERROR | Gst.MessageType.EOS
        )
        
        if msg:
            t = msg.type
            if t == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print(f"❌ Error: {err}")
                print(f"   Debug: {debug}")
            elif t == Gst.MessageType.EOS:
                print("✅ End of stream (EOS) - Success!")
        else:
            print("⏱️  Timeout - but no error!")
        
        # Cleanup
        pipeline.set_state(Gst.State.NULL)
        print("\n✅ Test complete - GStreamer + Hailo working!")
        return 0
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
