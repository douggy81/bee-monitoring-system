# Digital4.ai Bee Monitoring System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-red.svg)](https://www.raspberrypi.org/)

A comprehensive IoT solution for modern beekeeping that combines AI-powered computer vision, environmental monitoring, and real-time analytics to provide actionable insights about bee colonies.

## 🚀 Live Demo

**Production System**: [https://y0h0i3c8jkgk.manus.space](https://y0h0i3c8jkgk.manus.space)

## 📋 Table of Contents

- [Features](#features)
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
- **AI-Powered Bee Detection**: Computer vision with 96% accuracy for live bee counting
- **Behavior Analysis**: Automatic classification of foraging, guarding, and swarming behaviors
- **Environmental Monitoring**: Temperature, humidity, and light level tracking
- **Health Assessment**: Colony health scoring with mite detection and wing condition analysis

### Advanced Analytics
- **Activity Patterns**: Daily and seasonal behavior analysis with trend visualization
- **Predictive Insights**: Weather impact forecasting and health trend predictions
- **Historical Data**: Comprehensive data retention with exportable analytics
- **Alert System**: Configurable thresholds with real-time notifications

### Professional Dashboard
- **Responsive Web Interface**: Modern React-based dashboard with real-time updates
- **Interactive Visualizations**: Dynamic charts and graphs using Recharts
- **Multi-Device Support**: Desktop, tablet, and mobile compatibility
- **Real-Time Updates**: Live data refresh every 5 seconds

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
- **Production Demo**: `https://y0h0i3c8jkgk.manus.space`

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
- **Production**: `https://y0h0i3c8jkgk.manus.space/api/bee`

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
cd api && python src/main.py

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
