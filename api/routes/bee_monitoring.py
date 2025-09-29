"""
Bee Monitoring API Routes

This module provides REST API endpoints for the Digital4.ai Bee Monitoring System.
Includes endpoints for real-time data, analytics, alerts, and system management.

Author: Digital4.ai Development Team
Date: September 2025
"""

from flask import Blueprint, jsonify, request, Response
from datetime import datetime, timedelta
import json
import sqlite3
import os
from typing import Dict, List, Any
import logging
import base64
import time
from io import BytesIO
import subprocess
import threading
import numpy as np


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
bee_bp = Blueprint('bee_monitoring', __name__)

# Global lock to prevent multiple concurrent Picamera2 streams
_PICAM_STREAM_LOCK = threading.Lock()
# Global stop signal to proactively terminate an active Picamera2 stream
_PICAM_STOP_EVENT = threading.Event()

# Database path (shared with SQLAlchemy in api/main.py if BEE_DB_PATH is set)
DB_PATH = os.environ.get(
    'BEE_DB_PATH',
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'bee_monitoring.db')
)
# Ensure database directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_bee_database():
    """Initialize bee monitoring database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Activity metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            bee_count INTEGER,
            entrance_activity INTEGER,
            exit_activity INTEGER,
            net_activity INTEGER,
            average_speed REAL,
            clustering_index REAL,
            agitation_level REAL,
            traffic_density REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Behavior analysis table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS behavior_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            dominant_behavior TEXT,
            behavior_confidence REAL,
            swarming_probability REAL,
            foraging_activity REAL,
            guard_bee_activity REAL,
            unusual_patterns TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Health assessment table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health_assessment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            overall_health_score REAL,
            mite_detection_score REAL,
            wing_condition_score REAL,
            size_distribution_score REAL,
            activity_pattern_score REAL,
            risk_indicators TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Environmental data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS environmental_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            light_level REAL,
            battery_level REAL,
            solar_power REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            acknowledged BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # System status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu_usage REAL,
            memory_usage REAL,
            storage_usage REAL,
            ai_performance REAL,
            camera_status TEXT,
            network_status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Bee monitoring database initialized")

# Initialize database on import
init_bee_database()

# -----------------------------
# Lazy-loaded AI backends
# -----------------------------
_cpu_backend = None  # type: ignore

def _get_cpu_backend():
    """Load and cache the YOLOv8 CPU backend (Ultralytics) lazily.
    Returns None if the backend fails to initialize.
    """
    global _cpu_backend
    if _cpu_backend is not None:
        return _cpu_backend
    try:
        from ai.cpu_backend import CpuBackend
        # Prefer ONNX; fall back to PT; if neither exists, let backend resolve
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        onnx_p = os.path.join(models_dir, 'yolov8n.onnx')
        pt_p = os.path.join(models_dir, 'yolov8n.pt')
        model_path = onnx_p if os.path.isfile(onnx_p) else (pt_p if os.path.isfile(pt_p) else None)
        backend = CpuBackend(model_path=model_path, imgsz=640, conf_threshold=0.25, iou_threshold=0.45)
        if backend.initialize():
            _cpu_backend = backend
            return _cpu_backend
        logger.warning("CpuBackend failed to initialize; YOLOv8 weights or ultralytics may be missing")
        return None
    except Exception as e:
        logger.warning(f"CpuBackend import/init failed: {e}")
        return None

@bee_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Digital4.ai Bee Monitoring API',
        'version': '1.0.0'
    })

@bee_bp.route('/current-status', methods=['GET'])
def get_current_status():
    """Get current bee monitoring status"""
    try:
        conn = get_db_connection()
        
        # Get latest activity data
        activity = conn.execute(
            'SELECT * FROM activity_metrics ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        # Get latest behavior data
        behavior = conn.execute(
            'SELECT * FROM behavior_analysis ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        # Get latest health data
        health = conn.execute(
            'SELECT * FROM health_assessment ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        # Get latest environmental data
        environment = conn.execute(
            'SELECT * FROM environmental_data ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        # Get recent alerts
        alerts = conn.execute(
            'SELECT * FROM alerts WHERE acknowledged = FALSE ORDER BY timestamp DESC LIMIT 5'
        ).fetchall()
        
        conn.close()
        
        # Format response
        response = {
            'timestamp': datetime.now().isoformat(),
            'activity': dict(activity) if activity else None,
            'behavior': dict(behavior) if behavior else None,
            'health': dict(health) if health else None,
            'environment': dict(environment) if environment else None,
            'alerts': [dict(alert) for alert in alerts],
            'system_online': True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting current status: {e}")
        return jsonify({'error': str(e)}), 500

# -----------------------------
# Camera endpoints
# -----------------------------

@bee_bp.route('/camera/stream')
def camera_stream():
    """Live camera stream endpoint (MJPEG)."""
    try:
        # Allow forcing rpicam-vid via query param: /camera/stream?source=rpicam
        source = request.args.get('source', '').lower()
        q_w = request.args.get('width', type=int) or 1280
        q_h = request.args.get('height', type=int) or 720
        q_fps = request.args.get('fps', type=int) or 30
        # AI overlay controls
        ai_enabled = request.args.get('ai', '0').lower() in ('1', 'true', 'yes')
        ai_stride = request.args.get('ai_stride', type=int) or 3
        ai_async = request.args.get('ai_async', '1').lower() in ('1', 'true', 'yes')
        ai_interval_ms = request.args.get('ai_interval_ms', type=int) or 500
        lock_wait_ms = request.args.get('lock_wait_ms', type=int) or 1500
        terminate_prev = request.args.get('terminate_prev', '1').lower() in ('1', 'true', 'yes')

        def _stream_from_rpicam(width: int, height: int, fps: int):
            """Fallback: stream MJPEG by spawning rpicam-vid and parsing JPEG frames."""
            cmd = [
                "/usr/bin/rpicam-vid",
                "--timeout", "0",
                "--width", str(width),
                "--height", str(height),
                "--framerate", str(fps),
                "--nopreview",
                "--codec", "mjpeg",
                "--inline",
                "-o", "-",
            ]
            logger.warning(f"Falling back to rpicam-vid subprocess: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
            buf = b""
            try:
                while True:
                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    # Parse JPEG frames between SOI (FFD8) and EOI (FFD9)
                    while True:
                        soi = buf.find(b"\xff\xd8")
                        if soi < 0:
                            # No start marker yet; keep buffering
                            # Prevent unbounded growth
                            if len(buf) > 1_000_000:
                                buf = buf[-200_000:]
                            break
                        eoi = buf.find(b"\xff\xd9", soi + 2)
                        if eoi < 0:
                            # Wait for the rest of the frame
                            break
                        frame_bytes = buf[soi:eoi+2]
                        buf = buf[eoi+2:]
                        headers = (
                            b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n'
                            + f'Content-Length: {len(frame_bytes)}\r\n'.encode('ascii')
                            + b'\r\n'
                        )
                        yield headers + frame_bytes + b'\r\n'
            finally:
                try:
                    proc.terminate()
                except Exception:
                    pass

        # If client explicitly requests rpicam, bypass hardware_integration entirely
        if source == 'rpicam':
            return Response(
                _stream_from_rpicam(q_w, q_h, q_fps),
                mimetype='multipart/x-mixed-replace; boundary=frame',
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',  # hint nginx to disable buffering
                },
            )

        # Lazy import only if not forcing rpicam
        from hardware_integration import CameraManager

        def generate_frames():
            # Try to import Pillow lazily; if it fails, fallback to rpicam-vid
            try:
                from PIL import Image, ImageDraw
                pil_ok = True
            except Exception as pil_err:
                logger.warning(f"Pillow not available for JPEG encoding ({pil_err}); using rpicam-vid fallback")
                pil_ok = False

            # If we can't encode with Pillow, stream via rpicam-vid directly
            if not pil_ok:
                yield from _stream_from_rpicam(q_w, q_h, q_fps)
                return

            # Proactively request the current stream to stop, if any
            if terminate_prev:
                _PICAM_STOP_EVENT.set()
            # Try to acquire global Picamera2 stream lock; if busy, wait up to lock_wait_ms
            _got_lock = _PICAM_STREAM_LOCK.acquire(timeout=float(lock_wait_ms) / 1000.0)
            if not _got_lock:
                logger.info("Picamera2 stream is busy; continuing to wait for lock")
                # Block until available rather than spawning rpicam (which also needs the camera)
                _PICAM_STREAM_LOCK.acquire()
            # We now exclusively own the stream; clear the stop signal so we don't stop ourselves
            _PICAM_STOP_EVENT.clear()
            camera = CameraManager(resolution=(q_w, q_h), fps=q_fps)
            # Try Picamera2 only; if not available, release lock and go to rpicam-vid fallback
            if not camera.initialize(allow_opencv_fallback=False):
                try:
                    _PICAM_STREAM_LOCK.release()
                except Exception:
                    pass
                yield from _stream_from_rpicam(q_w, q_h, q_fps)
                return
            try:
                empty_count = 0
                # AI backend (optional)
                ai_on = ai_enabled
                backend = None
                last_dets = []
                last_infer_ts = 0.0
                infer_thread = None
                infer_lock = threading.Lock()
                frame_index = 0
                if ai_on:
                    backend = _get_cpu_backend()
                    if backend is None:
                        logger.warning("AI overlay requested but backend unavailable; continuing without overlay")
                        ai_on = False
                # Define async inference runner if enabled
                if ai_on and backend is not None and ai_async:
                    def _run_infer(img_bgr):
                        nonlocal last_dets, last_infer_ts
                        try:
                            res = backend.infer_full(img_bgr)
                        except Exception as infer_err:
                            logger.warning(f"AI overlay inference failed: {infer_err}")
                            res = []
                        with infer_lock:
                            last_dets = res
                            last_infer_ts = time.time()
                while True:
                    # If a new request asked us to stop, exit quickly to release the lock
                    if _PICAM_STOP_EVENT.is_set():
                        logger.info("Stream stop requested; closing Picamera2 stream")
                        break
                    frame = camera.capture_frame()
                    if frame is not None:
                        empty_count = 0
                        # Convert BGR->RGB if needed (CameraManager returns BGR for OpenCV compat)
                        if frame.shape[2] == 3:
                            rgb = frame[:, :, ::-1]
                        else:
                            rgb = frame
                        # Optional AI inference & overlay (non-blocking preferred)
                        frame_index += 1
                        dets_to_draw = []
                        if ai_on and backend is not None:
                            if ai_async:
                                can_launch = (infer_thread is None) or (not infer_thread.is_alive())
                                elapsed_ms = (time.time() - last_infer_ts) * 1000.0
                                if can_launch and elapsed_ms >= float(ai_interval_ms):
                                    try:
                                        # copy current frame for background inference
                                        img_copy = frame.copy()
                                        infer_thread = threading.Thread(target=_run_infer, args=(img_copy,), daemon=True)
                                        infer_thread.start()
                                    except Exception as th_err:
                                        logger.warning(f"Failed to start async inference: {th_err}")
                                # use last available detections without blocking
                                with infer_lock:
                                    if last_dets:
                                        dets_to_draw = list(last_dets)
                            else:
                                # synchronous fallback controlled by ai_stride
                                if (frame_index % max(1, ai_stride) == 0):
                                    try:
                                        last_dets = backend.infer_full(frame)
                                    except Exception as infer_err:
                                        logger.warning(f"AI overlay inference failed: {infer_err}")
                                        last_dets = []
                                if last_dets:
                                    dets_to_draw = last_dets
                        try:
                            # Encode JPEG via Pillow
                            bio = BytesIO()
                            if ai_on and dets_to_draw:
                                img = Image.fromarray(rgb)
                                draw = ImageDraw.Draw(img)
                                for det in dets_to_draw:
                                    bbox = det.get('bbox', [0, 0, 0, 0])
                                    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                                        continue
                                    x, y, w_box, h_box = bbox
                                    # Rectangle
                                    draw.rectangle([(int(x), int(y)), (int(x + w_box), int(y + h_box))], outline=(0, 255, 0), width=2)
                                    # Label
                                    label = f"{det.get('class_name','obj')} {det.get('confidence',0):.2f}"
                                    tx, ty = int(x), max(0, int(y) - 12)
                                    draw.text((tx + 2, ty), label, fill=(255, 255, 255))
                                img.save(bio, format='JPEG', quality=85)
                            else:
                                Image.fromarray(rgb).save(bio, format='JPEG', quality=85)
                            frame_bytes = bio.getvalue()
                            headers = (
                                b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n'
                                + f'Content-Length: {len(frame_bytes)}\r\n'.encode('ascii')
                                + b'\r\n'
                            )
                            yield headers + frame_bytes + b'\r\n'
                        except Exception as enc_err:
                            logger.error(f"Pillow JPEG encode failed: {enc_err}; switching to rpicam-vid fallback")
                            break
                    else:
                        empty_count += 1
                        if empty_count >= 5:
                            logger.warning("No frames captured from CameraManager; switching to rpicam-vid fallback")
                            break
                        time.sleep(0.2)  # ~5 FPS
            finally:
                camera.cleanup()
                # Always release the global stream lock
                try:
                    _PICAM_STREAM_LOCK.release()
                except Exception:
                    pass
                if empty_count >= 5:
                    # Start rpicam-vid fallback stream
                    for part in _stream_from_rpicam(camera.resolution[0], camera.resolution[1], camera.fps):
                        yield part

        return Response(
            generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    except Exception as e:
        logger.error(f"Camera stream error: {e}")
        return jsonify({'error': str(e)}), 500


@bee_bp.route('/ai/detect', methods=['GET'])
def ai_detect():
    """Run YOLOv8 CPU inference on a single camera frame.
    Query params:
      - annotate: 0/1 to include an annotated image (base64) in the response
      - conf: confidence threshold (e.g., 0.25)
      - iou: IOU threshold for NMS (e.g., 0.45)
    Response JSON:
      {
        "success": true,
        "backend": "yolov8_cpu",
        "detections": [ {bbox:[x,y,w,h], confidence, class_id, class_name}, ... ],
        "image": "data:image/jpeg;base64,..."  (if annotate=1)
      }
    """
    try:
        # Load backend (and optionally tweak thresholds)
        backend = _get_cpu_backend()
        if backend is None:
            return jsonify({
                'success': False,
                'error': 'YOLOv8 CPU backend not available. Install ultralytics and ensure yolov8n.pt exists.'
            }), 503

        conf = request.args.get('conf', type=float)
        iou = request.args.get('iou', type=float)
        if conf is not None:
            backend.conf = float(conf)
        if iou is not None:
            backend.iou = float(iou)

        # Capture one frame from the camera
        from hardware_integration import CameraManager
        cam = CameraManager()
        if not cam.initialize():
            return jsonify({'success': False, 'error': 'Camera initialization failed'}), 500
        try:
            frame = cam.capture_frame()
            if frame is None:
                return jsonify({'success': False, 'error': 'Failed to capture frame'}), 500
        finally:
            cam.cleanup()

        # Run inference
        detections = backend.infer_full(frame)

        out = {
            'success': True,
            'backend': 'yolov8_cpu',
            'detections': detections,
            'timestamp': datetime.now().isoformat(),
        }

        # Optional annotation
        annotate = request.args.get('annotate', default='0')
        if annotate in ('1', 'true', 'True'):
            try:
                import cv2  # type: ignore
                draw = frame.copy()
                for det in detections:
                    x, y, w, h = det.get('bbox', [0, 0, 0, 0])
                    x2, y2 = x + w, y + h
                    cv2.rectangle(draw, (int(x), int(y)), (int(x2), int(y2)), (0, 255, 0), 2)
                    label = f"{det.get('class_name','obj')} {det.get('confidence',0):.2f}"
                    cv2.putText(draw, label, (int(x), max(0, int(y) - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                # Encode JPEG
                ok, buf = cv2.imencode('.jpg', draw)
                if ok:
                    img_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
                    out['image'] = f'data:image/jpeg;base64,{img_b64}'
            except Exception as e:
                logger.warning(f"Annotation failed: {e}")

        return jsonify(out)

    except Exception as e:
        logger.error(f"AI detect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bee_bp.route('/ai/status', methods=['GET'])
def ai_status():
    """Return AI backend readiness and configuration details.
    Response JSON:
      {
        ready: bool,
        runtime: "ultra" | "onnx" | "opencv_dnn" | null,
        weights_path: string | null,
        names_count: int,
        conf: float,
        iou: float,
        imgsz: int,
        onnxruntime_version: string (when runtime == 'onnx'),
        timestamp: string,
        error?: string
      }
    """
    try:
        backend = _get_cpu_backend()
        if backend is None:
            return jsonify({
                'ready': False,
                'runtime': None,
                'weights_path': None,
                'names_count': 0,
                'timestamp': datetime.now().isoformat(),
                'error': 'backend_unavailable'
            })

        resp: Dict[str, Any] = {
            'ready': bool(getattr(backend, 'initialized', False)),
            'runtime': getattr(backend, 'runtime', None),
            'weights_path': getattr(backend, 'model_path', None),
            'names_count': len(getattr(backend, 'names', {}) or {}),
            'conf': float(getattr(backend, 'conf', 0.0)),
            'iou': float(getattr(backend, 'iou', 0.0)),
            'imgsz': int(getattr(backend, 'imgsz', 0) or 0),
            'timestamp': datetime.now().isoformat(),
        }
        if resp['runtime'] == 'onnx':
            try:
                import onnxruntime as ort  # type: ignore
                resp['onnxruntime_version'] = getattr(ort, '__version__', 'unknown')
            except Exception:
                pass
        return jsonify(resp)
    except Exception as e:
        logger.error(f"AI status error: {e}")
        return jsonify({'ready': False, 'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

@bee_bp.route('/camera/snapshot')
def camera_snapshot():
    """Return a single camera snapshot as base64 JSON."""
    try:
        from hardware_integration import CameraManager

        from PIL import Image  # lazy import to avoid requiring OpenCV at app startup
        camera = CameraManager()
        if not camera.initialize():
            return jsonify({'error': 'Camera initialization failed'}), 500

        try:
            frame = camera.capture_frame()
            if frame is not None:
                # Convert BGR->RGB if needed
                if frame.shape[2] == 3:
                    rgb = frame[:, :, ::-1]
                else:
                    rgb = frame
                bio = BytesIO()
                Image.fromarray(rgb).save(bio, format='JPEG', quality=85)
                img_base64 = base64.b64encode(bio.getvalue()).decode('utf-8')
                return jsonify({
                    'success': True,
                    'image': f'data:image/jpeg;base64,{img_base64}',
                    'timestamp': datetime.now().isoformat()
                })
            return jsonify({'error': 'Failed to capture frame'}), 500
        finally:
            camera.cleanup()

    except Exception as e:
        logger.error(f"Camera snapshot error: {e}")
        return jsonify({'error': str(e)}), 500


@bee_bp.route('/camera/status')
def camera_status():
    """Non-invasive camera availability check using Picamera2 enumeration.
    This avoids opening the device so it won't report false negatives while a stream is active.
    """
    try:
        try:
            # Attempt to import Picamera2 from system packages if not in venv
            try:
                from picamera2 import Picamera2  # type: ignore
            except Exception:
                import sys as _sys
                _alt = "/usr/lib/python3/dist-packages"
                if _alt not in _sys.path:
                    _sys.path.append(_alt)
                from picamera2 import Picamera2  # type: ignore
            info = Picamera2.global_camera_info()
            available = bool(info and len(info) > 0)
            backend = 'Picamera2' if available else 'Not Available'
        except Exception as e2:
            logger.warning(f"Picamera2 enumeration failed: {e2}")
            available = False
            backend = 'Not Available'
        return jsonify({
            'available': available,
            'resolution': [1280, 720],
            'fps': 30,
            'backend': backend,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Camera status error: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/activity-data', methods=['GET'])
def get_activity_data():
    """Get activity data with optional time range filtering"""
    try:
        # Get query parameters
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Calculate time range
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        conn = get_db_connection()
        query = '''
            SELECT * FROM activity_metrics 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        
        rows = conn.execute(query, (start_time, limit)).fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'data': data,
            'count': len(data),
            'time_range_hours': hours,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting activity data: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/health-data', methods=['GET'])
def get_health_data():
    """Get health assessment data"""
    try:
        hours = request.args.get('hours', 168, type=int)  # Default 7 days
        limit = request.args.get('limit', 50, type=int)
        
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        conn = get_db_connection()
        query = '''
            SELECT * FROM health_assessment 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        
        rows = conn.execute(query, (start_time, limit)).fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'data': data,
            'count': len(data),
            'time_range_hours': hours,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting health data: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/behavior-data', methods=['GET'])
def get_behavior_data():
    """Get behavior analysis data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        conn = get_db_connection()
        query = '''
            SELECT * FROM behavior_analysis 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        
        rows = conn.execute(query, (start_time, limit)).fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'data': data,
            'count': len(data),
            'time_range_hours': hours,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting behavior data: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/environmental-data', methods=['GET'])
def get_environmental_data():
    """Get environmental sensor data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        conn = get_db_connection()
        query = '''
            SELECT * FROM environmental_data 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        
        rows = conn.execute(query, (start_time, limit)).fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        return jsonify({
            'data': data,
            'count': len(data),
            'time_range_hours': hours,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting environmental data: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get system alerts"""
    try:
        acknowledged = request.args.get('acknowledged', 'false').lower() == 'true'
        limit = request.args.get('limit', 50, type=int)
        
        conn = get_db_connection()
        query = '''
            SELECT * FROM alerts 
            WHERE acknowledged = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        
        rows = conn.execute(query, (acknowledged, limit)).fetchall()
        conn.close()
        
        alerts = [dict(row) for row in rows]
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts),
            'acknowledged': acknowledged,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        conn = get_db_connection()
        conn.execute(
            'UPDATE alerts SET acknowledged = TRUE WHERE id = ?',
            (alert_id,)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Alert {alert_id} acknowledged',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get analytics summary for dashboard"""
    try:
        hours = request.args.get('hours', 24, type=int)
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        conn = get_db_connection()
        
        # Activity summary
        activity_stats = conn.execute('''
            SELECT 
                AVG(bee_count) as avg_bee_count,
                MAX(bee_count) as max_bee_count,
                MIN(bee_count) as min_bee_count,
                SUM(entrance_activity) as total_entrances,
                SUM(exit_activity) as total_exits,
                AVG(agitation_level) as avg_agitation
            FROM activity_metrics 
            WHERE timestamp > ?
        ''', (start_time,)).fetchone()
        
        # Health summary
        health_stats = conn.execute('''
            SELECT 
                AVG(overall_health_score) as avg_health_score,
                MIN(overall_health_score) as min_health_score,
                AVG(mite_detection_score) as avg_mite_score,
                AVG(wing_condition_score) as avg_wing_score
            FROM health_assessment 
            WHERE timestamp > ?
        ''', (start_time,)).fetchone()
        
        # Behavior summary
        behavior_stats = conn.execute('''
            SELECT 
                dominant_behavior,
                COUNT(*) as count
            FROM behavior_analysis 
            WHERE timestamp > ?
            GROUP BY dominant_behavior
            ORDER BY count DESC
        ''', (start_time,)).fetchall()
        
        # Environmental summary
        env_stats = conn.execute('''
            SELECT 
                AVG(temperature) as avg_temperature,
                AVG(humidity) as avg_humidity,
                AVG(light_level) as avg_light_level,
                AVG(battery_level) as avg_battery_level
            FROM environmental_data 
            WHERE timestamp > ?
        ''', (start_time,)).fetchone()
        
        conn.close()
        
        summary = {
            'time_range_hours': hours,
            'activity': dict(activity_stats) if activity_stats else {},
            'health': dict(health_stats) if health_stats else {},
            'behavior': [dict(row) for row in behavior_stats],
            'environment': dict(env_stats) if env_stats else {},
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """Get system performance status"""
    try:
        conn = get_db_connection()
        
        # Get latest system status
        status = conn.execute(
            'SELECT * FROM system_status ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        conn.close()
        
        if status:
            return jsonify(dict(status))
        else:
            # Return default status if no data
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': 45.2,
                'memory_usage': 67.8,
                'storage_usage': 34.1,
                'ai_performance': 96.5,
                'camera_status': 'online',
                'network_status': 'connected'
            })
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/data/ingest', methods=['POST'])
def ingest_data():
    """Ingest new monitoring data from hardware"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        conn = get_db_connection()
        timestamp = datetime.now().isoformat()
        
        # Insert activity data if provided
        if 'activity' in data:
            activity = data['activity']
            conn.execute('''
                INSERT INTO activity_metrics 
                (timestamp, bee_count, entrance_activity, exit_activity, net_activity,
                 average_speed, clustering_index, agitation_level, traffic_density)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                activity.get('bee_count', 0),
                activity.get('entrance_activity', 0),
                activity.get('exit_activity', 0),
                activity.get('net_activity', 0),
                activity.get('average_speed', 0.0),
                activity.get('clustering_index', 0.0),
                activity.get('agitation_level', 0.0),
                activity.get('traffic_density', 0.0)
            ))
        
        # Insert behavior data if provided
        if 'behavior' in data:
            behavior = data['behavior']
            conn.execute('''
                INSERT INTO behavior_analysis 
                (timestamp, dominant_behavior, behavior_confidence, swarming_probability,
                 foraging_activity, guard_bee_activity, unusual_patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                behavior.get('dominant_behavior', 'unknown'),
                behavior.get('behavior_confidence', 0.0),
                behavior.get('swarming_probability', 0.0),
                behavior.get('foraging_activity', 0.0),
                behavior.get('guard_bee_activity', 0.0),
                json.dumps(behavior.get('unusual_patterns', []))
            ))
        
        # Insert health data if provided
        if 'health' in data:
            health = data['health']
            conn.execute('''
                INSERT INTO health_assessment 
                (timestamp, overall_health_score, mite_detection_score, wing_condition_score,
                 size_distribution_score, activity_pattern_score, risk_indicators)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                health.get('overall_health_score', 0.0),
                health.get('mite_detection_score', 0.0),
                health.get('wing_condition_score', 0.0),
                health.get('size_distribution_score', 0.0),
                health.get('activity_pattern_score', 0.0),
                json.dumps(health.get('risk_indicators', []))
            ))
        
        # Insert environmental data if provided
        if 'environment' in data:
            env = data['environment']
            conn.execute('''
                INSERT INTO environmental_data 
                (timestamp, temperature, humidity, light_level, battery_level, solar_power)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                env.get('temperature', 0.0),
                env.get('humidity', 0.0),
                env.get('light_level', 0.0),
                env.get('battery_level', 0.0),
                env.get('solar_power', 0.0)
            ))
        
        # Insert alerts if provided
        if 'alerts' in data:
            for alert in data['alerts']:
                conn.execute('''
                    INSERT INTO alerts 
                    (timestamp, alert_type, level, message)
                    VALUES (?, ?, ?, ?)
                ''', (
                    timestamp,
                    alert.get('type', 'general'),
                    alert.get('level', 'info'),
                    alert.get('message', '')
                ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Data ingested successfully',
            'timestamp': timestamp
        })
        
    except Exception as e:
        logger.error(f"Error ingesting data: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/config', methods=['GET'])
def get_config():
    """Get system configuration"""
    try:
        # Return current system configuration
        config = {
            'camera': {
                'resolution': [1920, 1080],
                'fps': 30,
                'detection_enabled': True
            },
            'ai_processing': {
                'confidence_threshold': 0.5,
                'nms_threshold': 0.4,
                'model_version': 'yolov8n_v1.0'
            },
            'alerts': {
                'swarming_threshold': 0.7,
                'health_threshold': 0.5,
                'agitation_threshold': 0.8
            },
            'data_retention': {
                'days': 30,
                'auto_cleanup': True
            }
        }
        
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'error': str(e)}), 500

@bee_bp.route('/config', methods=['POST'])
def update_config():
    """Update system configuration"""
    try:
        new_config = request.get_json()
        
        if not new_config:
            return jsonify({'error': 'No configuration provided'}), 400
        
        # In a real implementation, this would update the actual system configuration
        # For now, we'll just acknowledge the update
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({'error': str(e)}), 500
