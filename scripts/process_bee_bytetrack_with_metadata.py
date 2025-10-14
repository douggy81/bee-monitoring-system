#!/usr/bin/env python3
"""
Bee Video Processing with ByteTrack and Comprehensive Metadata Export

Processes bee videos with YOLO detection + ByteTrack tracking
Exports detailed metadata for dashboard integration and analytics

Usage:
    python3 process_bee_bytetrack_with_metadata.py input.mp4 output.mp4 --backend cpu
"""

import argparse
import cv2
import numpy as np
import sys
import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ByteTrack imports
try:
    from tracking.byte_tracker import BYTETracker, STrack
    BYTETRACK_AVAILABLE = True
    
    # Simple wrapper to adapt numpy detections to ultralytics format
    class DetectionResults:
        """Wrapper to make numpy detections compatible with ultralytics ByteTrack"""
        def __init__(self, detections):
            # detections: [[x1, y1, x2, y2, score], ...]
            self.data = np.array(detections) if len(detections) > 0 else np.empty((0, 5))
            
        @property
        def conf(self):
            """Return confidence scores"""
            return self.data[:, 4] if len(self.data) > 0 else np.array([])
        
        @property
        def xyxy(self):
            """Return bounding boxes in x1y1x2y2 format"""
            return self.data[:, :4] if len(self.data) > 0 else np.empty((0, 4))
        
        @property
        def xywh(self):
            """Return bounding boxes in xywh format (center_x, center_y, width, height)"""
            if len(self.data) == 0:
                return np.empty((0, 4))
            xyxy = self.data[:, :4]
            xywh = np.zeros_like(xyxy)
            xywh[:, 0] = (xyxy[:, 0] + xyxy[:, 2]) / 2  # center_x
            xywh[:, 1] = (xyxy[:, 1] + xyxy[:, 3]) / 2  # center_y
            xywh[:, 2] = xyxy[:, 2] - xyxy[:, 0]  # width
            xywh[:, 3] = xyxy[:, 3] - xyxy[:, 1]  # height
            return xywh
        
        @property
        def cls(self):
            """Return class IDs (all zeros for single-class 'bee')"""
            return np.zeros(len(self.data), dtype=int) if len(self.data) > 0 else np.array([])
        
        def __getitem__(self, index):
            """Allow indexing like results[mask]"""
            return DetectionResults(self.data[index])
        
        def __len__(self):
            return len(self.data)
            
except ImportError:
    print("⚠️  ByteTrack not available, using simple tracking")
    BYTETRACK_AVAILABLE = False


