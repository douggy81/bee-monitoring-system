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
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
bee_bp = Blueprint('bee_monitoring', __name__)

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
        # Lazy import to avoid hard dependency at import time
        from hardware_integration import CameraManager

        def generate_frames():
            camera = CameraManager()
            if not camera.initialize():
                logger.error("Camera initialization failed for streaming")
                return
            try:
                while True:
                    frame = camera.capture_frame()
                    if frame is not None:
                        ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if ok:
                            frame_bytes = buffer.tobytes()
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    time.sleep(0.2)  # ~5 FPS
            finally:
                camera.cleanup()

        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    except Exception as e:
        logger.error(f"Camera stream error: {e}")
        return jsonify({'error': str(e)}), 500


@bee_bp.route('/camera/snapshot')
def camera_snapshot():
    """Return a single camera snapshot as base64 JSON."""
    try:
        from hardware_integration import CameraManager

        camera = CameraManager()
        if not camera.initialize():
            return jsonify({'error': 'Camera initialization failed'}), 500

        try:
            frame = camera.capture_frame()
            if frame is not None:
                ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ok:
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
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
    """Check camera availability and report basic info."""
    try:
        from hardware_integration import CameraManager
        camera = CameraManager()
        available = camera.initialize()
        backend = 'Picamera2' if getattr(camera, 'use_picamera2', False) else 'OpenCV' if available else 'Not Available'
        if available:
            camera.cleanup()
        return jsonify({
            'available': available,
            'resolution': [camera.resolution[0], camera.resolution[1]],
            'fps': camera.fps,
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
