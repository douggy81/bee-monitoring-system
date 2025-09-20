#!/usr/bin/env python3
"""
Setup Script for Digital4.ai Bee Monitoring System - Current Hardware

This script sets up the development environment for the available hardware:
- Raspberry Pi 5 (8GB RAM)
- AI HAT+ (13 TOPS Hailo-8L)
- Camera Module 3 (12MP)
- 256GB microSD storage

Author: Digital4.ai Development Team
Date: September 2025
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HardwareSetup:
    """Setup class for configuring the bee monitoring system hardware"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.project_dir = self.home_dir / "bee_monitoring"
        self.data_dir = self.home_dir / "bee_data"
        self.models_dir = self.project_dir / "models"
        
    def run_setup(self):
        """Run the complete setup process"""
        logger.info("Starting Digital4.ai Bee Monitoring System setup...")
        
        try:
            self.create_directories()
            self.check_system_requirements()
            self.setup_camera()
            self.setup_ai_hat()
            self.install_dependencies()
            self.create_config_files()
            self.setup_database()
            self.create_startup_scripts()
            self.run_hardware_tests()
            
            logger.info("Setup completed successfully!")
            self.print_next_steps()
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            sys.exit(1)
    
    def create_directories(self):
        """Create necessary directories"""
        logger.info("Creating project directories...")
        
        directories = [
            self.project_dir,
            self.data_dir,
            self.models_dir,
            self.data_dir / "videos",
            self.data_dir / "images",
            self.data_dir / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    def check_system_requirements(self):
        """Check system requirements and hardware"""
        logger.info("Checking system requirements...")
        
        # Check OS version
        try:
            result = subprocess.run(['lsb_release', '-d'], capture_output=True, text=True)
            logger.info(f"OS: {result.stdout.strip()}")
        except:
            logger.warning("Could not determine OS version")
        
        # Check Python version
        python_version = sys.version
        logger.info(f"Python version: {python_version}")
        
        # Check available memory
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_info = f.read()
                for line in mem_info.split('\n'):
                    if 'MemTotal' in line:
                        total_mem = int(line.split()[1]) // 1024  # Convert to MB
                        logger.info(f"Total RAM: {total_mem} MB")
                        if total_mem < 7000:  # Less than ~7GB (accounting for system usage)
                            logger.warning("RAM may be insufficient for optimal performance")
                        break
        except:
            logger.warning("Could not determine memory information")
        
        # Check storage space
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            logger.info(f"Storage info:\n{result.stdout}")
        except:
            logger.warning("Could not determine storage information")
    
    def setup_camera(self):
        """Setup Camera Module 3"""
        logger.info("Setting up Camera Module 3...")
        
        # Enable camera interface
        try:
            # Check if camera is detected
            result = subprocess.run(['vcgencmd', 'get_camera'], capture_output=True, text=True)
            logger.info(f"Camera status: {result.stdout.strip()}")
            
            # Test camera with rpicam-apps (Bookworm+)
            logger.info("Testing camera with rpicam-hello...")
            result = subprocess.run(['rpicam-hello', '--list-cameras'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("Camera detected successfully")
                logger.info(f"Camera info:\n{result.stdout}")
            else:
                logger.warning("Camera not detected or not working properly")
                
        except subprocess.TimeoutExpired:
            logger.warning("Camera test timed out")
        except FileNotFoundError:
            logger.warning("rpicam-apps not found - install with: sudo apt install -y rpicam-apps")
        except Exception as e:
            logger.warning(f"Camera setup issue: {e}")
    
    def setup_ai_hat(self):
        """Setup AI HAT+ (Hailo-8L)"""
        logger.info("Setting up AI HAT+ (Hailo-8L)...")
        
        try:
            # Check if Hailo device is detected on PCIe (Pi 5 HAT+ over M.2)
            try:
                result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
                if 'Hailo' in result.stdout or '1e60' in result.stdout:
                    logger.info("Hailo device detected on PCIe")
                else:
                    logger.warning("Hailo device not detected on PCIe (lspci) — ensure PCIe is enabled and powered")
            except FileNotFoundError:
                logger.warning("lspci not found — install pciutils: sudo apt install -y pciutils")
            
            # Check for Hailo runtime
            try:
                result = subprocess.run(['hailortcli', '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Hailo runtime version: {result.stdout.strip()}")
                else:
                    logger.warning("Hailo runtime not installed")
            except FileNotFoundError:
                logger.warning("Hailo CLI not found - runtime may not be installed")
                logger.info("Please install Hailo runtime from: https://hailo.ai/developer-zone/")
                
        except Exception as e:
            logger.warning(f"AI HAT+ setup issue: {e}")
    
    def install_dependencies(self):
        """Install Python dependencies"""
        logger.info("Installing Python dependencies...")
        
        # Copy requirements.txt to project directory if it exists
        requirements_file = Path("requirements.txt")
        project_requirements = self.project_dir / "requirements.txt"
        
        if requirements_file.exists():
            import shutil
            shutil.copy(requirements_file, project_requirements)
            
            # Install dependencies
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(project_requirements)], 
                             check=True)
                logger.info("Dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install dependencies: {e}")
                raise
        else:
            logger.warning("requirements.txt not found - skipping dependency installation")
    
    def create_config_files(self):
        """Create configuration files"""
        logger.info("Creating configuration files...")
        
        # Enhanced config for current hardware
        config = {
            "camera": {
                "resolution": [1920, 1080],
                "fps": 30,
                "device_id": 0,
                "auto_exposure": True,
                "brightness": 50,
                "contrast": 50,
                "saturation": 50
            },
            "ai_processing": {
                "detection_model": "yolov8n_bee_detection.hef",
                "behavior_model": "bee_behavior_classifier.hef",
                "health_model": "bee_health_detector.hef",
                "inference_threads": 4,
                "batch_size": 1,
                "confidence_threshold": 0.5,
                "nms_threshold": 0.4
            },
            "data_storage": {
                "local_storage_path": str(self.data_dir),
                "max_video_duration": 300,
                "video_compression": "h264",
                "data_retention_days": 30,
                "backup_to_cloud": False
            },
            "analytics": {
                "entrance_line_y": 400,
                "activity_window_size": 100,
                "behavior_history_size": 50,
                "health_history_size": 100
            },
            "alerts": {
                "swarming_threshold": 0.7,
                "agitation_duration_threshold": 300,
                "health_score_threshold": 0.5,
                "low_activity_threshold": 3,
                "high_activity_threshold": 50
            },
            "system": {
                "log_level": "INFO",
                "max_log_size": "10MB",
                "log_rotation": 5,
                "enable_debug_mode": True
            }
        }
        
        config_file = self.project_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration file created: {config_file}")
    
    def setup_database(self):
        """Setup SQLite database"""
        logger.info("Setting up database...")
        
        # Copy and run the data analytics engine to initialize database
        analytics_file = Path("data_analytics_engine.py")
        if analytics_file.exists():
            import shutil
            shutil.copy(analytics_file, self.project_dir / "data_analytics_engine.py")
            
            # Initialize database by importing the module
            sys.path.insert(0, str(self.project_dir))
            try:
                from data_analytics_engine import DataStorage
                storage = DataStorage(str(self.data_dir / "monitoring.db"))
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.warning(f"Database initialization issue: {e}")
        else:
            logger.warning("data_analytics_engine.py not found - skipping database setup")
    
    def create_startup_scripts(self):
        """Create startup scripts"""
        logger.info("Creating startup scripts...")
        
        # Main monitoring script
        monitor_script = self.project_dir / "start_monitoring.py"
        monitor_content = '''#!/usr/bin/env python3
"""
Bee Monitoring System Startup Script
"""

import sys
import logging
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_dir.parent / 'bee_data' / 'logs' / 'monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main monitoring function"""
    logger.info("Starting Bee Monitoring System...")
    
    try:
        # Import and initialize hardware integration
        from hardware_integration import HardwareIntegrationLayer
        from data_analytics_engine import DataAnalyticsEngine
        
        # Initialize components
        hardware = HardwareIntegrationLayer()
        analytics = DataAnalyticsEngine(str(project_dir / "config.json"))
        
        if hardware.initialize():
            logger.info("Hardware initialized successfully")
            hardware.start_monitoring()
            
            # Main monitoring loop
            import time
            while True:
                data = hardware.get_data()
                if data:
                    data_type, data_content = data
                    if data_type == "detection":
                        # Process detection data through analytics
                        detections = [{'bbox': bbox, 'confidence': conf} 
                                    for bbox, conf in zip(data_content.bounding_boxes, 
                                                        data_content.confidence_scores)]
                        results = analytics.process_detection_data(detections)
                        
                        if results.get('alerts'):
                            for alert in results['alerts']:
                                logger.warning(f"ALERT: {alert['message']}")
                
                time.sleep(0.1)
                
        else:
            logger.error("Failed to initialize hardware")
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")
    finally:
        if 'hardware' in locals():
            hardware.cleanup()

if __name__ == "__main__":
    main()
'''
        
        with open(monitor_script, 'w') as f:
            f.write(monitor_content)
        
        # Make executable
        os.chmod(monitor_script, 0o755)
        logger.info(f"Monitoring script created: {monitor_script}")
        
        # System service file (optional)
        service_content = f'''[Unit]
Description=Digital4.ai Bee Monitoring System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory={self.project_dir}
ExecStart=/usr/bin/python3 {monitor_script}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
        
        service_file = self.project_dir / "bee-monitoring.service"
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        logger.info(f"Service file created: {service_file}")
        logger.info("To install as system service, run:")
        logger.info(f"sudo cp {service_file} /etc/systemd/system/")
        logger.info("sudo systemctl enable bee-monitoring.service")
        logger.info("sudo systemctl start bee-monitoring.service")
    
    def run_hardware_tests(self):
        """Run basic hardware tests"""
        logger.info("Running hardware tests...")
        
        # Test camera
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    logger.info(f"Camera test passed - captured frame: {frame.shape}")
                    # Save test image
                    test_image_path = self.data_dir / "images" / "camera_test.jpg"
                    cv2.imwrite(str(test_image_path), frame)
                    logger.info(f"Test image saved: {test_image_path}")
                else:
                    logger.warning("Camera test failed - could not capture frame")
                cap.release()
            else:
                logger.warning("Camera test failed - could not open camera")
        except Exception as e:
            logger.warning(f"Camera test error: {e}")
        
        # Test storage write
        try:
            test_file = self.data_dir / "test_write.txt"
            with open(test_file, 'w') as f:
                f.write("Storage test successful")
            test_file.unlink()  # Delete test file
            logger.info("Storage write test passed")
        except Exception as e:
            logger.warning(f"Storage test error: {e}")
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\n" + "="*60)
        print("SETUP COMPLETE - NEXT STEPS")
        print("="*60)
        print(f"Project directory: {self.project_dir}")
        print(f"Data directory: {self.data_dir}")
        print()
        print("To start monitoring:")
        print(f"cd {self.project_dir}")
        print("python3 start_monitoring.py")
        print()
        print("To install missing components:")
        print("1. Hailo runtime: https://hailo.ai/developer-zone/")
        print("2. Pre-trained models: Download to models/ directory")
        print()
        print("Configuration file: config.json")
        print("Logs location: bee_data/logs/")
        print()
        print("For development:")
        print("- Modify hardware_integration.py for sensor integration")
        print("- Update data_analytics_engine.py for custom analytics")
        print("- Configure alerts in config.json")
        print("="*60)

def main():
    """Main setup function"""
    setup = HardwareSetup()
    setup.run_setup()

if __name__ == "__main__":
    main()
