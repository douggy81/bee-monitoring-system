#!/usr/bin/env python3
"""
Hardware Integration Layer for Digital4.ai Bee Monitoring System

This module provides the hardware integration layer that interfaces with:
- Raspberry Pi Camera Module 3
- Environmental sensors (DHT22, light sensor)
- AI HAT+ (Hailo-8L) for edge AI processing
- Power management and monitoring

Author: Digital4.ai Development Team
Date: September 2025
"""

try:
    import cv2  # type: ignore
    _cv2_available = True
except Exception:
    cv2 = None  # type: ignore
    _cv2_available = False
import numpy as np
import os
import time
import json
import threading
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SensorReading:
    """Data structure for sensor readings"""
    timestamp: datetime
    temperature: float
    humidity: float
    light_level: float
    battery_level: float
    solar_power: float

@dataclass
class BeeDetection:
    """Data structure for bee detection results"""
    timestamp: datetime
    bee_count: int
    bounding_boxes: List[Tuple[int, int, int, int]]
    confidence_scores: List[float]
    behavior_classification: str
    health_indicators: Dict[str, float]

class CameraManager:
    """Manages the Pi Camera Module 3"""
    
    def __init__(self, resolution=(1280, 720), fps=30):
        self.resolution = resolution
        self.fps = fps
        self.cap = None
        self.is_recording = False
        self.use_picamera2 = False
        self.picam2 = None
        
    def initialize(self) -> bool:
        """Initialize the camera"""
        try:
            # Prefer Picamera2 on Raspberry Pi OS Bookworm (libcamera stack)
            try:
                from picamera2 import Picamera2
                self.picam2 = Picamera2()
                config = self.picam2.create_preview_configuration(
                    main={"size": (self.resolution[0], self.resolution[1]), "format": "RGB888"}
                )
                self.picam2.configure(config)
                self.picam2.start()
                self.use_picamera2 = True
                logger.info(
                    f"Camera initialized (Picamera2): {self.resolution[0]}x{self.resolution[1]} @ {self.fps}fps"
                )
                return True
            except Exception as pe:
                logger.warning(f"Picamera2 not available or failed to start ({pe}); falling back to OpenCV VideoCapture")

            # Fallback to OpenCV VideoCapture
            if not _cv2_available:
                logger.error("OpenCV (cv2) not available; cannot use VideoCapture fallback")
                return False
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            if not self.cap.isOpened():
                logger.error("Failed to open camera via OpenCV VideoCapture")
                return False
            logger.info(
                f"Camera initialized (OpenCV): {self.resolution[0]}x{self.resolution[1]} @ {self.fps}fps"
            )
            return True
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame"""
        try:
            if self.use_picamera2 and self.picam2 is not None:
                # Picamera2 returns RGB; convert to BGR for OpenCV compatibility
                rgb = self.picam2.capture_array()
                if rgb is None:
                    logger.warning("Picamera2 returned no frame")
                    return None
                # Avoid cv2; swap channels to BGR using numpy
                if rgb.ndim == 3 and rgb.shape[2] == 3:
                    frame = rgb[:, :, ::-1]
                else:
                    frame = rgb
                return frame
            else:
                if not _cv2_available:
                    return None
                if not self.cap or not self.cap.isOpened():
                    return None
                ret, frame = self.cap.read()
                if ret:
                    return frame
                else:
                    logger.warning("Failed to capture frame")
                    return None
        except Exception as e:
            logger.warning(f"Capture error: {e}")
            return None
    
    def start_recording(self, output_path: str):
        """Start recording video to file"""
        if self.is_recording:
            return
            
        if not _cv2_available:
            logger.error("OpenCV (cv2) not available; recording is disabled")
            return
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, self.resolution)
        self.is_recording = True
        logger.info(f"Started recording to {output_path}")
    
    def stop_recording(self):
        """Stop recording video"""
        if self.is_recording and hasattr(self, 'video_writer'):
            self.video_writer.release()
            self.is_recording = False
            logger.info("Stopped recording")
    
    def cleanup(self):
        """Clean up camera resources"""
        try:
            if self.use_picamera2 and self.picam2 is not None:
                self.picam2.stop()
                self.picam2 = None
        except Exception:
            pass
        if self.cap:
            self.cap.release()
        if self.is_recording:
            self.stop_recording()

class SensorManager:
    """Manages environmental sensors and power monitoring"""
    
    def __init__(self):
        self.dht22_pin = 4  # GPIO pin for DHT22
        self.light_sensor_pin = 2  # I2C address for light sensor
        self.battery_monitor_pin = 1  # ADC channel for battery monitoring
        
    def read_temperature_humidity(self) -> Tuple[float, float]:
        """Read temperature and humidity from DHT22"""
        try:
            # Simulated DHT22 reading - replace with actual sensor library
            # import Adafruit_DHT
            # humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self.dht22_pin)
            
            # For now, return simulated values
            temperature = 25.0 + np.random.normal(0, 2)
            humidity = 60.0 + np.random.normal(0, 5)
            
            return temperature, humidity
            
        except Exception as e:
            logger.error(f"Failed to read DHT22: {e}")
            return 0.0, 0.0
    
    def read_light_level(self) -> float:
        """Read light level from light sensor"""
        try:
            # Simulated light sensor reading - replace with actual sensor library
            # import board
            # import adafruit_tsl2591
            # i2c = board.I2C()
            # sensor = adafruit_tsl2591.TSL2591(i2c)
            # light_level = sensor.lux
            
            # For now, return simulated value
            light_level = 1000.0 + np.random.normal(0, 100)
            
            return max(0, light_level)
            
        except Exception as e:
            logger.error(f"Failed to read light sensor: {e}")
            return 0.0
    
    def read_power_status(self) -> Tuple[float, float]:
        """Read battery level and solar power generation"""
        try:
            # Simulated power monitoring - replace with actual ADC reading
            battery_level = 85.0 + np.random.normal(0, 5)
            solar_power = 15.0 + np.random.normal(0, 3)
            
            return max(0, min(100, battery_level)), max(0, solar_power)
            
        except Exception as e:
            logger.error(f"Failed to read power status: {e}")
            return 0.0, 0.0
    
    def get_sensor_reading(self) -> SensorReading:
        """Get complete sensor reading"""
        temperature, humidity = self.read_temperature_humidity()
        light_level = self.read_light_level()
        battery_level, solar_power = self.read_power_status()
        
        return SensorReading(
            timestamp=datetime.now(),
            temperature=temperature,
            humidity=humidity,
            light_level=light_level,
            battery_level=battery_level,
            solar_power=solar_power
        )

class AIProcessor:
    """Manages AI processing using Hailo-8L AI HAT+"""
    
    def __init__(self):
        self.model_loaded = False
        self.detection_model = None
        self.behavior_model = None
        self.health_model = None
        self.backend = None
        self.backend_name = os.getenv("AI_BACKEND", "CPU").upper()
        
    def initialize(self) -> bool:
        """Initialize AI backend and models"""
        try:
            if self.backend_name == "HAILO":
                try:
                    from ai.hailo_backend import HailoBackend
                    hef_path = os.getenv("HAILO_HEF", "")
                    self.backend = HailoBackend(hef_path=hef_path or None)
                    if self.backend.initialize():
                        self.model_loaded = True
                        logger.info("Hailo backend initialized%s",
                                    f" with HEF '{hef_path}'" if hef_path else " (no HEF provided; using placeholder inference)")
                        return True
                    else:
                        logger.warning("Falling back to CPU backend after Hailo backend failed to initialize")
                except Exception as he:
                    logger.warning(f"Hailo backend import/init failed: {he}. Falling back to CPU backend")

            # Default CPU fallback (simulation)
            from ai.cpu_backend import CpuBackend
            self.backend = CpuBackend()
            if self.backend.initialize():
                self.model_loaded = True
                logger.info("CPU backend initialized (simulated inference)")
                return True

            logger.error("No AI backend initialized")
            return False

        except Exception as e:
            logger.error(f"AI backend initialization failed: {e}")
            return False
    
    def detect_bees(self, frame: np.ndarray) -> BeeDetection:
        """Detect bees in the frame using the selected backend"""
        if not self.model_loaded or self.backend is None:
            return self._create_empty_detection()

        try:
            boxes, scores = self.backend.infer(frame)
            bee_count = len(boxes)
            behavior = self._classify_behavior(frame, boxes)
            health_indicators = self._analyze_health(frame, boxes)
            return BeeDetection(
                timestamp=datetime.now(),
                bee_count=bee_count,
                bounding_boxes=boxes,
                confidence_scores=scores,
                behavior_classification=behavior,
                health_indicators=health_indicators,
            )
        except Exception as e:
            logger.error(f"Bee detection failed: {e}")
            return self._create_empty_detection()
    
    def _classify_behavior(self, frame: np.ndarray, bounding_boxes: List) -> str:
        """Classify bee behavior"""
        # Simulated behavior classification
        behaviors = ["normal", "agitated", "clustering", "swarming_prep"]
        return np.random.choice(behaviors, p=[0.6, 0.2, 0.15, 0.05])
    
    def _analyze_health(self, frame: np.ndarray, bounding_boxes: List) -> Dict[str, float]:
        """Analyze bee health indicators"""
        # Simulated health analysis
        return {
            "mite_presence": np.random.uniform(0, 0.3),
            "wing_deformity": np.random.uniform(0, 0.1),
            "size_variance": np.random.uniform(0.8, 1.2),
            "activity_level": np.random.uniform(0.5, 1.0)
        }
    
    def _create_empty_detection(self) -> BeeDetection:
        """Create empty detection result"""
        return BeeDetection(
            timestamp=datetime.now(),
            bee_count=0,
            bounding_boxes=[],
            confidence_scores=[],
            behavior_classification="unknown",
            health_indicators={}
        )

class HardwareIntegrationLayer:
    """Main hardware integration layer"""
    
    def __init__(self):
        self.camera = CameraManager()
        self.sensors = SensorManager()
        self.ai_processor = AIProcessor()
        self.data_queue = queue.Queue()
        self.running = False
        
    def initialize(self) -> bool:
        """Initialize all hardware components"""
        logger.info("Initializing hardware integration layer...")
        
        success = True
        success &= self.camera.initialize()
        success &= self.ai_processor.initialize()
        
        if success:
            logger.info("Hardware integration layer initialized successfully")
        else:
            logger.error("Hardware initialization failed")
            
        return success
    
    def start_monitoring(self):
        """Start the monitoring loop"""
        if self.running:
            return
            
        self.running = True
        
        # Start sensor reading thread
        sensor_thread = threading.Thread(target=self._sensor_loop)
        sensor_thread.daemon = True
        sensor_thread.start()
        
        # Start camera processing thread
        camera_thread = threading.Thread(target=self._camera_loop)
        camera_thread.daemon = True
        camera_thread.start()
        
        logger.info("Monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("Monitoring stopped")
    
    def _sensor_loop(self):
        """Sensor reading loop"""
        while self.running:
            try:
                sensor_data = self.sensors.get_sensor_reading()
                self.data_queue.put(("sensor", sensor_data))
                time.sleep(30)  # Read sensors every 30 seconds
                
            except Exception as e:
                logger.error(f"Sensor loop error: {e}")
                time.sleep(5)
    
    def _camera_loop(self):
        """Camera processing loop"""
        while self.running:
            try:
                frame = self.camera.capture_frame()
                if frame is not None:
                    detection = self.ai_processor.detect_bees(frame)
                    self.data_queue.put(("detection", detection))
                
                time.sleep(1.0 / 30)  # 30 FPS processing
                
            except Exception as e:
                logger.error(f"Camera loop error: {e}")
                time.sleep(1)
    
    def get_data(self) -> Optional[Tuple[str, any]]:
        """Get data from the queue"""
        try:
            return self.data_queue.get_nowait()
        except queue.Empty:
            return None
    
    def cleanup(self):
        """Clean up all resources"""
        self.stop_monitoring()
        self.camera.cleanup()
        logger.info("Hardware integration layer cleaned up")

# Example usage
if __name__ == "__main__":
    # Initialize hardware integration layer
    hardware = HardwareIntegrationLayer()
    
    if hardware.initialize():
        try:
            hardware.start_monitoring()
            
            # Monitor for 60 seconds
            start_time = time.time()
            while time.time() - start_time < 60:
                data = hardware.get_data()
                if data:
                    data_type, data_content = data
                    if data_type == "sensor":
                        logger.info(f"Sensor: T={data_content.temperature:.1f}°C, "
                                  f"H={data_content.humidity:.1f}%, "
                                  f"L={data_content.light_level:.0f}lux, "
                                  f"B={data_content.battery_level:.1f}%")
                    elif data_type == "detection":
                        logger.info(f"Detection: {data_content.bee_count} bees, "
                                  f"behavior={data_content.behavior_classification}")
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            hardware.cleanup()
    else:
        logger.error("Failed to initialize hardware")
