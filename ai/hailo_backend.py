"""
Hailo AI backend scaffold for Bee Monitoring.

This backend verifies Hailo device availability, optionally loads a HEF model (path via HAILO_HEF),
and exposes an infer(frame) method returning (boxes, scores).

NOTE: This is a scaffold. Actual inference via HailoRT needs model-specific pre/post-processing.
For now, we generate placeholder detections after verifying the device is reachable.
"""
from __future__ import annotations

from typing import List, Tuple, Optional
import os
import subprocess
import numpy as np


class HailoBackend:
    def __init__(self, hef_path: Optional[str] = None) -> None:
        self.hef_path = hef_path
        self.initialized = False

    def _run_cli(self, args: List[str]) -> Tuple[int, str, str]:
        env = dict(os.environ)
        # Ensure logs go to writable directory to avoid warnings
        env.setdefault("HAILORT_LOG_DIR", "/tmp")
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
        out, err = proc.communicate(timeout=10)
        return proc.returncode, out, err

    def initialize(self) -> bool:
        # Verify hailortcli present (absolute path to avoid PATH issues under systemd)
        hailortcli_path = "/usr/bin/hailortcli"
        if not os.path.exists(hailortcli_path):
            return False

        # Identify device to confirm basic connectivity
        rc, out, err = self._run_cli([hailortcli_path, "fw-control", "identify"])
        if rc != 0:
            # Try with sudo as fallback
            sudo_path = "/usr/bin/sudo"
            if os.path.exists(sudo_path):
                rc, out, err = self._run_cli([sudo_path, "env", "HAILORT_LOG_DIR=/tmp", hailortcli_path, "fw-control", "identify"])
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
