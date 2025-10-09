"""
Hailo YOLO Post-Processing - Adapted from official Hailo Model Zoo.

Source: https://github.com/hailo-ai/hailo_model_zoo/blob/master/hailo_model_zoo/core/postprocessing/detection/yolo.py

Simplified for bee detection with OpenCV NMS (no TensorFlow dependency).
"""
import numpy as np
import cv2
from typing import List, Dict, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


def sigmoid(x):
    """Sigmoid activation function."""
    return 1.0 / (1.0 + np.exp(-x))


class BeeYOLOPostProcessor:
    """
    YOLO post-processing for Hailo bee detection model.
    
    Adapted from official Hailo Model Zoo implementation.
    """
    
    def __init__(self,
                 img_dims=(640, 640),
                 nms_iou_thresh=0.45,
                 score_threshold=0.25,
                 num_classes=3,
                 meta_arch="yolo_v5"):
        """
        Initialize YOLO post-processor.
        
        Args:
            img_dims: Model input dimensions (height, width)
            nms_iou_thresh: NMS IoU threshold
            score_threshold: Confidence threshold for detections
            num_classes: Number of classes (3 for bee model: background, bee, pollen)
            meta_arch: YOLO architecture variant ("yolo_v5" for YOLO11/v8/v5)
        """
        self.img_dims = img_dims
        self.nms_iou_thresh = nms_iou_thresh
        self.score_threshold = score_threshold
        self.num_classes = num_classes
        self.meta_arch = meta_arch
        
        logger.info(f"Initialized BeeYOLOPostProcessor:")
        logger.info(f"  Image dims: {img_dims}")
        logger.info(f"  NMS threshold: {nms_iou_thresh}")
        logger.info(f"  Score threshold: {score_threshold}")
        logger.info(f"  Num classes: {num_classes}")
        logger.info(f"  Architecture: {meta_arch}")
    
    def convert_tensor_format(self, tensor: np.ndarray) -> np.ndarray:
        """
        Convert Hailo tensor from uint8 (0-255) to float32 format.
        
        Based on Hailo community finding that hailonet outputs uint8
        but post-processing expects float32.
        """
        if tensor.dtype == np.uint8:
            logger.debug(f"Converting uint8 tensor {tensor.shape} to float32")
            # Convert to float and normalize to 0-1 range
            tensor = tensor.astype(np.float32) / 255.0
        return tensor
    
    def _yolo5_decode(self, 
                      predictions: np.ndarray,
                      img_width: int,
                      img_height: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Decode YOLOv5/v8/v11 predictions.
        
        Args:
            predictions: Raw model output [batch, num_predictions, 5+num_classes]
                        Format: [x, y, w, h, confidence, class_scores...]
            img_width: Original image width
            img_height: Original image height
        
        Returns:
            boxes: Array of [N, 4] in format [x1, y1, x2, y2]
            scores: Array of [N] confidence scores
            classes: Array of [N] class IDs
        """
        # YOLOv5/v8/v11 output format: [x_center, y_center, width, height, confidence, class_probs...]
        # Already in normalized coordinates (0-1)
        
        boxes_list = []
        scores_list = []
        classes_list = []
        
        for pred in predictions:
            # pred shape: [num_predictions, 5+num_classes]
            for detection in pred:
                if len(detection) < 5 + self.num_classes:
                    continue
                
                x_center, y_center, width, height, obj_conf = detection[:5]
                class_probs = detection[5:5+self.num_classes]
                
                # Get best class
                class_id = np.argmax(class_probs)
                class_conf = class_probs[class_id]
                
                # Combined confidence
                confidence = obj_conf * class_conf
                
                if confidence < self.score_threshold:
                    continue
                
                # Convert from center format to corner format
                # Scale to image dimensions
                x1 = (x_center - width / 2) * img_width
                y1 = (y_center - height / 2) * img_height
                x2 = (x_center + width / 2) * img_width
                y2 = (y_center + height / 2) * img_height
                
                boxes_list.append([x1, y1, x2, y2])
                scores_list.append(confidence)
                classes_list.append(class_id)
        
        if not boxes_list:
            return np.array([]), np.array([]), np.array([])
        
        return np.array(boxes_list), np.array(scores_list), np.array(classes_list)
    
    def apply_nms(self, 
                  boxes: np.ndarray,
                  scores: np.ndarray,
                  classes: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Apply Non-Maximum Suppression using OpenCV.
        
        Args:
            boxes: Array of [N, 4] in format [x1, y1, x2, y2]
            scores: Array of [N] confidence scores
            classes: Array of [N] class IDs
        
        Returns:
            Filtered boxes, scores, classes after NMS
        """
        if len(boxes) == 0:
            return boxes, scores, classes
        
        # Convert boxes to OpenCV format [x, y, w, h]
        boxes_xywh = np.copy(boxes)
        boxes_xywh[:, 2] = boxes[:, 2] - boxes[:, 0]  # width
        boxes_xywh[:, 3] = boxes[:, 3] - boxes[:, 1]  # height
        
        # Apply NMS
        indices = cv2.dnn.NMSBoxes(
            boxes_xywh.tolist(),
            scores.tolist(),
            self.score_threshold,
            self.nms_iou_thresh
        )
        
        if len(indices) == 0:
            return np.array([]), np.array([]), np.array([])
        
        # OpenCV returns indices in different formats depending on version
        if isinstance(indices, tuple):
            indices = indices[0]
        indices = np.array(indices).flatten()
        
        return boxes[indices], scores[indices], classes[indices]
    
    def process_tensors(self,
                       tensors: Dict[str, np.ndarray],
                       img_width: int,
                       img_height: int) -> List[Dict[str, Any]]:
        """
        Process raw Hailo tensors into detections.
        
        Args:
            tensors: Dictionary of {layer_name: tensor_array}
            img_width: Original image width
            img_height: Original image height
        
        Returns:
            List of detection dicts with keys: bbox, confidence, class_id, class_name
        """
        try:
            # Get the output tensor (usually single output for YOLO)
            if len(tensors) == 0:
                logger.warning("No tensors provided")
                return []
            
            # Convert all tensors to float32 if needed
            tensors_float = {}
            for name, tensor in tensors.items():
                tensors_float[name] = self.convert_tensor_format(tensor)
                logger.debug(f"Tensor '{name}': shape={tensor.shape}, dtype={tensor.dtype} -> {tensors_float[name].dtype}")
            
            # Get main output tensor
            # For single output, just take the first one
            output_tensor = list(tensors_float.values())[0]
            
            logger.debug(f"Processing output tensor: shape={output_tensor.shape}")
            
            # Decode predictions based on architecture
            if self.meta_arch in ["yolo_v5", "yolo_v8", "yolo_v11"]:
                boxes, scores, classes = self._yolo5_decode(
                    output_tensor, img_width, img_height
                )
            else:
                logger.error(f"Unsupported architecture: {self.meta_arch}")
                return []
            
            if len(boxes) == 0:
                logger.debug("No detections before NMS")
                return []
            
            logger.debug(f"Before NMS: {len(boxes)} detections")
            
            # Apply NMS
            boxes, scores, classes = self.apply_nms(boxes, scores, classes)
            
            logger.debug(f"After NMS: {len(boxes)} detections")
            
            # Convert to detection format
            detections = []
            for box, score, cls_id in zip(boxes, scores, classes):
                x1, y1, x2, y2 = box
                
                # Convert to xywh format
                x = int(max(0, x1))
                y = int(max(0, y1))
                w = int(min(img_width - x, x2 - x1))
                h = int(min(img_height - y, y2 - y1))
                
                detections.append({
                    'bbox': [x, y, w, h],
                    'confidence': float(score),
                    'class_id': int(cls_id),
                    'class_name': f'class_{int(cls_id)}'  # Will be updated by backend
                })
            
            return detections
            
        except Exception as e:
            logger.error(f"Error in post-processing: {e}")
            import traceback
            traceback.print_exc()
            return []
