"""
Hailo GStreamer Backend - The CORRECT approach for Raspberry Pi + Hailo-8L.

Based on official hailo-rpi5-examples using GStreamer integration.
This avoids manual buffer allocation and uses the platform-optimized approach.
"""
import os
import json
import logging
import threading
import time
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# Import GStreamer
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
    import hailo
    _GSTREAMER_AVAILABLE = True
except ImportError as e:
    _GSTREAMER_AVAILABLE = False
    logger.warning(f"GStreamer or Hailo not available: {e}")


class HailoGStreamerBackend:
    """
    Hailo backend using GStreamer integration (RPi + Hailo-8L optimized).
    
    This is the CORRECT approach for Raspberry Pi 5 + Hailo-8L.
    """
    
    def __init__(self, hef_path: Optional[str] = None) -> None:
        self.hef_path = hef_path or self._resolve_default_hef_path()
        self.initialized = False
        
        # GStreamer objects
        self.pipeline = None
        self.loop = None
        self.appsink = None
        
        # Detection results
        self.latest_detections = []
        self.detection_lock = threading.Lock()
        
        # Align interface with CpuBackend
        self.conf: float = 0.25
        self.iou: float = 0.45
        self.imgsz: int = 640
        self.runtime = "hailo-gstreamer"
        
        # Class names
        self.names: Dict[int, str] = {}
        
        # Processing thread
        self.processing_thread = None
        self.stop_flag = threading.Event()
    
    def _resolve_default_hef_path(self) -> Optional[str]:
        """Find default HEF file."""
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.abspath(os.path.join(here, os.pardir))
        models_dir = os.path.join(root, "api", "models")
        
        # Prioritize newest freshly compiled model
        hef_candidates = [
            os.path.join(models_dir, "bee_test2--640x640_quant_hailort_multidevice_1/bee_test2--640x640_quant_hailort_multidevice_1.hef"),
            os.path.join(models_dir, "yolo11n_bee_v2--800x800_quant_hailort_multidevice_2.hef"),
            os.path.join(models_dir, "yolo11n_bee_best--640x640_quant_hailort_multidevice_1.hef"),
        ]
        
        for hef in hef_candidates:
            if os.path.isfile(hef):
                return hef
        return None
    
    def initialize(self) -> bool:
        """Initialize GStreamer and Hailo pipeline."""
        if not _GSTREAMER_AVAILABLE:
            logger.warning("GStreamer or Hailo not available")
            return False
        
        if not self.hef_path or not os.path.isfile(self.hef_path):
            logger.warning(f"HEF file not found: {self.hef_path}")
            return False
        
        try:
            logger.info(f"Initializing GStreamer Hailo backend")
            logger.info(f"  HEF: {self.hef_path}")
            
            # Initialize GStreamer
            Gst.init(None)
            
            # Extract input size from HEF filename
            hef_filename = os.path.basename(self.hef_path)
            if '800x800' in hef_filename:
                self.imgsz = 800
            elif '640x640' in hef_filename:
                self.imgsz = 640
            
            logger.info(f"  Model input size: {self.imgsz}×{self.imgsz}")
            
            # Load class names
            self._load_class_names()
            
            self.initialized = True
            logger.info("✓ GStreamer Hailo backend initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize GStreamer Hailo backend: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_class_names(self):
        """Load class names from labels JSON."""
        if not self.hef_path:
            return
        
        hef_dir = os.path.dirname(self.hef_path)
        labels_candidates = [
            os.path.join(hef_dir, "labels_bee_test2.json"),
            os.path.join(hef_dir, "labels_yolo11n_bee_v2.json"),
            os.path.join(hef_dir, "labels_bee_v2.json"),
            os.path.join(hef_dir, "labels_bee.json"),
        ]
        
        for labels_path in labels_candidates:
            if os.path.isfile(labels_path):
                try:
                    with open(labels_path, 'r') as f:
                        labels_dict = json.load(f)
                        self.names = {int(k): v for k, v in labels_dict.items()}
                        logger.info(f"✓ Loaded {len(self.names)} class names from {os.path.basename(labels_path)}")
                        return
                except Exception as e:
                    logger.warning(f"Failed to load labels from {labels_path}: {e}")
        
        # Fallback
        if not self.names:
            logger.warning("No labels file found, using default class names")
            self.names = {0: "background", 1: "bee", 2: "pollen"}
    
    def _create_pipeline_for_frame(self, frame: np.ndarray) -> str:
        """
        Create GStreamer pipeline for processing a single frame.
        
        Uses appsrc to feed frame data into Hailo pipeline.
        Simplified version without hailofilter - using raw output.
        """
        h, w = frame.shape[:2]
        
        # Simplified pipeline - HailoNet with built-in NMS
        pipeline_str = (
            f"appsrc name=source emit-signals=true is-live=true format=time "
            f"caps=video/x-raw,format=RGB,width={w},height={h},framerate=1/1 ! "
            f"queue ! "
            f"videoscale ! video/x-raw,width={self.imgsz},height={self.imgsz} ! "
            f"queue ! "
            f"hailonet hef-path={self.hef_path} is-active=true ! "
            f"queue ! "
            f"appsink name=sink emit-signals=true sync=false"
        )
        
        return pipeline_str
    
    def infer(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Run inference and return (boxes_xywh, confidences)."""
        detections = self.infer_full(frame)
        
        boxes: List[Tuple[int, int, int, int]] = []
        scores: List[float] = []
        
        for det in detections:
            bbox = det['bbox']  # [x, y, w, h]
            boxes.append((int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])))
            scores.append(float(det['confidence']))
        
        return boxes, scores
    
    def infer_full(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run inference using GStreamer Hailo pipeline.
        
        Returns:
            List of detection dicts: [{bbox, confidence, class_id, class_name}]
        """
        if not self.initialized:
            return []
        
        try:
            h_orig, w_orig = frame.shape[:2]
            
            # Convert BGR to RGB for GStreamer
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create pipeline
            pipeline_str = self._create_pipeline_for_frame(frame_rgb)
            logger.debug(f"Pipeline: {pipeline_str}")
            
            pipeline = Gst.parse_launch(pipeline_str)
            
            # Get appsrc and appsink
            appsrc = pipeline.get_by_name('source')
            appsink = pipeline.get_by_name('sink')
            
            # Container for results
            detections = []
            done_event = threading.Event()
            
            def on_new_sample(sink):
                """Callback when detection results are available."""
                sample = sink.emit('pull-sample')
                if sample:
                    buffer = sample.get_buffer()
                    
                    # Get detections from buffer using Hailo API
                    roi = hailo.get_roi_from_buffer(buffer)
                    hailo_detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
                    
                    for detection in hailo_detections:
                        label = detection.get_label()
                        confidence = detection.get_confidence()
                        bbox = detection.get_bbox()
                        
                        if confidence < self.conf:
                            continue
                        
                        # Scale bounding box to original frame size
                        x_min = bbox.xmin() * w_orig
                        y_min = bbox.ymin() * h_orig
                        x_max = bbox.xmax() * w_orig
                        y_max = bbox.ymax() * h_orig
                        
                        # Convert to xywh
                        x = int(x_min)
                        y = int(y_min)
                        w = int(x_max - x_min)
                        h = int(y_max - y_min)
                        
                        # Get class ID from label
                        class_id = next((k for k, v in self.names.items() if v == label), 1)
                        
                        detections.append({
                            'bbox': [x, y, w, h],
                            'confidence': float(confidence),
                            'class_id': int(class_id),
                            'class_name': label
                        })
                
                done_event.set()
                return Gst.FlowReturn.OK
            
            # Connect callback
            appsink.connect('new-sample', on_new_sample)
            
            # Start pipeline
            pipeline.set_state(Gst.State.PLAYING)
            
            # Push frame data
            data = frame_rgb.tobytes()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            buf.pts = 0
            buf.duration = Gst.SECOND
            
            appsrc.emit('push-buffer', buf)
            appsrc.emit('end-of-stream')
            
            # Wait for results (with timeout)
            if not done_event.wait(timeout=5.0):
                logger.warning("Hailo inference timed out")
            
            # Cleanup
            pipeline.set_state(Gst.State.NULL)
            
            logger.debug(f"Got {len(detections)} detections from Hailo GStreamer")
            return detections
            
        except Exception as e:
            logger.error(f"Hailo GStreamer inference failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def close(self) -> None:
        """Clean up resources."""
        self.stop_flag.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
        
        self.initialized = False
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get version information."""
        return {
            "hef_path": self.hef_path,
            "ready": bool(self.initialized),
            "api": "GStreamer + Hailo (RPi optimized)"
        }
