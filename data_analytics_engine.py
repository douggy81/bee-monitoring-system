#!/usr/bin/env python3
"""
Data Processing and Analytics Engine for Digital4.ai Bee Monitoring System

This module provides advanced data processing and analytics capabilities for bee monitoring,
optimized for the Raspberry Pi 5 with AI HAT+ (13 TOPS) and Camera Module 3.

Current Hardware:
- Raspberry Pi 5 (8GB RAM)
- AI HAT+ (13 TOPS Hailo-8L)
- Camera Module 3 (12MP)
- 256GB microSD storage

Author: Digital4.ai Development Team
Date: September 2025
"""

import numpy as np
import pandas as pd
import cv2
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
import threading
import time
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BeeActivityMetrics:
    """Comprehensive bee activity metrics"""
    timestamp: datetime
    bee_count: int
    entrance_activity: int
    exit_activity: int
    net_activity: int
    average_speed: float
    clustering_index: float
    agitation_level: float
    traffic_density: float

@dataclass
class BehaviorAnalysis:
    """Behavioral analysis results"""
    timestamp: datetime
    dominant_behavior: str
    behavior_confidence: float
    swarming_probability: float
    foraging_activity: float
    guard_bee_activity: float
    unusual_patterns: List[str]

@dataclass
class HealthAssessment:
    """Health assessment results"""
    timestamp: datetime
    overall_health_score: float
    mite_detection_score: float
    wing_condition_score: float
    size_distribution_score: float
    activity_pattern_score: float
    risk_indicators: List[str]

