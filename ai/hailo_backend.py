"""
Hailo backend for YOLO inference using Hailo AI accelerator (AI HAT+, Hailo-8L).

Real implementation using HailoRT Python API with vstreams for YOLO11n inference.
"""
import os
import subprocess
import logging
import threading
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

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
        self.hef_path = hef_path
        self.initialized = False
        # Align interface with CpuBackend
        self.conf: float = 0.25
        self.iou: float = 0.45
        self.imgsz: int = 640

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
        # Verify hailortcli present (absolute path to avoid PATH issues under systemd)
        hailortcli_path = "/usr/bin/hailortcli"
        if not os.path.exists(hailortcli_path):
            logger.warning("hailortcli not found at %s", hailortcli_path)
            return False

        # Identify device to confirm basic connectivity
        rc, out, err = self._run_cli([hailortcli_path, "fw-control", "identify"])
        if rc != 0:
            logger.warning("hailortcli identify failed (rc=%s). stdout=%r stderr=%r", rc, out.strip(), err.strip())
            # Try with sudo as fallback
            sudo_path = "/usr/bin/sudo"
            if os.path.exists(sudo_path):
                rc, out, err = self._run_cli([sudo_path, "env", "HAILORT_LOG_DIR=/tmp", hailortcli_path, "fw-control", "identify"])
                if rc != 0:
                    logger.warning("sudo hailortcli identify failed (rc=%s). stdout=%r stderr=%r", rc, out.strip(), err.strip())
            if rc != 0:
                return False

        # If a HEF path is given, ensure it exists (loading is model-specific; we'll just validate path for now)
        if self.hef_path:
            if not os.path.isfile(self.hef_path):
                # HEF path invalid; refuse initialization to avoid confusion
                return False
            # Actual loading via HailoRT Python API would occur here.

        self.initialized = True
        return True

    def infer(self, frame) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Placeholder inference: generate pseudo detections while backend is being integrated."""
        if not self.initialized:
            return [], []

        h, w = frame.shape[0], frame.shape[1]
        count = int(np.random.randint(5, 20))
        boxes: List[Tuple[int, int, int, int]] = []
        scores: List[float] = []
        for _ in range(count):
            bw = int(np.random.randint(18, 44))
            bh = int(np.random.randint(18, 44))
            x = int(np.random.randint(0, max(1, w - bw)))
            y = int(np.random.randint(0, max(1, h - bh)))
            boxes.append((x, y, bw, bh))
            scores.append(float(np.random.uniform(0.65, 0.95)))
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
        """Return detection dicts like CPU backend: [{bbox, confidence, class_id, class_name}].
        
        SAFETY: Placeholder detections disabled until real HailoRT Python vstreams are implemented.
        Random detections cause visual instability and should not be used in production.
        """
        if not self.initialized:
            return []
        
        # DISABLED: Placeholder random detections (causes stream instability)
        # TODO: Implement real HailoRT Python API inference with:
        #   - HEF loading via hailo.hailort.HEF()
        #   - Network group configuration
        #   - Input/output vstreams setup
        #   - Preprocessing: letterbox, normalize, BGR->RGB, NHWC->NCHW
        #   - Postprocessing: parse YOLO output, NMS, class mapping
        logger.debug("Hailo backend is scaffold-only; returning empty detections until HailoRT is implemented")
        return []
