"""
Hailo backend with FIXED buffer allocation (v3).

Based on community forum solution:
https://community.hailo.ai/t/hailort-error-check-failed-input-buffer-size-0-is-different-than-expected-602112-for-input-yolov8m-input-layer1/3645

The key fix: Allocate BOTH input and output buffers in create_bindings()
"""
import os
import logging
import json
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# Try to import Hailo platform
try:
    from hailo_platform import HEF, VDevice, FormatType, HailoSchedulingAlgorithm
    _HAILO_AVAILABLE = True
except ImportError:
    _HAILO_AVAILABLE = False
    logger.warning("hailo_platform not available")


class HailoBackend:
    """Hailo backend with CORRECT buffer allocation."""
    
    def __init__(self, hef_path: Optional[str] = None) -> None:
        self.hef_path = hef_path or self._resolve_default_hef_path()
        self.initialized = False
        
        # Hailo objects
        self.hef = None
        self.target = None
        self.infer_model = None
        self.configured_infer_model = None
        
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
        """Initialize Hailo device with CORRECT buffer allocation."""
        if not _HAILO_AVAILABLE:
            logger.warning("hailo_platform not available")
            return False
        
        if not self.hef_path or not os.path.isfile(self.hef_path):
            logger.warning(f"HEF file not found: {self.hef_path}")
            return False
        
        try:
            logger.info(f"Loading HEF: {self.hef_path}")
            
            # Load HEF
            self.hef = HEF(self.hef_path)
            
            # Create VDevice
            params = VDevice.create_params()
            params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN
            self.target = VDevice(params)
            
            # Create infer model
            self.infer_model = self.target.create_infer_model(self.hef_path)
            self.infer_model.set_batch_size(1)
            
            # Set input format
            input_format_type = self.hef.get_input_vstream_infos()[0].format.type
            self.infer_model.input().set_format_type(input_format_type)
            
            # Set output format to FLOAT32
            for output in self.infer_model.outputs:
                output.set_format_type(FormatType.FLOAT32)
            
            # Get input shape
            input_vstream_info = self.hef.get_input_vstream_infos()[0]
            self.input_shape = input_vstream_info.shape
            self.imgsz = self.input_shape[0]  # Assume square
            
            logger.info(f"✓ HEF loaded successfully")
            logger.info(f"  Network: {self.hef.get_network_group_names()[0]}")
            logger.info(f"  Input shape: {self.input_shape}")
            logger.info(f"  Model input size: {self.imgsz}×{self.imgsz}")
            
            # Configure the model
            self.configured_infer_model = self.infer_model.configure()
            
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
            self.names = {i: f"class_{i}" for i in range(80)}
    
    def _create_bindings_with_input_buffers(self):
        """
        Create bindings with BOTH input and output buffers allocated.
        
        This is the FIX for the "buffer size 0" error!
        """
        # Create OUTPUT buffers
        output_buffers = {}
        for name in self.infer_model.output_names:
            output_shape = self.infer_model.output(name).shape
            output_buffers[name] = np.empty(output_shape, dtype=np.float32)
        
        # CREATE INPUT BUFFERS (this was missing!)
        input_buffers = {}
        for name in self.infer_model.input_names:
            input_shape = self.infer_model.input(name).shape
            input_buffers[name] = np.empty(input_shape, dtype=np.uint8)
        
        # Create bindings with BOTH input and output buffers
        return self.configured_infer_model.create_bindings(
            input_buffers=input_buffers,
            output_buffers=output_buffers
        )
    
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
        Run inference with CORRECT buffer allocation.
        
        Returns:
            List of detection dicts: [{bbox, confidence, class_id, class_name}]
        """
        if not self.initialized or self.configured_infer_model is None:
            return []
        
        try:
            h_orig, w_orig = frame.shape[:2]
            
            # Preprocess frame
            frame_resized = cv2.resize(frame, (self.imgsz, self.imgsz))
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            frame_rgb = np.ascontiguousarray(frame_rgb, dtype=np.uint8)
            
            logger.debug(f"Preprocessed: shape={frame_rgb.shape}, dtype={frame_rgb.dtype}, size={frame_rgb.nbytes}")
            
            # Create bindings with BOTH input and output buffers allocated
            bindings = self._create_bindings_with_input_buffers()
            
            # Copy frame data into the pre-allocated input buffer
            input_buffer = bindings.input().get_buffer()
            np.copyto(input_buffer, frame_rgb)
            
            logger.debug(f"Input buffer filled: shape={input_buffer.shape}, size={input_buffer.nbytes}")
            
            # Create a completion event
            import threading
            completion_event = threading.Event()
            completion_result = {}
            
            def callback(completion_info, bindings_arg):
                """Callback when inference completes."""
                if completion_info.exception:
                    logger.error(f"Inference callback exception: {completion_info.exception}")
                else:
                    # Get results from output buffers
                    for name in self.infer_model.output_names:
                        completion_result[name] = bindings_arg.output(name).get_buffer().copy()
                completion_event.set()
            
            # Wait for device ready
            self.configured_infer_model.wait_for_async_ready(timeout_ms=10000)
            
            # Run async inference with callback
            self.configured_infer_model.run_async([bindings], lambda ci: callback(ci, bindings))
            
            # Wait for completion
            if not completion_event.wait(timeout=10.0):
                raise TimeoutError("Hailo inference timed out")
            
            # Get results
            results = completion_result
            
            logger.debug(f"Got {len(results)} output tensors")
            
            # Parse detections (assuming NMS post-processing in HEF)
            detections = self._parse_nms_output(results, h_orig, w_orig)
            
            return detections
            
        except Exception as e:
            logger.error(f"Hailo inference failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_nms_output(self, output_data: Dict[str, np.ndarray], h_orig: int, w_orig: int) -> List[Dict[str, Any]]:
        """Parse NMS output from Hailo."""
        detections = []
        
        # Assuming single output with NMS results
        # Format may vary - check actual output structure
        if len(output_data) == 1:
            output = list(output_data.values())[0]
            
            # If output is list of arrays (per-class detections)
            if isinstance(output, list):
                for class_id, class_detections in enumerate(output):
                    if not isinstance(class_detections, np.ndarray) or class_detections.size == 0:
                        continue
                    
                    for detection in class_detections:
                        if len(detection) < 5:
                            continue
                        
                        y_min, x_min, y_max, x_max, conf = detection[:5]
                        
                        if conf < self.conf:
                            continue
                        
                        # Scale to original frame
                        x1 = float(x_min * w_orig)
                        y1 = float(y_min * h_orig)
                        x2 = float(x_max * w_orig)
                        y2 = float(y_max * h_orig)
                        
                        # Convert to xywh
                        x = int(max(0, x1))
                        y = int(max(0, y1))
                        w = int(min(w_orig - x, x2 - x1))
                        h = int(min(h_orig - y, y2 - y1))
                        
                        detections.append({
                            'bbox': [x, y, w, h],
                            'confidence': float(conf),
                            'class_id': int(class_id),
                            'class_name': self.names.get(class_id, f"class_{class_id}")
                        })
        
        return detections
    
    def close(self) -> None:
        """Clean up resources."""
        if self.configured_infer_model is not None:
            del self.configured_infer_model
            self.configured_infer_model = None
        
        if self.target is not None:
            self.target.release()
            self.target = None
        
        self.initialized = False
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get version information."""
        return {
            "hef_path": self.hef_path,
            "ready": bool(self.initialized),
            "api": "hailo_platform with FIXED buffer allocation"
        }