class DataStorage:
    """Handles local data storage and retrieval"""
    
    def __init__(self, db_path: str = "/home/ubuntu/bee_data/monitoring.db"):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
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
                    traffic_density REAL
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
                    unusual_patterns TEXT
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
                    risk_indicators TEXT
                )
            ''')
            
            # Raw detections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    detection_data TEXT,
                    frame_path TEXT
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def store_activity_metrics(self, metrics: BeeActivityMetrics):
        """Store activity metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO activity_metrics 
                (timestamp, bee_count, entrance_activity, exit_activity, net_activity,
                 average_speed, clustering_index, agitation_level, traffic_density)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.bee_count,
                metrics.entrance_activity,
                metrics.exit_activity,
                metrics.net_activity,
                metrics.average_speed,
                metrics.clustering_index,
                metrics.agitation_level,
                metrics.traffic_density
            ))
            conn.commit()
    
    def store_behavior_analysis(self, analysis: BehaviorAnalysis):
        """Store behavior analysis"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO behavior_analysis 
                (timestamp, dominant_behavior, behavior_confidence, swarming_probability,
                 foraging_activity, guard_bee_activity, unusual_patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.timestamp.isoformat(),
                analysis.dominant_behavior,
                analysis.behavior_confidence,
                analysis.swarming_probability,
                analysis.foraging_activity,
                analysis.guard_bee_activity,
                json.dumps(analysis.unusual_patterns)
            ))
            conn.commit()
    
    def store_health_assessment(self, assessment: HealthAssessment):
        """Store health assessment"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO health_assessment 
                (timestamp, overall_health_score, mite_detection_score, wing_condition_score,
                 size_distribution_score, activity_pattern_score, risk_indicators)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                assessment.timestamp.isoformat(),
                assessment.overall_health_score,
                assessment.mite_detection_score,
                assessment.wing_condition_score,
                assessment.size_distribution_score,
                assessment.activity_pattern_score,
                json.dumps(assessment.risk_indicators)
            ))
            conn.commit()
    
    def get_recent_data(self, table: str, hours: int = 24) -> pd.DataFrame:
        """Get recent data from specified table"""
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            query = f"SELECT * FROM {table} WHERE timestamp > ? ORDER BY timestamp DESC"
            df = pd.read_sql_query(query, conn, params=(cutoff_time,))
            return df

class ActivityAnalyzer:
    """Analyzes bee activity patterns"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.detection_history = deque(maxlen=window_size)
        self.entrance_line_y = None  # Will be set based on hive entrance position
        
    def set_entrance_line(self, y_position: int):
        """Set the entrance line for traffic analysis"""
        self.entrance_line_y = y_position
        logger.info(f"Entrance line set at y={y_position}")
    
    def analyze_frame_activity(self, detections: List[Dict]) -> BeeActivityMetrics:
        """Analyze activity in a single frame"""
        timestamp = datetime.now()
        
        if not detections:
            return BeeActivityMetrics(
                timestamp=timestamp,
                bee_count=0,
                entrance_activity=0,
                exit_activity=0,
                net_activity=0,
                average_speed=0.0,
                clustering_index=0.0,
                agitation_level=0.0,
                traffic_density=0.0
            )
        
        # Basic metrics
        bee_count = len(detections)
        
        # Calculate traffic analysis if entrance line is set
        entrance_activity, exit_activity = self._analyze_traffic(detections)
        net_activity = entrance_activity - exit_activity
        
        # Calculate movement metrics
        average_speed = self._calculate_average_speed(detections)
        
        # Calculate clustering index
        clustering_index = self._calculate_clustering_index(detections)
        
        # Calculate agitation level
        agitation_level = self._calculate_agitation_level(detections)
        
        # Calculate traffic density
        traffic_density = self._calculate_traffic_density(detections)
        
        metrics = BeeActivityMetrics(
            timestamp=timestamp,
            bee_count=bee_count,
            entrance_activity=entrance_activity,
            exit_activity=exit_activity,
            net_activity=net_activity,
            average_speed=average_speed,
            clustering_index=clustering_index,
            agitation_level=agitation_level,
            traffic_density=traffic_density
        )
        
        self.detection_history.append(metrics)
        return metrics
    
    def _analyze_traffic(self, detections: List[Dict]) -> Tuple[int, int]:
        """Analyze entrance and exit traffic"""
        if self.entrance_line_y is None:
            return 0, 0
        
        entrance_count = 0
        exit_count = 0
        
        for detection in detections:
            bbox = detection.get('bbox', [0, 0, 0, 0])
            center_y = bbox[1] + bbox[3] / 2
            
            # Simple heuristic: bees above entrance line are entering, below are exiting
            if center_y < self.entrance_line_y:
                entrance_count += 1
            else:
                exit_count += 1
        
        return entrance_count, exit_count
    
    def _calculate_average_speed(self, detections: List[Dict]) -> float:
        """Calculate average movement speed"""
        if len(self.detection_history) < 2:
            return 0.0
        
        # Simplified speed calculation based on position changes
        # In a real implementation, this would use tracking data
        speeds = []
        for detection in detections:
            # Simulated speed based on detection confidence and position
            speed = detection.get('confidence', 0.5) * 10.0
            speeds.append(speed)
        
        return np.mean(speeds) if speeds else 0.0
    
    def _calculate_clustering_index(self, detections: List[Dict]) -> float:
        """Calculate how clustered the bees are"""
        if len(detections) < 2:
            return 0.0
        
        centers = []
        for detection in detections:
            bbox = detection.get('bbox', [0, 0, 0, 0])
            center_x = bbox[0] + bbox[2] / 2
            center_y = bbox[1] + bbox[3] / 2
            centers.append([center_x, center_y])
        
        centers = np.array(centers)
        
        # Calculate average distance between all pairs
        distances = []
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                dist = np.linalg.norm(centers[i] - centers[j])
                distances.append(dist)
        
        avg_distance = np.mean(distances) if distances else 0.0
        
        # Normalize to 0-1 scale (lower distance = higher clustering)
        max_possible_distance = 1000  # Adjust based on frame size
        clustering_index = 1.0 - min(avg_distance / max_possible_distance, 1.0)
        
        return clustering_index
    
    def _calculate_agitation_level(self, detections: List[Dict]) -> float:
        """Calculate agitation level based on movement patterns"""
        if len(self.detection_history) < 5:
            return 0.0
        
        # Calculate variance in bee count over recent history
        recent_counts = [h.bee_count for h in list(self.detection_history)[-5:]]
        count_variance = np.var(recent_counts)
        
        # Calculate variance in clustering
        recent_clustering = [h.clustering_index for h in list(self.detection_history)[-5:]]
        clustering_variance = np.var(recent_clustering)
        
        # Combine metrics to estimate agitation
        agitation = (count_variance / 100.0) + (clustering_variance * 2.0)
        return min(agitation, 1.0)
    
    def _calculate_traffic_density(self, detections: List[Dict]) -> float:
        """Calculate traffic density at entrance"""
        if not detections or self.entrance_line_y is None:
            return 0.0
        
        # Count bees near the entrance line
        entrance_zone_height = 50  # pixels
        bees_near_entrance = 0
        
        for detection in detections:
            bbox = detection.get('bbox', [0, 0, 0, 0])
            center_y = bbox[1] + bbox[3] / 2
            
            if abs(center_y - self.entrance_line_y) < entrance_zone_height:
                bees_near_entrance += 1
        
        # Normalize by total bee count
        density = bees_near_entrance / len(detections) if detections else 0.0
        return density

class BehaviorAnalyzer:
    """Analyzes bee behavior patterns"""
    
    def __init__(self):
        self.behavior_history = deque(maxlen=50)
        self.behavior_patterns = {
            'normal': {'speed_range': (0.2, 0.8), 'clustering_range': (0.3, 0.7)},
            'foraging': {'speed_range': (0.6, 1.0), 'clustering_range': (0.1, 0.4)},
            'guarding': {'speed_range': (0.1, 0.5), 'clustering_range': (0.6, 0.9)},
            'swarming_prep': {'speed_range': (0.4, 0.9), 'clustering_range': (0.7, 1.0)},
            'agitated': {'speed_range': (0.7, 1.0), 'clustering_range': (0.2, 0.8)}
        }
    
    def analyze_behavior(self, activity_metrics: BeeActivityMetrics) -> BehaviorAnalysis:
        """Analyze behavior based on activity metrics"""
        timestamp = datetime.now()
        
        # Determine dominant behavior
        dominant_behavior, confidence = self._classify_behavior(activity_metrics)
        
        # Calculate swarming probability
        swarming_probability = self._calculate_swarming_probability(activity_metrics)
        
        # Analyze specific activities
        foraging_activity = self._analyze_foraging_activity(activity_metrics)
        guard_bee_activity = self._analyze_guard_activity(activity_metrics)
        
        # Detect unusual patterns
        unusual_patterns = self._detect_unusual_patterns(activity_metrics)
        
        analysis = BehaviorAnalysis(
            timestamp=timestamp,
            dominant_behavior=dominant_behavior,
            behavior_confidence=confidence,
            swarming_probability=swarming_probability,
            foraging_activity=foraging_activity,
            guard_bee_activity=guard_bee_activity,
            unusual_patterns=unusual_patterns
        )
        
        self.behavior_history.append(analysis)
        return analysis
    
    def _classify_behavior(self, metrics: BeeActivityMetrics) -> Tuple[str, float]:
        """Classify the dominant behavior"""
        speed_norm = min(metrics.average_speed / 20.0, 1.0)  # Normalize speed
        clustering = metrics.clustering_index
        
        best_match = 'normal'
        best_score = 0.0
        
        for behavior, patterns in self.behavior_patterns.items():
            speed_match = self._in_range(speed_norm, patterns['speed_range'])
            clustering_match = self._in_range(clustering, patterns['clustering_range'])
            
            score = (speed_match + clustering_match) / 2.0
            if score > best_score:
                best_score = score
                best_match = behavior
        
        return best_match, best_score
    
    def _in_range(self, value: float, range_tuple: Tuple[float, float]) -> float:
        """Calculate how well a value fits in a range (0-1)"""
        min_val, max_val = range_tuple
        if min_val <= value <= max_val:
            return 1.0
        elif value < min_val:
            return max(0.0, 1.0 - (min_val - value))
        else:
            return max(0.0, 1.0 - (value - max_val))
    
    def _calculate_swarming_probability(self, metrics: BeeActivityMetrics) -> float:
        """Calculate probability of swarming behavior"""
        factors = []
        
        # High bee count increases swarming probability
        if metrics.bee_count > 30:
            factors.append(0.3)
        
        # High clustering increases probability
        if metrics.clustering_index > 0.7:
            factors.append(0.4)
        
        # High agitation increases probability
        if metrics.agitation_level > 0.6:
            factors.append(0.3)
        
        # Net exit activity (more bees leaving than entering)
        if metrics.net_activity < -5:
            factors.append(0.2)
        
        return min(sum(factors), 1.0)
    
    def _analyze_foraging_activity(self, metrics: BeeActivityMetrics) -> float:
        """Analyze foraging activity level"""
        # High entrance activity and moderate speed suggest foraging
        entrance_factor = min(metrics.entrance_activity / 20.0, 1.0)
        speed_factor = metrics.average_speed / 20.0
        
        # Low clustering suggests individual foraging behavior
        clustering_factor = 1.0 - metrics.clustering_index
        
        foraging_score = (entrance_factor + speed_factor + clustering_factor) / 3.0
        return min(foraging_score, 1.0)
    
    def _analyze_guard_activity(self, metrics: BeeActivityMetrics) -> float:
        """Analyze guard bee activity"""
        # Guard bees typically show high traffic density but lower overall movement
        density_factor = metrics.traffic_density
        
        # Moderate clustering around entrance
        clustering_factor = metrics.clustering_index if 0.4 < metrics.clustering_index < 0.8 else 0.0
        
        # Lower average speed
        speed_factor = 1.0 - min(metrics.average_speed / 20.0, 1.0)
        
        guard_score = (density_factor + clustering_factor + speed_factor) / 3.0
        return min(guard_score, 1.0)
    
    def _detect_unusual_patterns(self, metrics: BeeActivityMetrics) -> List[str]:
        """Detect unusual behavioral patterns"""
        patterns = []
        
        if metrics.bee_count > 50:
            patterns.append("unusually_high_activity")
        
        if metrics.bee_count < 2:
            patterns.append("unusually_low_activity")
        
        if metrics.agitation_level > 0.8:
            patterns.append("high_agitation")
        
        if metrics.net_activity < -10:
            patterns.append("mass_exodus")
        
        if metrics.clustering_index > 0.9:
            patterns.append("extreme_clustering")
        
        return patterns

class HealthAnalyzer:
    """Analyzes bee colony health"""
    
    def __init__(self):
        self.health_history = deque(maxlen=100)
        self.baseline_metrics = None
    
    def analyze_health(self, activity_metrics: BeeActivityMetrics, 
                      behavior_analysis: BehaviorAnalysis) -> HealthAssessment:
        """Perform comprehensive health analysis"""
        timestamp = datetime.now()
        
        # Calculate individual health scores
        activity_score = self._assess_activity_health(activity_metrics)
        behavior_score = self._assess_behavior_health(behavior_analysis)
        pattern_score = self._assess_pattern_health(activity_metrics)
        
        # Overall health score (weighted average)
        overall_score = (
            activity_score * 0.4 +
            behavior_score * 0.3 +
            pattern_score * 0.3
        )
        
        # Simulated specific health indicators (would be from AI models in real implementation)
        mite_score = max(0.0, 1.0 - behavior_analysis.swarming_probability)
        wing_score = min(1.0, activity_metrics.average_speed / 15.0)
        size_score = 0.8 + np.random.normal(0, 0.1)  # Placeholder
        
        # Identify risk indicators
        risk_indicators = self._identify_risks(activity_metrics, behavior_analysis)
        
        assessment = HealthAssessment(
            timestamp=timestamp,
            overall_health_score=overall_score,
            mite_detection_score=mite_score,
            wing_condition_score=wing_score,
            size_distribution_score=max(0.0, min(1.0, size_score)),
            activity_pattern_score=pattern_score,
            risk_indicators=risk_indicators
        )
        
        self.health_history.append(assessment)
        return assessment
    
    def _assess_activity_health(self, metrics: BeeActivityMetrics) -> float:
        """Assess health based on activity patterns"""
        # Healthy colonies show moderate, consistent activity
        activity_score = 1.0
        
        # Penalize extreme values
        if metrics.bee_count < 5 or metrics.bee_count > 60:
            activity_score -= 0.3
        
        if metrics.agitation_level > 0.7:
            activity_score -= 0.2
        
        if abs(metrics.net_activity) > 15:
            activity_score -= 0.2
        
        return max(0.0, activity_score)
    
    def _assess_behavior_health(self, analysis: BehaviorAnalysis) -> float:
        """Assess health based on behavioral patterns"""
        behavior_score = 1.0
        
        # High swarming probability indicates stress
        if analysis.swarming_probability > 0.6:
            behavior_score -= 0.4
        
        # Unusual patterns indicate health issues
        if len(analysis.unusual_patterns) > 2:
            behavior_score -= 0.3
        
        # Low foraging activity may indicate health problems
        if analysis.foraging_activity < 0.3:
            behavior_score -= 0.2
        
        return max(0.0, behavior_score)
    
    def _assess_pattern_health(self, metrics: BeeActivityMetrics) -> float:
        """Assess health based on pattern consistency"""
        if len(self.health_history) < 10:
            return 0.8  # Default score for insufficient data
        
        # Calculate consistency in recent activity
        recent_counts = [h.activity_pattern_score for h in list(self.health_history)[-10:]]
        consistency = 1.0 - min(np.std(recent_counts), 0.5) / 0.5
        
        return consistency
    
    def _identify_risks(self, activity_metrics: BeeActivityMetrics, 
                       behavior_analysis: BehaviorAnalysis) -> List[str]:
        """Identify specific health risks"""
        risks = []
        
        if behavior_analysis.swarming_probability > 0.7:
            risks.append("imminent_swarming")
        
        if activity_metrics.agitation_level > 0.8:
            risks.append("colony_stress")
        
        if activity_metrics.bee_count < 5:
            risks.append("population_decline")
        
        if "mass_exodus" in behavior_analysis.unusual_patterns:
            risks.append("colony_abandonment_risk")
        
        if behavior_analysis.foraging_activity < 0.2:
            risks.append("reduced_foraging")
        
        return risks

class DataAnalyticsEngine:
    """Main analytics engine that coordinates all analysis components"""
    
    def __init__(self, config_path: str = "hardware_config.json"):
        self.config = self._load_config(config_path)
        self.storage = DataStorage()
        self.activity_analyzer = ActivityAnalyzer()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.health_analyzer = HealthAnalyzer()
        self.running = False
        
        # Set entrance line if configured
        entrance_y = self.config.get('analytics', {}).get('entrance_line_y')
        if entrance_y:
            self.activity_analyzer.set_entrance_line(entrance_y)
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {}
    
    def process_detection_data(self, detections: List[Dict]) -> Dict[str, Any]:
        """Process raw detection data through all analysis stages"""
        try:
            # Stage 1: Activity Analysis
            activity_metrics = self.activity_analyzer.analyze_frame_activity(detections)
            
            # Stage 2: Behavior Analysis
            behavior_analysis = self.behavior_analyzer.analyze_behavior(activity_metrics)
            
            # Stage 3: Health Analysis
            health_assessment = self.health_analyzer.analyze_health(activity_metrics, behavior_analysis)
            
            # Store results
            self.storage.store_activity_metrics(activity_metrics)
            self.storage.store_behavior_analysis(behavior_analysis)
            self.storage.store_health_assessment(health_assessment)
            
            # Return comprehensive analysis
            return {
                'activity': asdict(activity_metrics),
                'behavior': asdict(behavior_analysis),
                'health': asdict(health_assessment),
                'alerts': self._generate_alerts(activity_metrics, behavior_analysis, health_assessment)
            }
            
        except Exception as e:
            logger.error(f"Error processing detection data: {e}")
            return {}
    
    def _generate_alerts(self, activity: BeeActivityMetrics, 
                        behavior: BehaviorAnalysis, 
                        health: HealthAssessment) -> List[Dict]:
        """Generate alerts based on analysis results"""
        alerts = []
        
        # Critical health alerts
        if health.overall_health_score < 0.5:
            alerts.append({
                'level': 'critical',
                'type': 'health',
                'message': f'Colony health score critically low: {health.overall_health_score:.2f}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Swarming alerts
        if behavior.swarming_probability > 0.7:
            alerts.append({
                'level': 'warning',
                'type': 'behavior',
                'message': f'High swarming probability detected: {behavior.swarming_probability:.2f}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Activity alerts
        if activity.agitation_level > 0.8:
            alerts.append({
                'level': 'warning',
                'type': 'activity',
                'message': f'High agitation level detected: {activity.agitation_level:.2f}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Population alerts
        if activity.bee_count < 3:
            alerts.append({
                'level': 'critical',
                'type': 'population',
                'message': f'Very low bee count: {activity.bee_count}',
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Generate daily summary report"""
        try:
            # Get data from last 24 hours
            activity_df = self.storage.get_recent_data('activity_metrics', 24)
            behavior_df = self.storage.get_recent_data('behavior_analysis', 24)
            health_df = self.storage.get_recent_data('health_assessment', 24)
            
            if activity_df.empty:
                return {'error': 'No data available for summary'}
            
            summary = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'activity_summary': {
                    'avg_bee_count': float(activity_df['bee_count'].mean()),
                    'max_bee_count': int(activity_df['bee_count'].max()),
                    'total_entrance_activity': int(activity_df['entrance_activity'].sum()),
                    'total_exit_activity': int(activity_df['exit_activity'].sum()),
                    'avg_agitation_level': float(activity_df['agitation_level'].mean())
                },
                'behavior_summary': {
                    'dominant_behaviors': behavior_df['dominant_behavior'].value_counts().to_dict() if not behavior_df.empty else {},
                    'avg_swarming_probability': float(behavior_df['swarming_probability'].mean()) if not behavior_df.empty else 0.0,
                    'avg_foraging_activity': float(behavior_df['foraging_activity'].mean()) if not behavior_df.empty else 0.0
                },
                'health_summary': {
                    'avg_health_score': float(health_df['overall_health_score'].mean()) if not health_df.empty else 0.0,
                    'min_health_score': float(health_df['overall_health_score'].min()) if not health_df.empty else 0.0,
                    'health_trend': self._calculate_health_trend(health_df)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return {'error': str(e)}
    
    def _calculate_health_trend(self, health_df: pd.DataFrame) -> str:
        """Calculate health trend over the day"""
        if len(health_df) < 2:
            return 'insufficient_data'
        
        # Simple trend calculation
        first_half = health_df.iloc[:len(health_df)//2]['overall_health_score'].mean()
        second_half = health_df.iloc[len(health_df)//2:]['overall_health_score'].mean()
        
        if second_half > first_half + 0.1:
            return 'improving'
        elif second_half < first_half - 0.1:
            return 'declining'
        else:
            return 'stable'

# Example usage and testing
if __name__ == "__main__":
    # Initialize analytics engine
    engine = DataAnalyticsEngine()
    
    # Simulate some detection data
    sample_detections = [
        {'bbox': [100, 200, 30, 25], 'confidence': 0.85, 'class': 'bee'},
        {'bbox': [150, 180, 28, 30], 'confidence': 0.92, 'class': 'bee'},
        {'bbox': [200, 220, 32, 27], 'confidence': 0.78, 'class': 'bee'},
        {'bbox': [80, 190, 29, 26], 'confidence': 0.88, 'class': 'bee'},
        {'bbox': [300, 250, 31, 28], 'confidence': 0.81, 'class': 'bee'}
    ]
    
    # Process the data
    logger.info("Processing sample detection data...")
    results = engine.process_detection_data(sample_detections)
    
    if results:
        print("\n=== Analysis Results ===")
        print(f"Bee Count: {results['activity']['bee_count']}")
        print(f"Dominant Behavior: {results['behavior']['dominant_behavior']}")
        print(f"Health Score: {results['health']['overall_health_score']:.2f}")
        print(f"Alerts: {len(results['alerts'])}")
        
        for alert in results['alerts']:
            print(f"  - {alert['level'].upper()}: {alert['message']}")
    
    # Generate daily summary
    logger.info("Generating daily summary...")
    summary = engine.get_daily_summary()
    print(f"\n=== Daily Summary ===")
    print(json.dumps(summary, indent=2, default=str))