class TrackingMetadata:
    """Collect and manage tracking metadata"""
    
    def __init__(self):
        self.start_time = time.time()
        self.frame_data = []
        self.track_history = defaultdict(list)  # track_id -> list of (frame, bbox, conf)
        self.track_first_seen = {}  # track_id -> frame number
        self.track_last_seen = {}   # track_id -> frame number
        self.total_detections = 0
        self.frame_count = 0
        
    def add_frame(self, frame_num: int, timestamp: float, detections: List[Dict]):
        """Add frame data"""
        bee_count = len(detections)
        active_tracks = [d['track_id'] for d in detections if 'track_id' in d]
        
        # Track individual bees
        for det in detections:
            self.total_detections += 1
            if 'track_id' in det:
                track_id = det['track_id']
                self.track_history[track_id].append({
                    'frame': frame_num,
                    'bbox': det['bbox'],
                    'confidence': det['confidence']
                })
                
                if track_id not in self.track_first_seen:
                    self.track_first_seen[track_id] = frame_num
                self.track_last_seen[track_id] = frame_num
        
        # Determine new/lost tracks
        prev_tracks = set(self.frame_data[-1]['active_tracks']) if self.frame_data else set()
        current_tracks = set(active_tracks)
        new_tracks = list(current_tracks - prev_tracks)
        lost_tracks = list(prev_tracks - current_tracks)
        
        self.frame_data.append({
            'frame': frame_num,
            'timestamp': round(timestamp, 3),
            'bee_count': bee_count,
            'active_tracks': active_tracks,
            'new_tracks': new_tracks,
            'lost_tracks': lost_tracks
        })
        
        self.frame_count = frame_num + 1
    
    def calculate_track_metrics(self):
        """Calculate track-level metrics"""
        metrics = {
            'unique_tracks': len(self.track_history),
            'avg_track_length_frames': 0,
            'longest_track_frames': 0,
            'shortest_track_frames': 999999,
            'tracks_entering': 0,
            'tracks_exiting': 0,
            'complete_tracks': 0,  # Tracks that entered and exited
        }
        
        if not self.track_history:
            return metrics
        
        track_lengths = []
        for track_id, history in self.track_history.items():
            length = len(history)
            track_lengths.append(length)
            
            first_frame = self.track_first_seen[track_id]
            last_frame = self.track_last_seen[track_id]
            
            # Track entered if first seen after frame 0
            if first_frame > 0:
                metrics['tracks_entering'] += 1
            
            # Track exited if last seen before final frame
            if last_frame < self.frame_count - 1:
                metrics['tracks_exiting'] += 1
            
            # Complete track if both entered and exited
            if first_frame > 0 and last_frame < self.frame_count - 1:
                metrics['complete_tracks'] += 1
        
        if track_lengths:
            metrics['avg_track_length_frames'] = round(np.mean(track_lengths), 2)
            metrics['longest_track_frames'] = max(track_lengths)
            metrics['shortest_track_frames'] = min(track_lengths)
        
        return metrics
    
    def calculate_speed_metrics(self, fps: float):
        """Calculate bee movement speed metrics"""
        speeds = []
        
        for track_id, history in self.track_history.items():
            if len(history) < 2:
                continue
            
            # Calculate speed between consecutive frames
            for i in range(1, len(history)):
                prev = history[i-1]
                curr = history[i]
                
                # Center points
                prev_center = self._bbox_center(prev['bbox'])
                curr_center = self._bbox_center(curr['bbox'])
                
                # Distance in pixels
                distance = np.sqrt(
                    (curr_center[0] - prev_center[0])**2 +
                    (curr_center[1] - prev_center[1])**2
                )
                
                # Frames between observations
                frame_diff = curr['frame'] - prev['frame']
                
                # Speed in pixels per second
                speed = (distance / frame_diff) * fps
                speeds.append(speed)
        
        if speeds:
            return {
                'avg_speed_pixels_per_sec': round(np.mean(speeds), 2),
                'max_speed_pixels_per_sec': round(np.max(speeds), 2),
                'median_speed_pixels_per_sec': round(np.median(speeds), 2),
                'speed_variance': round(np.var(speeds), 2)
            }
        else:
            return {
                'avg_speed_pixels_per_sec': 0,
                'max_speed_pixels_per_sec': 0,
                'median_speed_pixels_per_sec': 0,
                'speed_variance': 0
            }
    
    def calculate_traffic_metrics(self, fps: float, frame_height: int):
        """Calculate traffic analysis metrics (entrance/exit)"""
        # Assume entrance is bottom 30% of frame
        entrance_threshold = frame_height * 0.7
        
        entrance_count = 0
        exit_count = 0
        
        for track_id, history in self.track_history.items():
            if not history:
                continue
            
            first_frame = history[0]
            last_frame = history[-1]
            
            first_y = self._bbox_center(first_frame['bbox'])[1]
            last_y = self._bbox_center(last_frame['bbox'])[1]
            
            # Entering: first position in entrance zone
            if first_y > entrance_threshold:
                entrance_count += 1
            
            # Exiting: last position in entrance zone
            if last_y > entrance_threshold:
                exit_count += 1
        
        duration_minutes = self.frame_count / fps / 60.0
        
        return {
            'entrance_count': entrance_count,
            'exit_count': exit_count,
            'entrance_rate_per_min': round(entrance_count / duration_minutes, 2) if duration_minutes > 0 else 0,
            'exit_rate_per_min': round(exit_count / duration_minutes, 2) if duration_minutes > 0 else 0,
            'net_traffic': entrance_count - exit_count,
            'traffic_balance': round(min(entrance_count, exit_count) / max(entrance_count, exit_count, 1), 2)
        }
    
    def calculate_clustering_index(self, frame_width: int, frame_height: int):
        """Calculate spatial clustering of bees"""
        # Sample positions from all tracks
        positions = []
        for track_id, history in self.track_history.items():
            if history:
                # Use middle observation
                mid_idx = len(history) // 2
                center = self._bbox_center(history[mid_idx]['bbox'])
                positions.append(center)
        
        if len(positions) < 2:
            return 0.0
        
        # Calculate average distance to nearest neighbor
        positions = np.array(positions)
        distances = []
        
        for i, pos in enumerate(positions):
            other_pos = np.delete(positions, i, axis=0)
            dists = np.sqrt(np.sum((other_pos - pos)**2, axis=1))
            if len(dists) > 0:
                distances.append(np.min(dists))
        
        avg_distance = np.mean(distances) if distances else 0
        
        # Normalize by frame diagonal
        frame_diagonal = np.sqrt(frame_width**2 + frame_height**2)
        clustering_index = 1.0 - min(avg_distance / (frame_diagonal / 4), 1.0)
        
        return round(clustering_index, 3)
    
    def calculate_dwell_time(self, fps: float):
        """Calculate average dwell time in frame"""
        dwell_times = []
        
        for track_id, history in self.track_history.items():
            track_length_frames = len(history)
            dwell_time_sec = track_length_frames / fps
            dwell_times.append(dwell_time_sec)
        
        if dwell_times:
            return {
                'avg_dwell_time_sec': round(np.mean(dwell_times), 2),
                'max_dwell_time_sec': round(np.max(dwell_times), 2),
                'median_dwell_time_sec': round(np.median(dwell_times), 2)
            }
        else:
            return {
                'avg_dwell_time_sec': 0,
                'max_dwell_time_sec': 0,
                'median_dwell_time_sec': 0
            }
    
    def calculate_health_score(self, traffic_metrics: Dict, speed_metrics: Dict, 
                               track_metrics: Dict, clustering_index: float, dwell_metrics: Dict):
        """Calculate overall health score (0-100)"""
        
        # 1. Traffic Balance Score (0-100)
        # Healthy = balanced entrance/exit (ratio close to 1.0)
        traffic_balance_score = traffic_metrics['traffic_balance'] * 100
        
        # 2. Movement Quality Score (0-100)
        # Healthy = moderate speed, low variance
        avg_speed = speed_metrics['avg_speed_pixels_per_sec']
        speed_var = speed_metrics['speed_variance']
        
        # Ideal speed around 10-20 px/sec, variance < 50
        speed_score = 100 if 10 <= avg_speed <= 20 else max(0, 100 - abs(avg_speed - 15) * 3)
        variance_score = max(0, 100 - speed_var)
        movement_quality_score = (speed_score + variance_score) / 2
        
        # 3. Population Stability Score (0-100)
        # Healthy = good number of tracks, reasonable track lengths
        unique_tracks = track_metrics['unique_tracks']
        avg_track_length = track_metrics['avg_track_length_frames']
        
        # Ideal: 50+ unique tracks, avg length 30-100 frames
        track_count_score = min(unique_tracks * 2, 100)
        track_length_score = 100 if 30 <= avg_track_length <= 100 else max(0, 100 - abs(avg_track_length - 65))
        population_stability_score = (track_count_score + track_length_score) / 2
        
        # 4. Spatial Organization Score (0-100)
        # Healthy = moderate clustering (not too dispersed, not too clustered)
        # Ideal clustering: 0.3-0.6
        if 0.3 <= clustering_index <= 0.6:
            spatial_score = 100
        else:
            spatial_score = max(0, 100 - abs(clustering_index - 0.45) * 200)
        
        # Overall health score (weighted average)
        health_score = (
            traffic_balance_score * 0.25 +
            movement_quality_score * 0.25 +
            population_stability_score * 0.30 +
            spatial_score * 0.20
        )
        
        # Determine status
        if health_score >= 80:
            status = "EXCELLENT"
        elif health_score >= 60:
            status = "GOOD"
        elif health_score >= 40:
            status = "WARNING"
        else:
            status = "CRITICAL"
        
        return {
            'overall_score': round(health_score, 1),
            'status': status,
            'component_scores': {
                'traffic_balance': round(traffic_balance_score, 1),
                'movement_quality': round(movement_quality_score, 1),
                'population_stability': round(population_stability_score, 1),
                'spatial_organization': round(spatial_score, 1)
            }
        }
    
    @staticmethod
    def _bbox_center(bbox):
        """Get center point of bbox [x, y, w, h]"""
        return (bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2)
    
    def export_metadata(self, output_path: str, video_info: Dict):
        """Export complete metadata to JSON"""
        processing_time = time.time() - self.start_time
        
        # Calculate all metrics
        bee_counts = [f['bee_count'] for f in self.frame_data]
        track_metrics = self.calculate_track_metrics()
        speed_metrics = self.calculate_speed_metrics(video_info['fps'])
        traffic_metrics = self.calculate_traffic_metrics(video_info['fps'], video_info['height'])
        clustering_index = self.calculate_clustering_index(video_info['width'], video_info['height'])
        dwell_metrics = self.calculate_dwell_time(video_info['fps'])
        health_score = self.calculate_health_score(traffic_metrics, speed_metrics, track_metrics, clustering_index, dwell_metrics)
        
        metadata = {
            'video_metadata': {
                'filename': video_info['filename'],
                'output_filename': video_info['output_filename'],
                'duration_seconds': round(video_info['duration'], 2),
                'fps': video_info['fps'],
                'total_frames': self.frame_count,
                'resolution': f"{video_info['width']}x{video_info['height']}",
                'processing_time_seconds': round(processing_time, 2),
                'processing_fps': round(self.frame_count / processing_time, 2),
                'model': video_info['model'],
                'backend': video_info['backend'],
                'tracker': 'ByteTrack',
                'processed_at': datetime.now().isoformat()
            },
            'detection_summary': {
                'total_detections': self.total_detections,
                'unique_tracks': track_metrics['unique_tracks'],
                'avg_bees_per_frame': round(np.mean(bee_counts), 2) if bee_counts else 0,
                'max_bees_single_frame': max(bee_counts) if bee_counts else 0,
                'min_bees_single_frame': min(bee_counts) if bee_counts else 0,
                'median_bees_per_frame': int(np.median(bee_counts)) if bee_counts else 0
            },
            'tracking_metrics': {
                **track_metrics,
                **speed_metrics
            },
            'health_metrics': {
                'traffic_analysis': traffic_metrics,
                'movement_patterns': {
                    **speed_metrics,
                    'clustering_index': clustering_index,
                    **dwell_metrics
                },
                'overall_health': health_score
            },
            'per_frame_data': self.frame_data
        }
        
        # Write full metadata
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Write summary (without per-frame data for easier viewing)
        summary_path = output_path.replace('.json', '_summary.json')
        summary = {k: v for k, v in metadata.items() if k != 'per_frame_data'}
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return metadata, summary


