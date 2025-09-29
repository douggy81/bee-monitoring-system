"""
YOLOv8 (Ultralytics) CPU backend for Bee Monitoring.

This replaces the simulated detections with real YOLOv8 inference on CPU.
If Ultralytics (and its dependencies) are not available, initialization will fail
gracefully so the caller can decide to fall back to another backend.
"""
from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any
import os
import logging
import numpy as np
try:
    import cv2  # type: ignore
    _cv2_ok = True
except Exception:
    # Attempt to load OpenCV from system site-packages so venv can use apt-installed python3-opencv
    cv2 = None  # type: ignore
    _cv2_ok = False
    try:
        import sys as _sys
        _alt = "/usr/lib/python3/dist-packages"
        if _alt not in _sys.path:
            _sys.path.append(_alt)
        import cv2 as _cv2_try  # type: ignore
        cv2 = _cv2_try  # type: ignore
        _cv2_ok = True
    except Exception:
        pass


logger = logging.getLogger(__name__)


class CpuBackend:
    """YOLOv8 CPU inference backend using the Ultralytics library.

    Typical usage:
        backend = CpuBackend(model_path="api/models/yolov8n.pt")
        backend.initialize()
        detections = backend.infer_full(frame)  # list of dicts with bbox/conf/class
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        imgsz: int = 640,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        classes: Optional[List[int]] = None,
    ) -> None:
        self.initialized = False
        self.model = None  # type: ignore
        self.runtime: Optional[str] = None  # 'ultra' or 'onnx'
        self.ort_session = None  # type: ignore
        self.dnn_net = None  # type: ignore
        self.names: Dict[int, str] = {}
        self.model_path = model_path
        self.imgsz = imgsz
        self.conf = conf_threshold
        self.iou = iou_threshold
        self.classes = classes

    def _resolve_default_model_path(self) -> str:
        # Prefer ONNX to avoid requiring PyTorch on target device
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.abspath(os.path.join(here, os.pardir))
        onnx_path = os.path.join(root, "api", "models", "yolov8n.onnx")
        pt_path = os.path.join(root, "api", "models", "yolov8n.pt")
        return onnx_path if os.path.isfile(onnx_path) else pt_path

    def initialize(self) -> bool:
        """Initialize YOLOv8 via Ultralytics if available, else ONNX Runtime.

        Returns True if loaded, False otherwise.
        """
        weights = self.model_path or self._resolve_default_model_path()
        if not os.path.isfile(weights):
            logger.error("YOLOv8 weights not found at %s", weights)
            return False

        # Try Ultralytics (requires torch)
        try:
            from ultralytics import YOLO  # type: ignore
            self.model = YOLO(weights)
            if hasattr(self.model, "names") and isinstance(self.model.names, (list, dict)):
                if isinstance(self.model.names, list):
                    self.names = {i: n for i, n in enumerate(self.model.names)}
                else:
                    self.names = dict(self.model.names)
            self.model_path = weights
            self.runtime = 'ultra'
            self.initialized = True
            logger.info("YOLOv8 (Ultralytics) initialized with %s", weights)
            return True
        except Exception as e:
            logger.warning("Ultralytics unavailable (%s). Falling back to ONNX Runtime.", e)

        # Fallback to ONNX Runtime (venv only; do not pull system onnxruntime)
        try:
            import onnxruntime as ort  # type: ignore
            try:
                ver = getattr(ort, '__version__', 'unknown')
                logger.info("ONNXRuntime detected: %s", ver)
            except Exception:
                pass
            self.ort_session = ort.InferenceSession(weights, providers=['CPUExecutionProvider'])
            if not self.names:
                # Try to load names from adjacent files or known defaults
                self.names = self._load_class_names(weights)
            self.model_path = weights
            self.runtime = 'onnx'
            self.initialized = True
            logger.info("YOLOv8 (ONNXRuntime) initialized with %s", weights)
            return True
        except Exception as e:
            logger.exception("Failed to initialize ONNX Runtime with %s: %s", weights, e)

        # Final fallback: OpenCV DNN
        try:
            if not _cv2_ok:
                raise RuntimeError("OpenCV not available for DNN fallback")
            self.dnn_net = cv2.dnn.readNetFromONNX(weights)  # type: ignore
            if not self.names:
                self.names = self._load_class_names(weights)
            self.model_path = weights
            self.runtime = 'opencv_dnn'
            self.initialized = True
            logger.info("YOLOv8 (OpenCV DNN) initialized with %s", weights)
            return True
        except Exception as e:
            logger.exception("Failed to initialize OpenCV DNN with %s: %s", weights, e)
            return False

    def infer(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Run YOLOv8 inference and return (boxes_xywh, confidences)."""
        if not self.initialized:
            return [], []

        h, w = frame.shape[:2]
        if self.runtime == 'ultra' and self.model is not None:
            try:
                # Ultralytics accepts numpy array in BGR
                results = self.model(
                    frame,
                    imgsz=self.imgsz,
                    conf=self.conf,
                    iou=self.iou,
                    classes=self.classes,
                    verbose=False,
                )
                r0 = results[0]
                boxes_xyxy = r0.boxes.xyxy.cpu().numpy() if hasattr(r0.boxes, "xyxy") else np.empty((0, 4))
                confs = r0.boxes.conf.cpu().numpy().tolist() if hasattr(r0.boxes, "conf") else []

                boxes_xywh: List[Tuple[int, int, int, int]] = []
                for xyxy in boxes_xyxy:
                    x1, y1, x2, y2 = map(float, xyxy)
                    x1 = max(0, min(w - 1, int(round(x1))))
                    y1 = max(0, min(h - 1, int(round(y1))))
                    x2 = max(0, min(w - 1, int(round(x2))))
                    y2 = max(0, min(h - 1, int(round(y2))))
                    bw = max(1, x2 - x1)
                    bh = max(1, y2 - y1)
                    boxes_xywh.append((x1, y1, bw, bh))

                return boxes_xywh, confs[: len(boxes_xywh)]
            except Exception as e:
                logger.exception("YOLOv8 (Ultralytics) inference failed: %s", e)
                return [], []

        # ONNX Runtime path
        try:
            dets = self._onnx_infer(frame)
            boxes_xywh = [tuple(d['bbox']) for d in dets]
            confs = [float(d['confidence']) for d in dets]
            return boxes_xywh, confs
        except Exception as e:
            logger.exception("YOLOv8 (ONNX) inference failed: %s", e)
            # Try OpenCV DNN
            try:
                dets = self._dnn_infer(frame)
                boxes_xywh = [tuple(d['bbox']) for d in dets]
                confs = [float(d['confidence']) for d in dets]
                return boxes_xywh, confs
            except Exception as e2:
                logger.exception("YOLOv8 (OpenCV DNN) inference failed: %s", e2)
                return [], []

    def infer_full(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Run inference and return list of detection dicts:
        {bbox:[x,y,w,h], confidence:float, class_id:int, class_name:str}
        """
        if not self.initialized:
            return []

        if self.runtime == 'ultra' and self.model is not None:
            try:
                results = self.model(
                    frame,
                    imgsz=self.imgsz,
                    conf=self.conf,
                    iou=self.iou,
                    classes=self.classes,
                    verbose=False,
                )
                r0 = results[0]
                h, w = frame.shape[:2]
                dets: List[Dict[str, Any]] = []

                if not hasattr(r0, "boxes") or r0.boxes is None:
                    return dets

                xyxy = r0.boxes.xyxy.cpu().numpy() if hasattr(r0.boxes, "xyxy") else np.empty((0, 4))
                confs = r0.boxes.conf.cpu().numpy().tolist() if hasattr(r0.boxes, "conf") else []
                clss = (
                    r0.boxes.cls.cpu().numpy().astype(int).tolist() if hasattr(r0.boxes, "cls") else [None] * len(confs)
                )

                for i in range(len(confs)):
                    if i >= len(xyxy):
                        break
                    x1, y1, x2, y2 = map(float, xyxy[i])
                    x1 = max(0, min(w - 1, int(round(x1))))
                    y1 = max(0, min(h - 1, int(round(y1))))
                    x2 = max(0, min(w - 1, int(round(x2))))
                    y2 = max(0, min(h - 1, int(round(y2))))
                    bw = max(1, x2 - x1)
                    bh = max(1, y2 - y1)
                    cid = clss[i] if i < len(clss) else None
                    cname = self.names.get(cid, str(cid)) if cid is not None else "unknown"
                    dets.append({
                        "bbox": [x1, y1, bw, bh],
                        "confidence": float(confs[i]),
                        "class_id": int(cid) if cid is not None else -1,
                        "class_name": cname,
                    })
                return dets
            except Exception as e:
                logger.exception("YOLOv8 (Ultralytics) full inference failed: %s", e)
                return []

        # ONNX path
        try:
            return self._onnx_infer(frame)
        except Exception as e:
            logger.exception("YOLOv8 (ONNX) full inference failed: %s", e)
            # Try OpenCV DNN
            try:
                return self._dnn_infer(frame)
            except Exception as e2:
                logger.exception("YOLOv8 (OpenCV DNN) full inference failed: %s", e2)
                return []

    def close(self) -> None:
        self.initialized = False

    # -----------------------------
    # ONNX helpers (fallback)
    # -----------------------------
    def _letterbox(self, image: np.ndarray, new_shape: int = 640) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Resize and pad image to square keeping aspect ratio. Returns padded image, scale, and padding."""
        h, w = image.shape[:2]
        r = min(new_shape / h, new_shape / w)
        new_unpad = (int(round(w * r)), int(round(h * r)))
        dw, dh = new_shape - new_unpad[0], new_shape - new_unpad[1]
        dw //= 2
        dh //= 2
        if _cv2_ok:
            resized = cv2.resize(image, new_unpad, interpolation=cv2.INTER_LINEAR)
            top, bottom, left, right = dh, dh, dw, dw
            color = (114, 114, 114)
            padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        else:
            # Fallback via Pillow if available
            try:
                from PIL import Image  # type: ignore
                resized = np.array(Image.fromarray(image).resize(new_unpad, Image.BILINEAR))
            except Exception:
                # As a last resort, simple naive resize
                resized = np.zeros((new_unpad[1], new_unpad[0], 3), dtype=image.dtype)
                yy = np.linspace(0, image.shape[0]-1, new_unpad[1]).astype(np.int32)
                xx = np.linspace(0, image.shape[1]-1, new_unpad[0]).astype(np.int32)
                resized = image[yy][:, xx]
            padded = np.full((new_shape, new_shape, 3), 114, dtype=resized.dtype)
            padded[dh:dh + resized.shape[0], dw:dw + resized.shape[1]] = resized
        return padded, r, (dw, dh)

    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_thres: float) -> List[int]:
        if boxes.size == 0:
            return []
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep: List[int] = []
        while order.size > 0:
            i = order[0]
            keep.append(int(i))
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            denom = areas[i] + areas[order[1:]] - inter + 1e-6
            ovr = inter / denom
            inds = np.where(ovr <= iou_thres)[0]
            order = order[inds + 1]
        return keep

    def _onnx_infer(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Run ONNX Runtime inference and return detection dicts compatible with Ultralytics output."""
        if self.ort_session is None:
            return []
        h0, w0 = frame.shape[:2]
        # BGR->RGB for typical ONNX models
        img_rgb = frame[:, :, ::-1]
        img_lb, r, (dw, dh) = self._letterbox(img_rgb, self.imgsz)
        img_in = img_lb.astype(np.float32) / 255.0
        img_in = np.transpose(img_in, (2, 0, 1))[None]  # 1x3xH xW
        input_name = self.ort_session.get_inputs()[0].name
        outputs = self.ort_session.run(None, {input_name: img_in})
        pred = outputs[0]
        # Normalize shape to (N, 4+num_classes)
        if pred.ndim == 3:
            pred = np.squeeze(pred, 0)
        if pred.shape[0] in (84, 5 + 80):
            pred = pred.T
        # Split
        boxes_xywh = pred[:, :4]
        class_conf = pred[:, 4:]
        class_ids = np.argmax(class_conf, axis=1)
        scores = class_conf.max(axis=1)
        # Confidence threshold
        mask = scores >= float(self.conf)
        if self.classes is not None:
            mask = mask & np.isin(class_ids, np.array(self.classes))
        boxes_xywh = boxes_xywh[mask]
        class_ids = class_ids[mask]
        scores = scores[mask]
        if boxes_xywh.size == 0:
            return []
        # xywh -> xyxy on letterboxed image scale
        cx, cy, bw, bh = boxes_xywh.T
        x1 = cx - bw / 2
        y1 = cy - bh / 2
        x2 = cx + bw / 2
        y2 = cy + bh / 2
        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)
        # Undo letterbox: remove padding, then divide by scale
        boxes_xyxy[:, [0, 2]] -= dw
        boxes_xyxy[:, [1, 3]] -= dh
        boxes_xyxy /= r
        # Clip to image
        boxes_xyxy[:, 0::2] = np.clip(boxes_xyxy[:, 0::2], 0, w0 - 1)
        boxes_xyxy[:, 1::2] = np.clip(boxes_xyxy[:, 1::2], 0, h0 - 1)
        # NMS
        keep = self._nms(boxes_xyxy, scores, float(self.iou))
        boxes_xyxy = boxes_xyxy[keep]
        scores = scores[keep]
        class_ids = class_ids[keep]
        # Build detections
        dets: List[Dict[str, Any]] = []
        for i in range(len(scores)):
            xx1, yy1, xx2, yy2 = boxes_xyxy[i]
            bw = max(1, int(round(xx2 - xx1)))
            bh = max(1, int(round(yy2 - yy1)))
            x = max(0, int(round(xx1)))
            y = max(0, int(round(yy1)))
            cid = int(class_ids[i])
            cname = self.names.get(cid, str(cid))
            dets.append({
                "bbox": [x, y, bw, bh],
                "confidence": float(scores[i]),
                "class_id": cid,
                "class_name": cname,
            })
        return dets

    # -----------------------------
    # Names utilities
    # -----------------------------
    def _load_class_names(self, weights_path: str) -> Dict[int, str]:
        """Attempt to load class names, preferring adjacent files, else use COCO names.
        Returns a mapping {class_id: class_name}.
        """
        # 1) Try sibling files next to the weights
        base, _ = os.path.splitext(weights_path)
        candidates = [
            base + ".names",
            os.path.join(os.path.dirname(weights_path), "classes.names"),
            os.path.join(os.path.dirname(weights_path), "classes.txt"),
            # Project default
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "models", "coco.names"),
        ]
        for p in candidates:
            try:
                if os.path.isfile(p):
                    with open(p, "r", encoding="utf-8") as f:
                        names = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
                    if names:
                        return {i: n for i, n in enumerate(names)}
            except Exception:
                continue
        # 2) If filename suggests standard YOLOv8 COCO model, return COCO-80 names
        fname = os.path.basename(weights_path).lower()
        if "yolov8" in fname:
            return {i: n for i, n in enumerate(self._coco80_names())}
        # 3) Fallback: numeric IDs
        return {i: str(i) for i in range(80)}

    def _coco80_names(self) -> List[str]:
        # Standard YOLOv8 COCO class names (80 classes)
        return [
            "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat","traffic light",
            "fire hydrant","stop sign","parking meter","bench","bird","cat","dog","horse","sheep","cow",
            "elephant","bear","zebra","giraffe","backpack","umbrella","handbag","tie","suitcase","frisbee",
            "skis","snowboard","sports ball","kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket","bottle",
            "wine glass","cup","fork","knife","spoon","bowl","banana","apple","sandwich","orange",
            "broccoli","carrot","hot dog","pizza","donut","cake","chair","couch","potted plant","bed",
            "dining table","toilet","tv","laptop","mouse","remote","keyboard","cell phone","microwave","oven",
            "toaster","sink","refrigerator","book","clock","vase","scissors","teddy bear","hair drier","toothbrush",
        ]

    def _dnn_infer(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Run OpenCV DNN on ONNX weights and return detection dicts."""
        if not _cv2_ok or self.dnn_net is None:
            return []
        h0, w0 = frame.shape[:2]
        # Letterbox to square then blob
        img_rgb = frame[:, :, ::-1]
        img_lb, r, (dw, dh) = self._letterbox(img_rgb, self.imgsz)
        blob = cv2.dnn.blobFromImage(img_lb, scalefactor=1/255.0, size=(self.imgsz, self.imgsz), swapRB=True, crop=False)  # type: ignore
        self.dnn_net.setInput(blob)
        out = self.dnn_net.forward()
        pred = out
        if pred.ndim == 3:
            pred = np.squeeze(pred, 0)
        if pred.shape[0] in (84, 5 + 80):
            pred = pred.T
        boxes_xywh = pred[:, :4]
        class_conf = pred[:, 4:]
        class_ids = np.argmax(class_conf, axis=1)
        scores = class_conf.max(axis=1)
        mask = scores >= float(self.conf)
        if self.classes is not None:
            mask = mask & np.isin(class_ids, np.array(self.classes))
        boxes_xywh = boxes_xywh[mask]
        class_ids = class_ids[mask]
        scores = scores[mask]
        if boxes_xywh.size == 0:
            return []
        cx, cy, bw, bh = boxes_xywh.T
        x1 = cx - bw / 2
        y1 = cy - bh / 2
        x2 = cx + bw / 2
        y2 = cy + bh / 2
        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)
        boxes_xyxy[:, [0, 2]] -= dw
        boxes_xyxy[:, [1, 3]] -= dh
        boxes_xyxy /= r
        boxes_xyxy[:, 0::2] = np.clip(boxes_xyxy[:, 0::2], 0, w0 - 1)
        boxes_xyxy[:, 1::2] = np.clip(boxes_xyxy[:, 1::2], 0, h0 - 1)
        keep = self._nms(boxes_xyxy, scores, float(self.iou))
        boxes_xyxy = boxes_xyxy[keep]
        scores = scores[keep]
        class_ids = class_ids[keep]
        dets: List[Dict[str, Any]] = []
        for i in range(len(scores)):
            xx1, yy1, xx2, yy2 = boxes_xyxy[i]
            bw = max(1, int(round(xx2 - xx1)))
            bh = max(1, int(round(yy2 - yy1)))
            x = max(0, int(round(xx1)))
            y = max(0, int(round(yy1)))
            cid = int(class_ids[i])
            cname = self.names.get(cid, str(cid))
            dets.append({
                "bbox": [x, y, bw, bh],
                "confidence": float(scores[i]),
                "class_id": cid,
                "class_name": cname,
            })
        return dets
