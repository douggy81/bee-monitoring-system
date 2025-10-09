"""
Hailo backend using official picamera2 Hailo wrapper (HIGH-LEVEL API).

This is the CORRECT way to use Hailo on Raspberry Pi 5 with AI Kit.
Much simpler than the low-level hailo_platform API.
"""
import os
import logging
import json
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Try to import picamera2 Hailo wrapper
try:
    from picamera2.devices import Hailo as HailoDevice
    _HAILO_AVAILABLE = True
except ImportError:
    _HAILO_AVAILABLE = False
    logger.warning("picamera2 Hailo wrapper not available")


class HailoBackend:
    """Simplified Hailo backend using picamera2 high-level API."""
    
    def __init__(self, hef_path: Optional[str] = None) -> None:
        self.hef_path = hef_path or self._resolve_default_hef_path()
        self.initialized = False
        self.hailo = None
        
        # Align interface with CpuBackend
        self.conf: float = 0.25
        self.iou: float = 0.45
        self.imgsz: int = 640
        self.runtime = "hailo"
        
        # Class names
        self.names: Dict[int, str] = {}
    
    def _resolve_default_hef_path(self) -> Optional[str]:
        """Find default HEF file."""
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.abspath(os.path.join(here, os.pardir))
        models_dir = os.path.join(root, "api", "models")
        
        # Look for YOLO11n HEF first - prioritize custom bee model v2
        hef_candidates = [
            os.path.join(models_dir, "yolo11n_bee_v2--800x800_quant_hailort_multidevice_2.hef"),
            os.path.join(models_dir, "yolo11n_bee_best--640x640_quant_hailort_multidevice_1.hef"),
            os.path.join(models_dir, "yolo11n_coco--640x640_quant_hailort_multidevice_1.hef"),
        ]
        
        for hef in hef_candidates:
            if os.path.isfile(hef):
                return hef
        return None
    
    def initialize(self) -> bool:
        """Initialize Hailo device using picamera2 wrapper."""
        if not _HAILO_AVAILABLE:
            logger.warning("picamera2 Hailo wrapper not available")
            return False
        
        if not self.hef_path or not os.path.isfile(self.hef_path):
            logger.warning(f"HEF file not found: {self.hef_path}")
            return False
        
        try:
            logger.info(f"Loading HEF with picamera2 wrapper: {self.hef_path}")
            
            # Initialize Hailo device with HEF
            self.hailo = HailoDevice(self.hef_path)
            
            # Get model input shape
            model_h, model_w, model_c = self.hailo.get_input_shape()
            self.imgsz = model_h  # Assume square
            
            logger.info(f"✓ Hailo initialized successfully")
            logger.info(f"  HEF: {os.path.basename(self.hef_path)}")
            logger.info(f"  Input shape: {model_h}x{model_w}x{model_c}")
            
            # Extract input dimensions from HEF metadata
            hef_filename = os.path.basename(self.hef_path)
            if '800x800' in hef_filename:
                self.imgsz = 800
            elif '640x640' in hef_filename:
                self.imgsz = 640
            
            logger.info(f"  Model input size: {self.imgsz}×{self.imgsz}")
            
            # Load class names
            self._load_class_names()
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Hailo backend: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_class_names(self):
        """Load class names from labels JSON."""
        if not self.hef_path:
            return
        
        hef_dir = os.path.dirname(self.hef_path)
        labels_candidates = [
            os.path.join(hef_dir, "labels_yolo11n_bee_v2.json"),
            os.path.join(hef_dir, "labels_bee_v2.json"),
            os.path.join(hef_dir, "labels_bee.json"),
            os.path.join(hef_dir, "labels_yolo11n_coco.json"),
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
            self.names = {i: f"class_{i}" for i in range(80)}
    
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
        Run inference using picamera2 Hailo wrapper.
        
        Returns:
            List of detection dicts: [{bbox, confidence, class_id, class_name}]
        """
        if not self.initialized or self.hailo is None:
            return []
        
        try:
            h_orig, w_orig = frame.shape[:2]
            
            # Preprocess frame to model input size
            # The wrapper expects frame already resized to model input dimensions
            import cv2
            frame_resized = cv2.resize(frame, (self.imgsz, self.imgsz))
            
            # Run inference with Hailo wrapper
            results = self.hailo.run(frame_resized)
            
            # Extract detections from Hailo NMS output
            # Format: list where each element is detections for a class
            # Each detection: [y_min, x_min, y_max, x_max, confidence]
            detections = []
            
            for class_id, class_detections in enumerate(results):
                if not isinstance(class_detections, np.ndarray) or class_detections.size == 0:
                    continue
                
                for detection in class_detections:
                    if len(detection) < 5:
                        continue
                    
                    y_min, x_min, y_max, x_max, conf = detection[:5]
                    
                    # Filter by confidence
                    if conf < self.conf:
                        continue
                    
                    # Coordinates are normalized [0-1], scale to original frame
                    x1 = float(x_min * w_orig)
                    y1 = float(y_min * h_orig)
                    x2 = float(x_max * w_orig)
                    y2 = float(y_max * h_orig)
                    
                    # Clip to frame bounds
                    x1 = max(0, min(w_orig - 1, x1))
                    y1 = max(0, min(h_orig - 1, y1))
                    x2 = max(0, min(w_orig - 1, x2))
                    y2 = max(0, min(h_orig - 1, y2))
                    
                    # Convert to xywh format
                    x = int(x1)
                    y = int(y1)
                    w = int(x2 - x1)
                    h = int(y2 - y1)
                    
                    class_name = self.names.get(class_id, f"class_{class_id}")
                    
                    detections.append({
                        'bbox': [x, y, w, h],
                        'confidence': float(conf),
                        'class_id': int(class_id),
                        'class_name': class_name
                    })
            
            return detections
            
        except Exception as e:
            logger.error(f"Hailo inference failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def close(self) -> None:
        """Clean up resources."""
        if self.hailo is not None:
            try:
                self.hailo.close()
            except:
                pass
        self.initialized = False
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get version information."""
        return {
            "hef_path": self.hef_path,
            "ready": bool(self.initialized),
            "api": "picamera2.devices.Hailo (high-level)"
        }