def process_bee_video_with_bytetrack(
    input_path: str,
    output_path: str,
    metadata_path: str,
    backend_type: str = 'cpu',
    conf: float = 0.25,
    fps_override: int = None
):
    """
    Process bee video with ByteTrack and export metadata
    """
    
    # Import backend
    if backend_type == 'hailo':
        from ai.hailo_backend import HailoBackend as Backend
        print("Using Hailo backend (hardware accelerated)")
    else:
        from ai.cpu_backend import CpuBackend as Backend
        print("Using CPU backend (ONNX Runtime)")
    
    # Initialize backend
    print("Initializing detection backend...")
    backend = Backend()
    if not backend.initialize():
        raise RuntimeError("Failed to initialize backend")
    
    backend.conf = conf
    model_info = backend.model_path if hasattr(backend, 'model_path') else backend.hef_path
    
    print(f"✓ Backend initialized")
    print(f"  Model: {model_info}")
    print(f"  Confidence threshold: {backend.conf}")
    print()
    
    # Initialize ByteTrack
    if BYTETRACK_AVAILABLE:
        tracker_args = argparse.Namespace(
            track_thresh=0.5,
            track_high_thresh=0.6,    # High confidence threshold
            track_low_thresh=0.1,     # Low confidence threshold
            new_track_thresh=0.6,     # Threshold for new track creation  
            track_buffer=30,
            match_thresh=0.8,
            fuse_score=True,          # Fuse detection and tracking scores
            mot20=False
        )
        tracker = BYTETracker(tracker_args, frame_rate=fps_override if fps_override else 30)
        print("✓ ByteTrack initialized")
    else:
        tracker = None
        print("⚠️  ByteTrack not available")
    
    # Open video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")
    
    # Video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = fps_override if fps_override else cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    video_info = {
        'filename': Path(input_path).name,
        'output_filename': Path(output_path).name,
        'width': width,
        'height': height,
        'fps': fps,
        'duration': duration,
        'total_frames': total_frames,
        'model': 'YOLO11m',
        'backend': backend_type
    }
    
    print(f"Input video: {input_path}")
    print(f"  Resolution: {width}×{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total frames: {total_frames}")
    print(f"  Duration: {duration:.2f} seconds")
    print()
    
    # Output video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Metadata collector
    metadata = TrackingMetadata()
    
    # Store last calculated metrics for overlay (to prevent flickering)
    last_track_metrics = None
    last_speed_metrics = None
    last_traffic_metrics = None
    last_clustering = 0.0
    last_dwell = None
    last_health = None
    
    # Process frames
    print("Processing frames with ByteTrack...")
    print("="*70)
    
    frame_num = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp = frame_num / fps
        
        # Detection
        boxes, scores = backend.infer(frame)
        
        # Convert to tracking format
        detections_for_tracking = []
        if boxes and len(boxes) > 0:
            for box, score in zip(boxes, scores):
                # box is (x, y, w, h), convert to (x1, y1, x2, y2, score)
                x, y, w, h = box
                detections_for_tracking.append([x, y, x + w, y + h, score])
        
        # Tracking
        if tracker and detections_for_tracking:
            # Wrap detections in Results-like object for ByteTrack
            results = DetectionResults(detections_for_tracking)
            tracks = tracker.update(results, frame)
        else:
            tracks = []
        
        # Collect metadata
        frame_detections = []
        if len(tracks) > 0:
            # Use ByteTrack tracks
            # Format: [x1, y1, x2, y2, track_id, score, cls, idx]
            for track in tracks:
                x1, y1, x2, y2, track_id, score, cls_id, idx = track
                # Convert to xywh format
                x, y, w, h = x1, y1, x2 - x1, y2 - y1
                
                frame_detections.append({
                    'track_id': int(track_id),
                    'bbox': [float(x), float(y), float(w), float(h)],
                    'confidence': float(score)
                })
        else:
            # Fallback: Use raw detections without tracking
            for i, (box, score) in enumerate(zip(boxes, scores)):
                x, y, w, h = box
                frame_detections.append({
                    'track_id': i,  # Use frame-local ID
                    'bbox': [float(x), float(y), float(w), float(h)],
                    'confidence': float(score)
                })
        
        metadata.add_frame(frame_num, timestamp, frame_detections)
        
        # Draw on frame
        for det in frame_detections:
            bbox = det['bbox']
            track_id = det['track_id']
            conf = det['confidence']
            
            x, y, w, h = map(int, bbox)
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw track ID and confidence
            label = f"ID:{track_id} {conf:.2f}"
            cv2.putText(frame, label, (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Calculate health metrics every 30 frames (for performance)
        if frame_num % 30 == 0 and frame_num > 0:
            last_track_metrics = metadata.calculate_track_metrics()
            last_speed_metrics = metadata.calculate_speed_metrics(fps)
            last_traffic_metrics = metadata.calculate_traffic_metrics(fps, height)
            last_clustering = metadata.calculate_clustering_index(width, height)
            last_dwell = metadata.calculate_dwell_time(fps)
            last_health = metadata.calculate_health_score(
                last_traffic_metrics, last_speed_metrics,
                last_track_metrics, last_clustering, last_dwell
            )
        
        # Draw health metrics overlay on EVERY frame (using last calculated values)
        if last_health is not None:
            # Draw overlay panel (BOTTOM-LEFT)
            overlay = frame.copy()
            panel_height = 200
            y_start = height - panel_height - 10  # Bottom-left positioning
            cv2.rectangle(overlay, (10, y_start), (450, y_start + panel_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            # Title
            y_offset = y_start + 25
            cv2.putText(frame, f"Frame: {frame_num} | Time: {timestamp:.1f}s",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            y_offset += 30
            cv2.putText(frame, "Tracking Stats:",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            y_offset += 22
            
            cv2.putText(frame, f"  Active: {len(frame_detections)} tracks",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
            cv2.putText(frame, f"  Total IDs: {last_track_metrics['unique_tracks']}",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
            cv2.putText(frame, f"  Avg Speed: {last_speed_metrics['avg_speed_pixels_per_sec']:.1f} px/s",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
            
            # Health score
            cv2.putText(frame, f"Health Score: {last_health['overall_score']:.1f}",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            
            # Status color
            status_color = {
                "EXCELLENT": (0, 255, 0),
                "GOOD": (0, 255, 255),
                "WARNING": (0, 165, 255),
                "CRITICAL": (0, 0, 255)
            }.get(last_health['status'], (255, 255, 255))
            
            cv2.putText(frame, f"({last_health['status']})",
                       (210, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
            y_offset += 20
            
            # Component scores
            comp = last_health['component_scores']
            cv2.putText(frame, f"  Traffic: {comp['traffic_balance']:.0f}%",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            y_offset += 18
            cv2.putText(frame, f"  Movement: {comp['movement_quality']:.0f}%",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            y_offset += 18
            cv2.putText(frame, f"  Population: {comp['population_stability']:.0f}%",
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Status display on bottom
        if len(frame_detections) > 0:
            cv2.putText(frame, f"Frame: {frame_num} | Bees: {len(frame_detections)}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        out.write(frame)
        
        # Progress
        if (frame_num + 1) % 30 == 0:
            elapsed = time.time() - start_time
            fps_processing = (frame_num + 1) / elapsed
            eta = (total_frames - frame_num - 1) / fps_processing if fps_processing > 0 else 0
            progress = (frame_num + 1) / total_frames * 100
            
            print(f"Frame {frame_num + 1:4d}/{total_frames} ({progress:5.1f}%) | "
                  f"Bees:{len(frame_detections):3d} | Tracks:{len(set(d['track_id'] for d in frame_detections)):3d} | "
                  f"FPS:{fps_processing:5.1f} | ETA:{eta/60:.1f}min")
        
        frame_num += 1
    
    cap.release()
    out.release()
    
    print("="*70)
    print()
    
    # Export metadata
    print("📊 Exporting metadata...")
    full_metadata, summary = metadata.export_metadata(metadata_path, video_info)
    
    print("="*70)
    print("✅ PROCESSING COMPLETE!")
    print("="*70)
    print()
    print(f"📹 Output video: {output_path}")
    print(f"   Size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print()
    print(f"📊 Metadata: {metadata_path}")
    print(f"📊 Summary: {metadata_path.replace('.json', '_summary.json')}")
    print()
    print("📈 Statistics:")
    print(f"   Total frames: {full_metadata['video_metadata']['total_frames']}")
    print(f"   Processing time: {full_metadata['video_metadata']['processing_time_seconds']:.1f}s")
    print(f"   Processing FPS: {full_metadata['video_metadata']['processing_fps']:.1f}")
    print(f"   Unique tracks: {full_metadata['detection_summary']['unique_tracks']}")
    print(f"   Avg bees/frame: {full_metadata['detection_summary']['avg_bees_per_frame']:.1f}")
    print(f"   Max bees: {full_metadata['detection_summary']['max_bees_single_frame']}")
    print()
    print("🚦 Traffic Analysis:")
    traffic = full_metadata['health_metrics']['traffic_analysis']
    print(f"   Entrance rate: {traffic['entrance_rate_per_min']:.1f}/min")
    print(f"   Exit rate: {traffic['exit_rate_per_min']:.1f}/min")
    print(f"   Net traffic: {traffic['net_traffic']:+d}")
    print(f"   Traffic balance: {traffic['traffic_balance']:.2f}")
    print()
    print("🏃 Movement Patterns:")
    movement = full_metadata['health_metrics']['movement_patterns']
    print(f"   Avg speed: {movement['avg_speed_pixels_per_sec']:.1f} px/s")
    print(f"   Speed variance: {movement['speed_variance']:.1f}")
    print(f"   Clustering index: {movement['clustering_index']:.3f}")
    print(f"   Avg dwell time: {movement['avg_dwell_time_sec']:.1f}s")
    print()
    print("💚 Overall Health:")
    health = full_metadata['health_metrics']['overall_health']
    status_icon = {"EXCELLENT": "🟢", "GOOD": "🟡", "WARNING": "🟠", "CRITICAL": "🔴"}.get(health['status'], "⚪")
    print(f"   Score: {health['overall_score']:.1f}/100 {status_icon} ({health['status']})")
    comp = health['component_scores']
    print(f"   └─ Traffic: {comp['traffic_balance']:.0f}%")
    print(f"   └─ Movement: {comp['movement_quality']:.0f}%")
    print(f"   └─ Population: {comp['population_stability']:.0f}%")
    print(f"   └─ Spatial: {comp['spatial_organization']:.0f}%")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process bee video with ByteTrack and metadata export")
    parser.add_argument("input", help="Input video path")
    parser.add_argument("output", help="Output video path")
    parser.add_argument("--metadata", "-m", help="Metadata output path (default: same as output with .json)")
    parser.add_argument("--backend", choices=['hailo', 'cpu'], default='cpu', help="Detection backend")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--fps", type=int, help="Override output FPS")
    
    args = parser.parse_args()
    
    # Default metadata path
    if not args.metadata:
        args.metadata = args.output.replace('.mp4', '_metadata.json')
    
    process_bee_video_with_bytetrack(
        args.input,
        args.output,
        args.metadata,
        args.backend,
        args.conf,
        args.fps
    )
