"""
Stream Proxy for Internet Video Sources

Allows using external video streams (YouTube, RTSP, HLS) as input
for the bee monitoring system for demos and testing.
"""
import cv2
import logging
from flask import Blueprint, Response, request, jsonify
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

stream_proxy_bp = Blueprint('stream_proxy', __name__, url_prefix='/api/stream')

# Global stream capture for reuse
_stream_capture: Optional[cv2.VideoCapture] = None
_stream_url: Optional[str] = None

def get_stream_capture(url: str) -> Optional[cv2.VideoCapture]:
    """
    Get or create a VideoCapture for the given URL.
    
    Supported formats:
    - HTTP/HTTPS video streams (.mp4, .mjpg)
    - HLS streams (.m3u8)
    - RTSP streams (rtsp://)
    - YouTube URLs (requires youtube-dl/yt-dlp)
    """
    global _stream_capture, _stream_url
    
    # Reuse existing capture if same URL
    if _stream_capture is not None and _stream_url == url:
        if _stream_capture.isOpened():
            return _stream_capture
    
    # Close old capture
    if _stream_capture is not None:
        _stream_capture.release()
    
    logger.info(f"Opening stream: {url}")
    
    # Special handling for YouTube URLs
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                url = info['url']
                logger.info(f"Extracted YouTube stream URL")
        except ImportError:
            logger.warning("yt-dlp not installed, trying direct URL")
        except Exception as e:
            logger.error(f"Failed to extract YouTube URL: {e}")
            return None
    
    # Open stream
    cap = cv2.VideoCapture(url)
    
    if not cap.isOpened():
        logger.error(f"Failed to open stream: {url}")
        return None
    
    _stream_capture = cap
    _stream_url = url
    
    # Log stream info
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    logger.info(f"Stream opened: {width}x{height} @ {fps}fps")
    
    return cap

@stream_proxy_bp.route('/test', methods=['GET'])
def test_stream():
    """Test if a stream URL is accessible"""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'}), 400
    
    cap = get_stream_capture(url)
    if cap is None:
        return jsonify({
            'success': False,
            'error': 'Failed to open stream'
        }), 500
    
    # Try to read one frame
    ret, frame = cap.read()
    if not ret:
        return jsonify({
            'success': False,
            'error': 'Failed to read frame from stream'
        }), 500
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    return jsonify({
        'success': True,
        'url': url,
        'width': width,
        'height': height,
        'fps': fps,
        'frame_shape': list(frame.shape)
    })

@stream_proxy_bp.route('/frame', methods=['GET'])
def get_frame():
    """Get a single frame from the stream (JPEG)"""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'}), 400
    
    cap = get_stream_capture(url)
    if cap is None:
        return jsonify({'error': 'Failed to open stream'}), 500
    
    ret, frame = cap.read()
    if not ret:
        return jsonify({'error': 'Failed to read frame'}), 500
    
    # Encode as JPEG
    ret, buffer = cv2.imencode('.jpg', frame)
    if not ret:
        return jsonify({'error': 'Failed to encode frame'}), 500
    
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@stream_proxy_bp.route('/info', methods=['GET'])
def get_info():
    """Get information about the current stream"""
    global _stream_url, _stream_capture
    
    if _stream_capture is None or not _stream_capture.isOpened():
        return jsonify({
            'active': False,
            'url': None
        })
    
    width = int(_stream_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(_stream_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = _stream_capture.get(cv2.CAP_PROP_FPS)
    
    return jsonify({
        'active': True,
        'url': _stream_url,
        'width': width,
        'height': height,
        'fps': fps
    })

@stream_proxy_bp.route('/close', methods=['POST'])
def close_stream():
    """Close the current stream"""
    global _stream_capture, _stream_url
    
    if _stream_capture is not None:
        _stream_capture.release()
        _stream_capture = None
        _stream_url = None
        logger.info("Stream closed")
        return jsonify({'success': True, 'message': 'Stream closed'})
    
    return jsonify({'success': False, 'message': 'No stream active'})


# Preset stream URLs for convenience
PRESET_STREAMS = {
    'explore_bees': 'https://explore.org/livecams/player/honey-bees/honey-bee-landing-zone-cam',
    'test': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Test stream
}

@stream_proxy_bp.route('/presets', methods=['GET'])
def get_presets():
    """Get list of preset stream URLs"""
    return jsonify(PRESET_STREAMS)
