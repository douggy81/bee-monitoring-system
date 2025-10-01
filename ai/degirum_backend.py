"""
Degirum backend for YOLO inference using Hailo AI HAT+ via Degirum PySDK.

This backend uses Degirum's cloud-optimized models and SDK which:
- Simplifies Hailo inference (no raw HailoRT needed)
- Handles preprocessing/postprocessing automatically
- Supports multiple hardware targets (Hailo, CPU, GPU)
- Easy model updates and deployment
"""
import os
import logging
import threading
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import Degirum
try:
    import degirum as dg
    _DEGIRUM_AVAILABLE = True
except ImportError:
    _DEGIRUM_AVAILABLE = False
    logger.warning("degirum not available; install with: pip install degirum-tools")


class DegirumBackend:
    """YOLO inference backend using Degirum PySDK."""
    
    def __init__(
        self,
        model_name: str = "yolo11n_bee_monitoring",
        device: str = "AUTO",  # AUTO, HAILO, CPU
        token: Optional[str] = None
    ):
        """
        Initialize Degirum backend.
        
        Args:
            model_name: Name of model in Degirum zoo or cloud
            device: Target device (AUTO=try Hailo first, CPU fallback)
            token: Degirum API token (from env DEGIRUM_TOKEN if not provided)
        """
        self.model_name = model_name
        self.device_preference = device.upper()
        self.token = token or os.getenv("DEGIRUM_TOKEN")
        self.initialized = False
        self.runtime = None
        
        # Model and inference state
        self.model = None
        self.zoo = None
        
        # Align interface with CpuBackend
        self.conf: float = 0.25
        self.iou: float = 0.45
        self.imgsz: int = 640
        self.names: Dict[int, str] = {}  # Will be populated from model
        
        # Thread safety
        self._infer_lock = threading.Lock()
    
    def initialize(self) -> bool:
        """Initialize Degirum model zoo and load model."""
        if not _DEGIRUM_AVAILABLE:
            logger.error("Degirum SDK not available")
            return False
        
        if not self.token:
            logger.warning("DEGIRUM_TOKEN not set; cannot connect to Degirum cloud")
            return False
        
        # Set HOME to writable location to avoid DeGirum creating dirs in read-only /opt
        os.environ['HOME'] = '/tmp/degirum_home'
        os.makedirs('/tmp/degirum_home', exist_ok=True)
        
        try:
            # Try to connect to local Hailo device first
            if self.device_preference in ("AUTO", "HAILO"):
                try:
                    logger.info("Attempting to connect to local Hailo device...")
                    self.zoo = dg.connect(dg.LOCAL, device="hailo")
                    self.runtime = "hailo"
                    logger.info("✓ Connected to local Hailo device")
                except Exception as e:
                    logger.warning(f"Local Hailo connection failed: {e}")
                    if self.device_preference == "HAILO":
                        return False
                    # Fall through to cloud
            
            # If Hailo failed or preference is cloud/cpu, use cloud connection
            if self.zoo is None:
                logger.info("Connecting to Degirum Cloud...")
                self.zoo = dg.connect(dg.CLOUD, token=self.token)
                self.runtime = "cloud"
                logger.info("✓ Connected to Degirum Cloud")
            
            # Load model
            logger.info(f"Loading model: {self.model_name}")
            
            # Degirum API for loading models
            # May need to specify additional parameters based on their API
            self.model = self.zoo.load_model(
                model_name=self.model_name,
                # Optional parameters:
                # inference_host_address="@local" for local inference
                # overlay_alpha=0 to disable drawing (we do it ourselves)
            )
            
            # Extract class names if available
            if hasattr(self.model, 'model_info') and 'labels' in self.model.model_info:
                labels = self.model.model_info['labels']
                if isinstance(labels, list):
                    self.names = {i: name for i, name in enumerate(labels)}
                elif isinstance(labels, dict):
                    self.names = labels
            
            # Set confidence threshold
            if hasattr(self.model, 'confidence_threshold'):
                self.model.confidence_threshold = self.conf
            
            # Set NMS threshold
            if hasattr(self.model, 'nms_threshold'):
                self.model.nms_threshold = self.iou
            
            self.initialized = True
            logger.info(f"Degirum backend initialized (runtime: {self.runtime})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Degirum backend: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def infer_full(self, frame) -> List[Dict[str, Any]]:
        """
        Run inference on frame and return detections.
        
        Args:
            frame: numpy array (H, W, 3) BGR format
            
        Returns:
            List of detection dicts: [{bbox, confidence, class_id, class_name}]
        """
        if not self.initialized or self.model is None:
            return []
        
        with self._infer_lock:
            try:
                # Degirum handles preprocessing automatically
                # Just pass the frame (may need BGR->RGB conversion depending on model)
                result = self.model(frame)
                
                # Parse Degirum results
                # Result format may vary - common formats:
                # - result.results: list of detections
                # - result.inference_results: dict with 'boxes', 'scores', 'labels'
                
                detections = []
                
                # Try different result formats
                if hasattr(result, 'results') and result.results:
                    # Format 1: result.results is list of detection objects
                    for det in result.results:
                        if hasattr(det, 'bbox') and hasattr(det, 'score') and hasattr(det, 'label'):
                            # bbox format: [x, y, w, h] or [x1, y1, x2, y2]
                            bbox = det.bbox
                            if len(bbox) == 4:
                                # Check if it's xyxy or xywh
                                if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                                    # Assume xyxy format
                                    x1, y1, x2, y2 = bbox
                                    x, y, w, h = x1, y1, x2 - x1, y2 - y1
                                else:
                                    # Assume xywh format
                                    x, y, w, h = bbox
                                
                                class_id = det.label if isinstance(det.label, int) else 0
                                class_name = self.names.get(class_id, det.label if isinstance(det.label, str) else f"class_{class_id}")
                                
                                detections.append({
                                    'bbox': [float(x), float(y), float(w), float(h)],
                                    'confidence': float(det.score),
                                    'class_id': int(class_id),
                                    'class_name': class_name
                                })
                
                elif hasattr(result, 'inference_results'):
                    # Format 2: result.inference_results dict
                    inf_results = result.inference_results
                    boxes = inf_results.get('boxes', [])
                    scores = inf_results.get('scores', [])
                    labels = inf_results.get('labels', [])
                    
                    for i, (box, score, label) in enumerate(zip(boxes, scores, labels)):
                        if len(box) == 4:
                            x1, y1, x2, y2 = box
                            x, y, w, h = x1, y1, x2 - x1, y2 - y1
                            
                            class_id = label if isinstance(label, int) else i
                            class_name = self.names.get(class_id, f"class_{class_id}")
                            
                            detections.append({
                                'bbox': [float(x), float(y), float(w), float(h)],
                                'confidence': float(score),
                                'class_id': int(class_id),
                                'class_name': class_name
                            })
                
                return detections
                
            except Exception as e:
                logger.warning(f"Degirum inference failed: {e}")
                return []
    
    def close(self) -> None:
        """Clean up resources."""
        self.initialized = False
        self.model = None
        self.zoo = None
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get backend version and status information."""
        info = {
            "degirum_available": _DEGIRUM_AVAILABLE,
            "degirum_version": None,
            "model_name": self.model_name,
            "device": self.device_preference,
            "runtime": self.runtime,
            "ready": self.initialized
        }
        
        if _DEGIRUM_AVAILABLE:
            try:
                import degirum as dg
                info["degirum_version"] = dg.__version__
            except Exception:
                pass
        
        return info
