# Minimal utils for ByteTrack standalone use

import logging
import numpy as np

# Logger
LOGGER = logging.getLogger(__name__)

def xywh2ltwh(x):
    """
    Convert bounding box coordinates from (x_center, y_center, width, height) to (left, top, width, height).
    
    Args:
        x: np.array of shape (n, 4) containing boxes in xywh format
        
    Returns:
        y: np.array of shape (n, 4) containing boxes in ltwh format
    """
    y = np.copy(x)
    y[..., 0] = x[..., 0] - x[..., 2] / 2  # left = center_x - width/2
    y[..., 1] = x[..., 1] - x[..., 3] / 2  # top = center_y - height/2
    return y
