# Digital4.ai Bee Monitoring System - Deployment Guide

## Overview

The Digital4.ai Bee Monitoring System is a comprehensive IoT solution that combines AI-powered computer vision, environmental monitoring, and real-time analytics to provide beekeepers with actionable insights about their colonies. This guide covers the complete deployment process for both hardware and software components.

## System Architecture

The system consists of three main components:

1. **Hardware Layer**: Raspberry Pi 5 with AI HAT+ and Camera Module 3
2. **Software Layer**: Python-based data processing and Flask API backend
3. **User Interface**: React-based web dashboard with real-time monitoring

## Hardware Requirements

### Core Components (Already Acquired)
- **Raspberry Pi 5 (8GB RAM)**: Main processing unit
- **256GB MicroSD Card**: Storage for OS and data
- **AI HAT+ (13 TOPS)**: Accelerated AI processing for computer vision
- **Camera Module 3**: High-resolution image capture

### Additional Components (Recommended)
- **Environmental Sensors**:
  - DHT22 (Temperature & Humidity)
  - BH1750 (Light Level)
  - DS18B20 (Temperature probe for hive monitoring)
- **Power Management**:
  - Solar panel (20W minimum)
  - Battery pack (10,000mAh minimum)
  - Power management HAT
- **Connectivity**:
  - 4G/LTE module for remote locations
  - WiFi antenna for improved signal
- **Enclosure**:
  - Weatherproof case (IP65 rated)
  - Mounting hardware for hive installation

## Software Installation

### 1. Raspberry Pi Setup

```bash
# Flash Raspberry Pi OS (64-bit) to SD card
# Enable SSH, I2C, and Camera in raspi-config

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install python3-pip python3-venv git -y

# Install system dependencies for AI processing
sudo apt install libopencv-dev python3-opencv -y
```

### 2. Clone and Setup the Monitoring System

```bash
# Clone the repository
git clone https://github.com/digital4ai/bee-monitoring-system.git
cd bee-monitoring-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Hardware Integration Setup

```bash
# Copy hardware integration files
cp hardware_integration.py /opt/bee-monitoring/
cp hardware_config.json /opt/bee-monitoring/
cp setup_current_hardware.py /opt/bee-monitoring/

# Make setup script executable
chmod +x /opt/bee-monitoring/setup_current_hardware.py

# Run hardware setup
python /opt/bee-monitoring/setup_current_hardware.py
```

### 4. Configure System Services

```bash
# Create systemd service for bee monitoring
sudo cp bee-monitoring.service /etc/systemd/system/
sudo systemctl enable bee-monitoring
sudo systemctl start bee-monitoring

# Create systemd service for API server
sudo cp bee-api.service /etc/systemd/system/
sudo systemctl enable bee-api
sudo systemctl start bee-api
```

## Configuration

### Hardware Configuration

Edit `/opt/bee-monitoring/hardware_config.json`:

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

The Flask API is configured to serve both the backend API and the React frontend. Key endpoints include:

- **Health Check**: `/api/bee/health`
- **Current Status**: `/api/bee/current-status`
- **Activity Data**: `/api/bee/activity-data`
- **Health Data**: `/api/bee/health-data`
- **Environmental Data**: `/api/bee/environmental-data`
- **Alerts**: `/api/bee/alerts`
- **Analytics**: `/api/bee/analytics/summary`

## Deployment Options

### Option 1: Local Network Deployment

For local network access, the system runs on the Raspberry Pi and can be accessed via its IP address:

```bash
# Start the API server
cd /opt/bee-monitoring/api
source venv/bin/activate
python src/main.py
```

Access the dashboard at: `http://[raspberry-pi-ip]:5000`

### Option 2: Cloud Deployment

For remote access, deploy the system to a cloud platform:

**Deployed System**: https://y0h0i3c8jkgk.manus.space

The cloud deployment includes:
- Full React dashboard with real-time monitoring
- Complete REST API for data access
- SQLite database for data storage
- CORS enabled for cross-origin requests

### Option 3: Hybrid Deployment

Recommended for production use:
- Hardware and data collection on Raspberry Pi
- API and dashboard deployed to cloud
- Data synchronization between local and cloud systems

## Features and Capabilities

