"""
Hailo backend for YOLO inference using Hailo AI accelerator (AI HAT+, Hailo-8L).

Real implementation using HailoRT Python API for YOLO11n inference.
"""
import os
import subprocess
import logging
import threading
import json
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# Try to import Hailo Platform API
try:
    from hailo_platform import (
        HEF,
        Device,
        VDevice,
        HailoStreamInterface,
        InferVStreams,
        ConfigureParams,
        InputVStreamParams,
        OutputVStreamParams,
        FormatType
    )
    _HAILO_AVAILABLE = True
except ImportError:
    _HAILO_AVAILABLE = False
    logger.warning("hailo_platform not available; Hailo backend will not initialize")
class HailoBackend:
    def __init__(self, hef_path: Optional[str] = None) -> None:
        self.hef_path = hef_path or self._resolve_default_hef_path()
        self.initialized = False
        # Align interface with CpuBackend
        self.conf: float = 0.25
        self.iou: float = 0.45
        self.imgsz: int = 640
        self.runtime = "hailo"
        
        # Hailo inference objects
        self.hef = None
        self.network_group = None
        self.network_group_params = None
        self.input_vstreams_params = None
        self.output_vstreams_params = None
        self.vdevice = None
        
        # Class names (loaded from labels JSON)
        self.names: Dict[int, str] = {}
        
        # Thread safety
        self._infer_lock = threading.Lock()
    
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
            os.path.join(models_dir, "yolo11n.hef"),
            os.path.join(models_dir, "yolov8n.hef"),
        ]
        
        for hef in hef_candidates:
            if os.path.isfile(hef):
                return hef
        return None

    def _run_cli(self, args: List[str]) -> Tuple[int, str, str]:
        env = dict(os.environ)
        # Ensure logs go to writable directory to avoid warnings
        env.setdefault("HAILORT_LOG_DIR", "/tmp")
        # Ensure HOME points to a writable path so Hailo can create ~/.hailo
        # Use /tmp to avoid permissions issues with /opt/bee-monitoring
        env["HOME"] = os.getenv("HAILO_HOME", "/tmp/hailo_home")
        # Create the directory if it doesn't exist
        try:
            os.makedirs(env["HOME"], exist_ok=True)
        except Exception:
            pass
        # Ensure PATH contains system bins (hailortcli may invoke 'hostname')
        sys_path = "/usr/bin:/bin"
        env["PATH"] = f"{sys_path}:{env.get('PATH', '')}"
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
        out, err = proc.communicate(timeout=10)
        return proc.returncode, out, err

    def initialize(self) -> bool:
        """Initialize Hailo device and load HEF model."""
        if not _HAILO_AVAILABLE:
            logger.warning("Hailo Platform API not available")
            return False
        
        if not self.hef_path or not os.path.isfile(self.hef_path):
            logger.warning(f"HEF file not found: {self.hef_path}")
            return False
        
        # Set up environment for HailoRT
        os.environ.setdefault("HAILORT_LOG_DIR", "/tmp")
        home_dir = "/tmp/hailo_home"
        os.environ["HOME"] = home_dir
        os.makedirs(home_dir, exist_ok=True)
        # Ensure PATH has system bins for hostname etc
        os.environ["PATH"] = f"/usr/bin:/bin:{os.environ.get('PATH', '')}"
        
        try:
            logger.info(f"Loading HEF: {self.hef_path}")
            
            # Load HEF
            self.hef = HEF(self.hef_path)
            
            # Create VDevice
            self.vdevice = VDevice()
            
            # Configure network group
            network_groups = self.vdevice.configure(self.hef)
            if not network_groups:
                logger.error("No network groups found in HEF")
                return False
            
            self.network_group = network_groups[0]
            
            # Get input/output vstream params
            # API varies by HailoRT version - try different approaches
            try:
                # Method 1: via network_group_params
                self.network_group_params = self.network_group.create_params()
                self.input_vstreams_params = self.network_group_params.make_input_vstream_params()
                self.output_vstreams_params = self.network_group_params.make_output_vstream_params()
            except (AttributeError, TypeError):
                # Method 2: direct from network_group
                try:
                    self.input_vstreams_params = InputVStreamParams.make(self.network_group)
                    self.output_vstreams_params = OutputVStreamParams.make(self.network_group)
                except:
                    # Method 3: make_from_network_group
                    self.input_vstreams_params = InputVStreamParams.make_from_network_group(self.network_group)
                    self.output_vstreams_params = OutputVStreamParams.make_from_network_group(self.network_group)
            
            logger.info(f"✓ HEF loaded successfully")
            logger.info(f"  Network: {self.network_group.name}")
            logger.info(f"  Inputs: {len(self.input_vstreams_params)}")
            logger.info(f"  Outputs: {len(self.output_vstreams_params)}")
            
            # Extract input dimensions from HEF metadata
            # Parse from the filename or HEF metadata
            hef_filename = os.path.basename(self.hef_path)
            if '800x800' in hef_filename:
                self.imgsz = 800
                logger.info(f"  Input size detected from filename: {self.imgsz}×{self.imgsz}")
            elif '640x640' in hef_filename:
                self.imgsz = 640
                logger.info(f"  Input size detected from filename: {self.imgsz}×{self.imgsz}")
            else:
                # Try to get from buffer format
                try:
                    if self.input_vstreams_params:
                        if isinstance(self.input_vstreams_params, dict):
                            input_param = list(self.input_vstreams_params.values())[0]
                        else:
                            input_param = self.input_vstreams_params[0]
                        
                        if hasattr(input_param, 'user_buffer_format'):
                            buffer_format = input_param.user_buffer_format
                            if hasattr(buffer_format, 'height') and hasattr(buffer_format, 'width'):
                                self.imgsz = buffer_format.height
                                logger.info(f"  Input size detected from buffer: {self.imgsz}×{buffer_format.width}")
                except Exception as e:
                    logger.warning(f"  Could not detect input size: {e}. Using default 640")
            
            # Load class names from labels JSON
            self._load_class_names()
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Hailo backend: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_class_names(self):
        """Load COCO class names from labels JSON."""
        if not self.hef_path:
            return
        
        # Look for labels file alongside HEF
        hef_dir = os.path.dirname(self.hef_path)
        labels_candidates = [
            os.path.join(hef_dir, "labels_yolo11n_bee_v2.json"),
            os.path.join(hef_dir, "labels_yolo11n_bee_best.json"),
            os.path.join(hef_dir, "labels_bee.json"),
            os.path.join(hef_dir, "labels_yolo11n_coco.json"),
            os.path.join(hef_dir, "coco_labels.json"),
        ]
        
        for labels_path in labels_candidates:
            if os.path.isfile(labels_path):
                try:
                    with open(labels_path, 'r') as f:
                        labels_dict = json.load(f)
                        # Convert string keys to int
                        self.names = {int(k): v for k, v in labels_dict.items()}
                        logger.info(f"✓ Loaded {len(self.names)} class names from {os.path.basename(labels_path)}")
                        return
                except Exception as e:
                    logger.warning(f"Failed to load labels from {labels_path}: {e}")
        
        # Fallback to COCO defaults if no labels file
        if not self.names:
            logger.warning("No labels file found, using default COCO class names")
            self.names = {i: f"class_{i}" for i in range(80)}

    def infer(self, frame) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Run real Hailo inference and return (boxes_xywh, confidences)."""
        if not self.initialized:
            return [], []
        
        # Call infer_full and convert to simple format
        detections = self.infer_full(frame)
        
        boxes: List[Tuple[int, int, int, int]] = []
        scores: List[float] = []
        
        for det in detections:
            bbox = det['bbox']  # [x, y, w, h]
            boxes.append((int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])))
            scores.append(float(det['confidence']))
        
        return boxes, scores

    def close(self) -> None:
        self.initialized = False

    # -----------------------------
    # Status helpers
    # -----------------------------
    def get_version_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        try:
            # Use _run_cli to get version with proper env setup
            rc, out, err = self._run_cli(["/usr/bin/hailortcli", "--version"])
            if rc == 0:
                first = out.strip().splitlines()[0] if out else ""
                info["hailort_version"] = first
            else:
                # If failed, try to extract version from error (sometimes it's in stderr)
                combined = (out + err).strip()
                for line in combined.splitlines():
                    if "version" in line.lower() or "hailort" in line.lower():
                        info["hailort_version"] = line.strip()
                        break
        except Exception:
            pass
        info["hef_path"] = self.hef_path
        info["ready"] = bool(self.initialized)
        return info

    def infer_full(self, frame) -> List[Dict[str, Any]]:
        """
        Run inference on frame and return detections.
        
        Args:
            frame: numpy array (H, W, 3) BGR format
            
        Returns:
            List of detection dicts: [{bbox, confidence, class_id, class_name}]
        """
        if not self.initialized or self.network_group is None:
            return []
        
        with self._infer_lock:
            try:
                # Preprocess frame
                logger.info(f"Preprocessing frame: {frame.shape}")
                input_data = self._preprocess(frame)
                
                # Debug input data structure
                logger.info(f"Input data keys: {list(input_data.keys())}")
                for key, value in input_data.items():
                    logger.info(f"  '{key}': type={type(value)}, shape={value.shape if hasattr(value, 'shape') else 'N/A'}, dtype={value.dtype if hasattr(value, 'dtype') else 'N/A'}, nbytes={value.nbytes if hasattr(value, 'nbytes') else 'N/A'}, c_contiguous={value.flags.c_contiguous if hasattr(value, 'flags') else 'N/A'}")
                
                #  Debug vstream params
                logger.info(f"Input vstream params type: {type(self.input_vstreams_params)}")
                if isinstance(self.input_vstreams_params, dict):
                    logger.info(f"  Keys: {list(self.input_vstreams_params.keys())}")
                
                # Run inference with vstreams
                logger.info(f"Creating InferVStreams and activating network group...")
                # Activate network group before running inference
                with self.network_group.activate(self.network_group_params):
                    with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
                        logger.info(f"Running inference...")
                        # Run inference (blocking call)
                        output_data = infer_pipeline.infer(input_data)
                        logger.info(f"Inference complete! Output type: {type(output_data)}")
                
                # Postprocess output to get detections
                logger.debug(f"Postprocessing...")
                detections = self._postprocess(output_data, frame.shape)
                
                logger.debug(f"Inference complete: {len(detections)} detections")
                return detections
                
            except Exception as e:
                logger.error(f"Hailo inference failed: {e}")
                logger.error(f"Exception type: {type(e)}")
                import traceback
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                return []
    
    def _preprocess(self, frame) -> Dict[str, np.ndarray]:
        """
        Preprocess frame for Hailo inference.
        
        Returns dict with input name as key and preprocessed data as value.
        """
        # Resize to model input size (letterbox)
        target_size = (self.imgsz, self.imgsz)
        input_image, scale, pad = self._letterbox(frame, target_size)
        
        # Convert BGR to RGB
        input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
        
        # Hailo expects NHWC format with uint8, WITH batch dimension
        # Shape should be (1, H, W, C) = (1, 800, 800, 3)
        # The first dimension is the batch size (1 for single image)
        input_data = np.expand_dims(input_image, axis=0).astype(np.uint8)
        
        # Ensure C-contiguous memory layout (required by Hailo)
        if not input_data.flags.c_contiguous:
            input_data = np.ascontiguousarray(input_data)
        
        # Verify shape
        expected_size = self.imgsz * self.imgsz * 3
        actual_size = input_data.nbytes
        if actual_size != expected_size:
            logger.warning(f"Input size mismatch: expected {expected_size}, got {actual_size}")
        
        # Get input name from vstream params
        # Different HailoRT versions have different structures
        if isinstance(self.input_vstreams_params, dict):
            input_name = list(self.input_vstreams_params.keys())[0]
        elif isinstance(self.input_vstreams_params, list):
            input_name = self.input_vstreams_params[0].name
        else:
            # Fallback to common name
            input_name = "input_layer1"
        
        logger.debug(f"Preprocessed input '{input_name}': shape={input_data.shape}, dtype={input_data.dtype}, size={input_data.nbytes}")
        
        return {input_name: input_data}
    
    def _letterbox(self, image, new_shape=None):
        """
        Resize image with letterboxing (keep aspect ratio, add padding).
        
        Returns: resized_image, scale, (pad_w, pad_h)
        """
        if new_shape is None:
            new_shape = (self.imgsz, self.imgsz)
        
        shape = image.shape[:2]  # current shape [height, width]
        
        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        
        # Compute padding
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
        
        dw /= 2  # divide padding into 2 sides
        dh /= 2
        
        if shape[::-1] != new_unpad:  # resize
            image = cv2.resize(image, new_unpad, interpolation=cv2.INTER_LINEAR)
        
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        image = cv2.copyMakeBorder(image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        
        return image, r, (dw, dh)
    
    def _postprocess(self, output_data: Dict[str, np.ndarray], original_shape: Tuple[int, int, int]) -> List[Dict[str, Any]]:
        """
        Postprocess Hailo output to get detections.
        
        YOLO output format from Hailo: varies by post-processing
        - Some HEFs have built-in NMS (outputs boxes directly)
        - Others output raw [batch, 84, 8400] that needs NMS
        
        We'll try to handle both formats.
        """
        detections = []
        
        try:
            # Get output tensors (multiple outputs for YOLO)
            output_names = list(output_data.keys())
            
            # ALWAYS log output structure for debugging
            logger.info(f"=" * 70)
            logger.info(f"HAILO OUTPUT DEBUG")
            logger.info(f"=" * 70)
            logger.info(f"Number of output tensors: {len(output_names)}")
            logger.info(f"Output names: {output_names}")
            
            for name in output_names:
                output = output_data[name]
                logger.info(f"\nOutput '{name}':")
                logger.info(f"  Type: {type(output)}")
                if isinstance(output, np.ndarray):
                    logger.info(f"  Shape: {output.shape}")
                    logger.info(f"  Dtype: {output.dtype}")
                    logger.info(f"  Size: {output.size}")
                    logger.info(f"  Min/Max: {output.min():.4f} / {output.max():.4f}")
                elif isinstance(output, list):
                    logger.info(f"  List length: {len(output)}")
                    if len(output) > 0:
                        logger.info(f"  First element type: {type(output[0])}")
                        if isinstance(output[0], np.ndarray):
                            logger.info(f"  First element shape: {output[0].shape}")
                else:
                    logger.info(f"  Unexpected type: {type(output)}")
            logger.info(f"=" * 70)
            
            # Check if post-processed (has bboxes directly) or raw
            if len(output_names) == 1:
                # Likely post-processed output
                output = output_data[output_names[0]]
                logger.debug(f"Single output detected - checking format...")
                
                # Check if it's Hailo NMS format (list of arrays, one per class)
                if isinstance(output, list):
                    # Hailo sometimes wraps output in an extra list
                    if len(output) == 1 and isinstance(output[0], list):
                        logger.info(f"Detected Hailo NMS format (wrapped, {len(output[0])} classes)")
                        detections = self._parse_hailo_nms_output(output[0], original_shape)
                    else:
                        logger.info(f"Detected Hailo NMS format (list of {len(output)} classes)")
                        detections = self._parse_hailo_nms_output(output, original_shape)
                # Format: [num_detections, 6] where each row is [x1, y1, x2, y2, conf, class_id]
                elif output.ndim == 2 and output.shape[1] >= 6:
                    logger.info(f"Detected post-processed format: {output.shape}")
                    detections = self._parse_postprocessed_output(output, original_shape)
                else:
                    logger.warning(f"Unexpected single output shape: {output.shape}")
                    # Try to handle it anyway
                    if output.ndim == 2:
                        logger.info(f"Attempting to parse as detection output...")
                        detections = self._parse_postprocessed_output(output, original_shape)
            else:
                # Raw YOLO output - needs NMS
                logger.warning(f"Raw YOLO output detected ({len(output_names)} tensors)")
                logger.warning(f"Raw YOLO postprocessing not yet implemented")
                # TODO: Implement raw YOLO NMS
            
            logger.debug(f"Postprocess result: {len(detections)} detections")
            
        except Exception as e:
            logger.error(f"Postprocessing failed: {e}")
            import traceback
            traceback.print_exc()
        
        return detections
    
    def _parse_hailo_nms_output(self, output_list: list, original_shape: Tuple[int, int, int]) -> List[Dict[str, Any]]:
        """
        Parse Hailo NMS format output.
        
        Hailo NMS format is a list where each element corresponds to a class:
        - output_list[class_id] = numpy array of shape [num_detections, 5]
        - Each detection: [y_min, x_min, y_max, x_max, confidence]
        """
        detections = []
        h_orig, w_orig = original_shape[:2]
        
        # Scale factors (using model input size)
        scale_x = w_orig / float(self.imgsz)
        scale_y = h_orig / float(self.imgsz)
        
        for class_id, class_detections in enumerate(output_list):
            if not isinstance(class_detections, np.ndarray) or class_detections.size == 0:
                continue
            
            # Each detection: [y_min, x_min, y_max, x_max, confidence]
            for detection in class_detections:
                if len(detection) < 5:
                    continue
                
                y_min, x_min, y_max, x_max, conf = detection[:5]
                
                # Filter by confidence
                if conf < self.conf:
                    continue
                
                # Convert from normalized [0-1] to pixels
                # Hailo outputs are usually normalized
                x1 = float(x_min * self.imgsz * scale_x)
                y1 = float(y_min * self.imgsz * scale_y)
                x2 = float(x_max * self.imgsz * scale_x)
                y2 = float(y_max * self.imgsz * scale_y)
                
                # Convert to xywh format
                x = x1
                y = y1
                w = x2 - x1
                h = y2 - y1
                
                class_name = self.names.get(class_id, f"class_{class_id}")
                
                detections.append({
                    'bbox': [x, y, w, h],
                    'confidence': float(conf),
                    'class_id': int(class_id),
                    'class_name': class_name
                })
        
        return detections
    
    def _parse_postprocessed_output(self, output: np.ndarray, original_shape: Tuple[int, int, int]) -> List[Dict[str, Any]]:
        """Parse post-processed Hailo output (after built-in NMS)."""
        detections = []
        h_orig, w_orig = original_shape[:2]
        
        # Scale factors (using model input size)
        scale_x = w_orig / float(self.imgsz)
        scale_y = h_orig / float(self.imgsz)
        
        for detection in output:
            if len(detection) < 6:
                continue
            
            x1, y1, x2, y2, conf, class_id = detection[:6]
            
            # Filter by confidence
            if conf < self.conf:
                continue
            
            # Scale back to original size
            x1 = float(x1 * scale_x)
            y1 = float(y1 * scale_y)
            x2 = float(x2 * scale_x)
            y2 = float(y2 * scale_y)
            
            # Convert to xywh format
            x = x1
            y = y1
            w = x2 - x1
            h = y2 - y1
            
            class_id = int(class_id)
            class_name = self.names.get(class_id, f"class_{class_id}")
            
            detections.append({
                'bbox': [x, y, w, h],
                'confidence': float(conf),
                'class_id': class_id,
                'class_name': class_name
            })
        
        return detections
