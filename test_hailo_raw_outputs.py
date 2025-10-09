#!/usr/bin/env python3
"""
Test Hailo with RAW network outputs (pre-NMS).

The issue is that all HEF models have NMS built-in that filters everything.
We need to access the raw YOLO output layers before NMS.
"""
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import sys

def main():
    print("="*70)
    print("🔬 TESTING RAW HAILO OUTPUTS (PRE-NMS)")
    print("="*70)
    
    Gst.init(None)
    
    # Use official model
    hef_path = "/usr/local/hailo/resources/models/hailo8l/yolov6n.hef"
    print(f"📦 Model: {hef_path}")
    print(f"🖼️  Input: /tmp/test_street.jpg")
    
    # Try to get RAW outputs by NOT using hailofilter
    # Just use hailonet directly and probe the output
    pipeline_str = (
        f"filesrc location=/tmp/test_street.jpg ! "
        f"jpegdec ! videoconvert ! videoscale ! "
        f"video/x-raw,format=RGB,width=640,height=640 ! "
        f"hailonet hef-path={hef_path} ! "
        f"identity name=probe ! "
        f"fakesink"
    )
    
    print(f"\n🔧 Pipeline:\n{pipeline_str}\n")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        
        # Add probe to see what hailonet outputs
        identity = pipeline.get_by_name('probe')
        
        def probe_callback(pad, info):
            buffer = info.get_buffer()
            print(f"\n📊 Buffer info:")
            print(f"   Size: {buffer.get_size()} bytes")
            print(f"   PTS: {buffer.pts}")
            
            # Try to get buffer content
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if success:
                import numpy as np
                data = np.frombuffer(map_info.data, dtype=np.uint8)
                print(f"   Data shape: {data.shape}")
                print(f"   Data type: {data.dtype}")
                print(f"   Value range: [{data.min()}, {data.max()}]")
                print(f"   Non-zero: {np.count_nonzero(data)}/{data.size}")
                
                # Check if this looks like detection output
                if data.size > 1000:  # YOLO outputs are large
                    print(f"   🎯 This looks like raw YOLO output!")
                    print(f"   Mean: {data.mean():.2f}, Std: {data.std():.2f}")
                
                buffer.unmap(map_info)
            
            return Gst.PadProbeReturn.OK
        
        pad = identity.get_static_pad('src')
        pad.add_probe(Gst.PadProbeType.BUFFER, probe_callback)
        
        # Create main loop
        loop = GLib.MainLoop()
        
        def on_message(bus, message):
            t = message.type
            if t == Gst.MessageType.EOS:
                print("\n📬 EOS")
                loop.quit()
            elif t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print(f"\n❌ Error: {err}")
                print(f"   Debug: {debug}")
                loop.quit()
            return True
        
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', on_message)
        
        print("▶️  Starting pipeline...")
        pipeline.set_state(Gst.State.PLAYING)
        
        GLib.timeout_add_seconds(5, lambda: loop.quit())
        
        loop.run()
        
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