### Real-Time Monitoring
- **Live bee counting** using AI-powered computer vision
- **Behavior analysis** with pattern recognition
- **Environmental monitoring** (temperature, humidity, light)
- **Health assessment** with mite detection and wing condition analysis

### Analytics and Insights
- **Activity patterns** throughout the day
- **Health trend analysis** over time
- **Behavioral indicators** (foraging, guarding, swarming risk)
- **Predictive analytics** for weather impact and health forecasting

### Alert System
- **Configurable thresholds** for various parameters
- **Real-time notifications** for critical events
- **Alert acknowledgment** and management
- **Historical alert tracking**

### Data Management
- **Automated data collection** at configurable intervals
- **Local storage** with cloud synchronization options
- **Data retention policies** with automatic cleanup
- **Export capabilities** for further analysis

## API Usage Examples

### Get Current System Status
```bash
curl https://y0h0i3c8jkgk.manus.space/api/bee/current-status
```

### Retrieve Activity Data
```bash
curl "https://y0h0i3c8jkgk.manus.space/api/bee/activity-data?hours=24&limit=100"
```

### Ingest New Data
```bash
curl -X POST https://y0h0i3c8jkgk.manus.space/api/bee/data/ingest \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## Maintenance and Troubleshooting

### Regular Maintenance Tasks

1. **System Updates**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   pip install --upgrade -r requirements.txt
   ```

2. **Data Cleanup**:
   ```bash
   python /opt/bee-monitoring/scripts/cleanup_old_data.py
   ```

3. **Log Monitoring**:
   ```bash
   sudo journalctl -u bee-monitoring -f
   sudo journalctl -u bee-api -f
   ```

### Common Issues and Solutions

**Camera Not Detected**:
- Ensure camera is properly connected
- Enable camera interface in `raspi-config`
- Check camera cable and connections

**AI Processing Slow**:
- Verify AI HAT+ is properly installed
- Check system temperature and throttling
- Reduce camera resolution or FPS if needed

**Network Connectivity Issues**:
- Check WiFi/Ethernet connection
- Verify firewall settings
- Test API endpoints manually

**High Storage Usage**:
- Enable automatic data cleanup
- Reduce data collection frequency
- Archive old data to external storage

## Performance Optimization

### Hardware Optimization
- **Overclocking**: Safely overclock Raspberry Pi for better performance
- **Cooling**: Ensure adequate cooling for sustained operation
- **Power Management**: Optimize power consumption for battery operation

### Software Optimization
- **Model Optimization**: Use quantized TensorFlow Lite models
- **Batch Processing**: Process multiple frames together
- **Caching**: Implement intelligent caching for frequently accessed data

## Security Considerations

### Network Security
- Change default passwords
- Enable SSH key authentication
- Configure firewall rules
- Use VPN for remote access

### Data Security
- Encrypt sensitive data at rest
- Implement API authentication
- Regular security updates
- Backup encryption keys

## Scaling and Extensions

### Multi-Hive Monitoring
- Deploy multiple Raspberry Pi units
- Centralized data aggregation
- Comparative analysis across hives

### Advanced Analytics
- Machine learning model training
- Seasonal pattern analysis
- Weather correlation studies
- Predictive maintenance

### Integration Options
- Weather API integration
- Beekeeping management software
- Mobile app development
- IoT platform integration

## Support and Documentation

### Technical Support
- **GitHub Repository**: [Digital4.ai Bee Monitoring](https://github.com/digital4ai/bee-monitoring)
- **Documentation**: Comprehensive API and hardware documentation
- **Community Forum**: User community and support

### Development Resources
- **API Documentation**: Complete REST API reference
- **Hardware Schematics**: Wiring diagrams and component specifications
- **Software Architecture**: Detailed system design documentation

## Conclusion

The Digital4.ai Bee Monitoring System provides a comprehensive solution for modern beekeeping, combining cutting-edge AI technology with practical monitoring capabilities. The system is designed to be scalable, maintainable, and extensible, making it suitable for both hobbyist beekeepers and commercial operations.

For additional support or custom development needs, contact the Digital4.ai development team.

---

**System Version**: 1.0.0  
**Last Updated**: September 19, 2025  
**Deployment URL**: https://y0h0i3c8jkgk.manus.space
