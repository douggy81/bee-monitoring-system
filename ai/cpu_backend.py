"""
CPU (simulated) AI backend for Bee Monitoring.
Produces random detections shaped like YOLO-style (x, y, w, h) with confidence scores,
so the rest of the pipeline can be exercised without hardware.
"""
from __future__ import annotations

from typing import List, Tuple
import numpy as np


class CpuBackend:
    def __init__(self) -> None:
        self.initialized = False

    def initialize(self) -> bool:
        # Nothing to initialize for the simulated CPU backend
        self.initialized = True
        return True

    def infer(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Return simulated detections for the given frame.
        Boxes are (x, y, w, h) in pixel coordinates, confidences in [0, 1].
        """
        if not self.initialized:
            return [], []

        h, w = frame.shape[0], frame.shape[1]
        count = int(np.random.randint(5, 25))
        boxes: List[Tuple[int, int, int, int]] = []
        scores: List[float] = []
        for _ in range(count):
            bw = int(np.random.randint(20, 50))
            bh = int(np.random.randint(20, 50))
            x = int(np.random.randint(0, max(1, w - bw)))
            y = int(np.random.randint(0, max(1, h - bh)))
            boxes.append((x, y, bw, bh))
            scores.append(float(np.random.uniform(0.7, 0.95)))
        return boxes, scores

    def close(self) -> None:
        self.initialized = False
