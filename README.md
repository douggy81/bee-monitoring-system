# Digital4.ai Bee Monitoring System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-red.svg)](https://www.raspberrypi.org/)

A comprehensive IoT solution for modern beekeeping that combines AI-powered computer vision, environmental monitoring, and real-time analytics to provide actionable insights about bee colonies.

## 🎥 Video Demonstrations

### System Overview & Live Demo
[![Bee Monitoring System Demo](https://img.youtube.com/vi/Y1ME9W5ozKQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=Y1ME9W5ozKQ)

### AI Behavior Analysis in Action
[![AI Bee Behavior Analysis](https://img.youtube.com/vi/c9Q56m17Nj0/maxresdefault.jpg)](https://www.youtube.com/watch?v=c9Q56m17Nj0)

## 📋 Table of Contents

- [Video Demonstrations](#video-demonstrations)
- [Features](#features)
- [Video Processing Notebook](#video-processing-notebook)
- [Hardware Requirements](#hardware-requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [OTA Updates](#ota-updates)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### Real-Time Monitoring
- **AI-Powered Bee Detection**: YOLO11m computer vision with 96% accuracy for live bee counting
- **Behavior Analysis**: Automatic classification of flying, browsing, and stationary behaviors with FPS-aware tracking
- **ByteTrack Integration**: Persistent multi-object tracking for individual bee monitoring
- **Environmental Monitoring**: Temperature, humidity, and light level tracking
- **Health Assessment**: Colony health scoring with mite detection and wing condition analysis

### Advanced Analytics
- **Activity Patterns**: Daily and seasonal behavior analysis with trend visualization
- **Behavior Classification**: Flying, browsing, and stationary detection with 5-second rolling averages
- **Peak Behavior Tracking**: Persistent behavior labels (bees that flew stay labeled as "flying")
- **Predictive Insights**: Weather impact forecasting and health trend predictions
- **Historical Data**: Comprehensive data retention with exportable analytics in JSON format
- **Alert System**: Configurable thresholds with real-time notifications
- **Pollen Counter**: Extensible framework for pollen detection (demo included)

### Professional Dashboard
- **Responsive Web Interface**: Modern React-based dashboard with real-time updates
- **Interactive Visualizations**: Dynamic charts and graphs using Recharts
- **Multi-Device Support**: Desktop, tablet, and mobile compatibility
- **Real-Time Updates**: Live data refresh every 5 seconds
- **Video Streaming**: Live MJPEG camera feed with automatic fallback

### Video Processing & Analysis
- **Google Colab Notebook**: Cloud-based video processing with GPU acceleration
- **Behavior Detection**: Automated flying/browsing/stationary classification
- **Enhanced Output**: Color-coded bounding boxes, trails, and statistics overlay
- **Fast Processing**: Optimized for 1080p @ 30fps (6 minutes total time)
- **Logo Integration**: Branded overlays with fade-in effects and shadows

## 🎬 Video Processing Notebook

### Quick Start with Google Colab

Process and analyze bee videos with AI-powered behavior classification in the cloud!

**📓 Notebook Location**: [`notebooks/bee_processing_FIXED.ipynb`](notebooks/bee_processing_FIXED.ipynb)

### Features
- ✅ **Flying Detection**: Identifies bees entering/leaving hive (cyan boxes)
- ✅ **Browsing Detection**: Detects bees walking on hive surface (green boxes)
- ✅ **Stationary Detection**: Finds dead/stuck/resting bees (red boxes)
- ✅ **FPS-Aware Classification**: Automatically adjusts thresholds for any frame rate (30fps, 60fps, 120fps)
- ✅ **Peak Behavior Tracking**: Bees that flew stay labeled as "flying" even after landing
- ✅ **5-Second Rolling Averages**: Smooth metrics for all behavior counts
- ✅ **Pollen Counter**: Extensible framework for pollen detection
- ✅ **Logo Overlay**: Digital4.ai branding with fade-in and shadow effects
- ✅ **JSON Export**: Complete tracking data with trajectories and behavior statistics

### Processing Time
- **Conversion**: ~30 seconds (4K → 1080p)
- **AI Processing**: ~5-6 minutes (YOLO11m + ByteTrack)
- **Total**: ~6 minutes for typical bee video

### How to Use

1. **Open in Google Colab**:
   - Go to [Google Colab](https://colab.research.google.com/)
   - `File → Upload notebook`
   - Select `bee_processing_FIXED.ipynb`

2. **Enable GPU**:
   - `Runtime → Change runtime type`
   - Hardware accelerator: `GPU`
   - Save

3. **Upload Your Video**:
   - Upload to Google Drive: `/MyDrive/bee-monitoring/`
   - Supports: `.mp4`, `.mov`, `.avi`

4. **Run All Cells**:
   - `Runtime → Run all`
   - Wait ~6 minutes
   - Download enhanced video + JSON data

### Output

**Enhanced Video Includes**:
- Color-coded bounding boxes (Cyan=Flying, Green=Browsing, Red=Stationary)
- Persistent tracking IDs
- Motion trails
- Real-time statistics overlay:
  - Current bee count
  - 5-second rolling average
  - Behavior breakdown (Flying/Browsing/Stationary)
  - Pollen count
- Digital4.ai logo with fade-in

**JSON Export Contains**:
```json
{
  "summary": {
    "total_unique_bees": 156,
    "behaviors": {
      "flying": 45,
      "browsing": 98,
      "stationary": 13
    },
    "pollen_count": 42
  },
  "tracks": {
    "107": {
      "behavior": "flying",
      "trajectory": [[x, y, frame], ...]
    }
  }
}
```

### Behavior Classification Logic

**Flying (FLY)**: Fast movement (>3 px/frame @ 30fps)
- Incoming/outgoing bees
- Quick passes near hive
- Peak speed detected anywhere in track

**Browsing (BRW)**: Slow movement (0.5-3 px/frame)
- Walking on hive surface
- Slow hovering near entrance
- General activity on hive

**Stationary (STA)**: Minimal movement (<0.5 px/frame)
- Dead bees
- Stuck bees
- Resting/cleaning bees

### Customization

Edit configuration in Cell 6:
```python
CONFIG = {
    'conf_threshold': 0.50,        # Detection confidence
    'trail_length': 30,            # Motion trail frames
    'lost_track_buffer': 30,       # Tracking persistence
    # ... more settings
}
```

### Troubleshooting

**Out of Memory?**
- Use smaller videos (<5 minutes)
- Already downscaled to 1080p automatically

**Processing Too Slow?**
- Verify GPU is enabled (Runtime → Change runtime type)
- Should see "GPU: Tesla T4" in Cell 2 output

**No Behaviors Detected?**
- Check video has actual bee movement
- Classifier needs at least 1 second of tracking data

---

## 🛠 Hardware Requirements

### Core Components (Required)
- **Raspberry Pi 5** (8GB RAM recommended)
- **MicroSD Card** (256GB minimum, Class 10)
- **AI HAT+** (13 TOPS for accelerated AI processing)
- **Camera Module 3** (High-resolution image capture)

### Additional Sensors (Optional)
- **DHT22**: Temperature and humidity monitoring
- **BH1750**: Light level measurement
- **DS18B20**: Temperature probe for hive monitoring

### Power and Connectivity
- **Solar Panel**: 20W minimum for remote operation
- **Battery Pack**: 10,000mAh minimum capacity
- **4G/LTE Module**: For areas without WiFi connectivity
- **Weatherproof Enclosure**: IP65 rated for outdoor installation

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/douggy81/bee-monitoring-system.git
cd bee-monitoring-system
```

### 2. Automated Setup (Raspberry Pi)
```bash
# Make the setup script executable
chmod +x scripts/setup.sh

# Run automated setup
sudo ./scripts/setup.sh
```

### 3. Start the System
```bash
# Start all services
sudo systemctl start bee-monitoring
sudo systemctl start bee-api

# Check status
sudo systemctl status bee-monitoring bee-api
```

### 4. Access the Dashboard
Open your browser and navigate to:
- **Local Access**: `http://[raspberry-pi-ip]:5000`

## 📦 Installation

### Manual Installation

#### 1. System Prerequisites
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install python3-pip python3-venv git nginx sqlite3 -y

# Install OpenCV dependencies
sudo apt install libopencv-dev python3-opencv -y

# Enable camera and I2C interfaces
sudo raspi-config
# Navigate to Interface Options → Camera → Enable
# Navigate to Interface Options → I2C → Enable
```

#### 2. Python Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Database Initialization
```bash
# Create database directory
sudo mkdir -p /opt/bee-monitoring/data

# Initialize database
python scripts/init_database.py
```

#### 4. Service Configuration
```bash
# Copy service files
sudo cp config/systemd/*.service /etc/systemd/system/

# Enable services
sudo systemctl enable bee-monitoring bee-api nginx

# Start services
sudo systemctl start bee-monitoring bee-api nginx
```

## ⚙️ Configuration

### Hardware Configuration
Edit `config/hardware_config.json`:

```json
{
  "camera": {
    "resolution": [1920, 1080],
    "fps": 30,
    "rotation": 0,
    "detection_enabled": true
  },
  "ai_processing": {
    "model_path": "/opt/bee-monitoring/models/bee_detection_v1.tflite",
    "confidence_threshold": 0.5,
    "nms_threshold": 0.4,
    "max_detections": 100
  },
  "sensors": {
    "dht22_pin": 4,
    "light_sensor_address": "0x23",
    "temperature_probe_pin": 18
  },
  "data_collection": {
    "interval_seconds": 30,
    "batch_size": 10,
    "storage_path": "/opt/bee-monitoring/data"
  }
}
```

### API Configuration
Edit `config/api_config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  },
  "database": {
    "path": "/opt/bee-monitoring/data/bee_monitoring.db",
    "backup_enabled": true,
    "retention_days": 30
  },
  "alerts": {
    "swarming_threshold": 0.7,
    "health_threshold": 0.5,
    "agitation_threshold": 0.8
  }
}
```

## 📚 API Documentation

### Base URL
- **Local**: `http://[raspberry-pi-ip]:5000/api/bee`

### Key Endpoints

#### System Status
```bash
GET /health
GET /current-status
GET /system-status
```

#### Data Retrieval
```bash
GET /activity-data?hours=24&limit=100
GET /health-data?hours=168&limit=50
GET /environmental-data?hours=24&limit=100
GET /behavior-data?hours=24&limit=100
```

#### Analytics
```bash
GET /analytics/summary?hours=24
```

#### Alert Management
```bash
GET /alerts?acknowledged=false&limit=50
POST /alerts/{alert_id}/acknowledge
```

#### Data Ingestion
```bash
POST /data/ingest
Content-Type: application/json

{
  "activity": {
    "bee_count": 45,
    "entrance_activity": 12,
    "exit_activity": 8,
    "agitation_level": 0.3
  },
  "environment": {
    "temperature": 24.5,
    "humidity": 62,
    "light_level": 850
  }
}
```

## 🚀 Deployment

### Local Deployment (Raspberry Pi)
```bash
# Clone and setup
git clone https://github.com/douggy81/bee-monitoring-system.git
cd bee-monitoring-system
sudo ./scripts/setup.sh

# Start services
sudo systemctl start bee-monitoring bee-api
```

### Cloud Deployment
The system includes configuration for cloud deployment with automatic scaling and load balancing.

```bash
# Build for production
npm run build

# Deploy to cloud platform
./scripts/deploy.sh production
```

## 🔄 OTA Updates

### Automatic Updates
The system includes an Over-The-Air (OTA) update mechanism for seamless deployments:

```bash
# Enable automatic updates
sudo systemctl enable bee-ota-updater

# Manual update trigger
sudo /opt/bee-monitoring/scripts/ota-update.sh
```

### Update Process
1. **Check for Updates**: System checks GitHub repository for new releases
2. **Download**: Automatically downloads latest code and dependencies
3. **Backup**: Creates backup of current system state
4. **Deploy**: Installs updates with zero-downtime deployment
5. **Verify**: Performs health checks and rollback if needed

### Update Configuration
Edit `config/ota_config.json`:

```json
{
  "repository": "https://github.com/douggy81/bee-monitoring-system.git",
  "branch": "main",
  "check_interval": 3600,
  "auto_update": true,
  "backup_retention": 5
}
```

## 📊 Monitoring and Maintenance

### System Health Monitoring
```bash
# Check system status
sudo systemctl status bee-monitoring bee-api

# View logs
sudo journalctl -u bee-monitoring -f
sudo journalctl -u bee-api -f

# Monitor system resources
htop
df -h
```

### Database Maintenance
```bash
# Backup database
sudo /opt/bee-monitoring/scripts/backup-database.sh

# Clean old data
sudo /opt/bee-monitoring/scripts/cleanup-data.sh

# Optimize database
sudo /opt/bee-monitoring/scripts/optimize-database.sh
```

## 🧪 Development

### Development Setup
```bash
# Clone repository
git clone https://github.com/douggy81/bee-monitoring-system.git
cd bee-monitoring-system

# Setup development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Start development servers
# Terminal 1: API server
cd api && python main.py

# Terminal 2: Frontend development server
cd dashboard && npm run dev
```

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/hardware/

# Run with coverage
pytest --cov=src tests/
```

## 🤝 Contributing

We welcome contributions to the Digital4.ai Bee Monitoring System! Please follow these guidelines:

1. **Fork the Repository**: Create your own fork of the project
2. **Create Feature Branch**: `git checkout -b feature/amazing-feature`
3. **Commit Changes**: `git commit -m 'Add amazing feature'`
4. **Push to Branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**: Submit a pull request with detailed description

### Development Guidelines
- Follow PEP 8 style guidelines for Python code
- Use ESLint and Prettier for JavaScript/React code
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- **API Reference**: Complete REST API documentation
- **Hardware Guide**: Wiring diagrams and component specifications
- **Deployment Guide**: Step-by-step installation instructions

### Community
- **Issues**: Report bugs and request features on GitHub Issues
- **Discussions**: Join community discussions on GitHub Discussions
- **Wiki**: Additional documentation and tutorials

### Commercial Support
For commercial deployments and custom development:
- **Email**: support@digital4.ai
- **Website**: [https://digital4.ai](https://digital4.ai)

## 🏆 Acknowledgments

- **Raspberry Pi Foundation** for excellent hardware platform
- **TensorFlow Team** for AI/ML frameworks
- **React Community** for frontend development tools
- **Beekeeping Community** for domain expertise and feedback

---

**Made with ❤️ by Digital4.ai**

*Empowering modern beekeeping through AI and IoT technology*
