#!/bin/bash

# Digital4.ai Bee Monitoring System - Automated Setup Script
# This script sets up the complete bee monitoring system on Raspberry Pi

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/bee-monitoring"
SERVICE_USER="bee-monitor"
REPO_URL="https://github.com/douggy81/bee-monitoring-system.git"
BRANCH="main"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if running on Raspberry Pi
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        warning "This script is optimized for Raspberry Pi. Continuing anyway..."
    fi
}

# Update system packages
update_system() {
    log "Updating system packages..."
    apt update && apt upgrade -y
    log "System packages updated successfully"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Core packages
    apt install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        nginx \
        sqlite3 \
        curl \
        wget \
        htop \
        vim \
        screen \
        supervisor \
        pciutils \
        jq
    
    # OpenCV and camera dependencies
    apt install -y \
        libopencv-dev \
        python3-opencv \
        libcamera-dev \
        rpicam-apps \
        python3-picamera2
    
    # I2C and GPIO tools
    apt install -y \
        i2c-tools \
        python3-smbus \
        python3-rpi.gpio

    # NPU dependencies (Hailo runtime, driver, post-processing, rpicam stages)
    # This meta-package installs Hailo driver/firmware, HailoRT middleware, Tappas core libs,
    # and rpicam-apps Hailo post-processing stages.
    apt install -y hailo-all || warning "hailo-all not available from current apt sources; install HailoRT per vendor docs"
    
    log "System dependencies installed successfully"
}

# Enable PCIe Gen 3.0 (recommended for best NPU performance)
enable_pcie_gen3() {
    local cfg="/boot/firmware/config.txt"
    log "Ensuring PCIe Gen 3.0 is enabled (dtparam=pciex1_gen=3)"
    if [ -f "$cfg" ]; then
        if grep -q "^dtparam=pciex1_gen=3" "$cfg"; then
            info "PCIe Gen 3.0 already enabled in $cfg"
        else
            echo "dtparam=pciex1_gen=3" >> "$cfg"
            log "Appended dtparam=pciex1_gen=3 to $cfg (reboot required)"
        fi
    else
        warning "$cfg not found; skipping PCIe Gen 3.0 enablement"
    fi
}

# Check for Hailo runtime (AI HAT+) and advise installation if missing
check_hailo_runtime() {
    info "Checking Hailo runtime (hailortcli)..."
    if command -v hailortcli >/dev/null 2>&1; then
        hailortcli --version || true
    else
        warning "Hailo runtime not installed (hailortcli not found)."
        echo "Refer to Hailo AI kit documentation to install HailoRT and firmware:"
        echo "  https://hailo.ai/developer-zone/"
        echo "After installing, verify with: hailortcli device-info"
    fi
}

# Enable required interfaces
enable_interfaces() {
    log "Enabling camera and I2C interfaces..."
    
    # Enable camera
    if ! grep -q "^camera_auto_detect=1" /boot/firmware/config.txt; then
        echo "camera_auto_detect=1" >> /boot/firmware/config.txt
    fi
    
    # Enable I2C
    if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt; then
        echo "dtparam=i2c_arm=on" >> /boot/firmware/config.txt
    fi
    
    # Enable SPI (if needed)
    if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt; then
        echo "dtparam=spi=on" >> /boot/firmware/config.txt
    fi
    
    log "Interfaces enabled (reboot required to take effect)"
}

# Create service user
create_service_user() {
    log "Creating service user: $SERVICE_USER"
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
        usermod -a -G video,i2c,spi,gpio "$SERVICE_USER"
        log "Service user created successfully"
    else
        info "Service user already exists"
    fi
}

# Create installation directory
create_install_dir() {
    log "Creating installation directory: $INSTALL_DIR"
    
    mkdir -p "$INSTALL_DIR"/{data,logs,backups,models,config}
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    
    log "Installation directory created successfully"
}

# Clone or update repository
setup_repository() {
    log "Setting up repository..."
    
    if [ -d "$INSTALL_DIR/src" ]; then
        info "Repository already exists, updating..."
        cd "$INSTALL_DIR/src"
        sudo -u "$SERVICE_USER" git pull origin "$BRANCH"
    else
        info "Cloning repository..."
        sudo -u "$SERVICE_USER" git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR/src"
    fi
    
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/src"
    log "Repository setup completed"
}

# Setup Python environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    sudo -u "$SERVICE_USER" python3 -m venv venv
    
    # Activate and install dependencies
    sudo -u "$SERVICE_USER" bash -c "
        source venv/bin/activate
        pip install --upgrade pip setuptools wheel
        # Filter out packages that should be installed from apt or are heavy/problematic on Pi
        sed -E '/^(opencv-python|picamera2|RPi\\.GPIO|tensorflow)==/d' src/requirements.txt > /tmp/requirements.filtered.txt
        pip install -r /tmp/requirements.filtered.txt
    "
    
    log "Python environment setup completed"
}

# Setup database
setup_database() {
    log "Setting up database..."
    
    cd "$INSTALL_DIR"
    
    # Initialize database
    sudo -u "$SERVICE_USER" bash -c "
        source venv/bin/activate
        python src/scripts/init_database.py
    "
    
    # Set proper permissions
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/data"/*.db
    chmod 644 "$INSTALL_DIR/data"/*.db
    
    log "Database setup completed"
}

# Setup configuration files
setup_config() {
    log "Setting up configuration files..."
    
    # Copy default configurations
    cp "$INSTALL_DIR/src/config/hardware_config.json" "$INSTALL_DIR/config/"
    cp "$INSTALL_DIR/src/config/api_config.json" "$INSTALL_DIR/config/"
    cp "$INSTALL_DIR/src/config/ota_config.json" "$INSTALL_DIR/config/"
    
    # Set proper permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/config"
    chmod 644 "$INSTALL_DIR/config"/*.json
    
    log "Configuration files setup completed"
}

# Setup systemd services
setup_services() {
    log "Setting up systemd services..."
    
    # Copy service files
    cp "$INSTALL_DIR/src/config/systemd"/*.service /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable bee-monitoring.service
    systemctl enable bee-api.service
    systemctl enable bee-ota-updater.service
    
    log "Systemd services setup completed"
}

# Setup nginx
setup_nginx() {
    log "Setting up nginx reverse proxy..."
    
    # Copy nginx configuration
    cp "$INSTALL_DIR/src/config/nginx/bee-monitoring" /etc/nginx/sites-available/
    # Ensure rate limit zones are defined at http-level
    mkdir -p /etc/nginx/conf.d
    cp "$INSTALL_DIR/src/config/nginx/req_zones.conf" /etc/nginx/conf.d/req_zones.conf
    
    # Enable site
    ln -sf /etc/nginx/sites-available/bee-monitoring /etc/nginx/sites-enabled/
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    nginx -t
    
    # Enable and start nginx
    systemctl enable nginx
    systemctl restart nginx
    
    log "Nginx setup completed"
}

# Setup log rotation
setup_logrotate() {
    log "Setting up log rotation..."
    
    cat > /etc/logrotate.d/bee-monitoring << EOF
$INSTALL_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl reload bee-monitoring bee-api
    endscript
}
EOF
    
    log "Log rotation setup completed"
}

# Setup cron jobs
setup_cron() {
    log "Setting up cron jobs..."
    
    # Create cron job for system maintenance
    cat > /etc/cron.d/bee-monitoring << EOF
# Bee Monitoring System Maintenance
0 2 * * * $SERVICE_USER $INSTALL_DIR/scripts/maintenance.sh
0 */6 * * * $SERVICE_USER $INSTALL_DIR/scripts/backup-database.sh
*/15 * * * * $SERVICE_USER $INSTALL_DIR/scripts/health-check.sh
EOF
    
    log "Cron jobs setup completed"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start bee monitoring services
    systemctl start bee-monitoring.service
    systemctl start bee-api.service
    systemctl start bee-ota-updater.service
    
    # Check service status
    sleep 5
    
    if systemctl is-active --quiet bee-monitoring.service; then
        log "Bee monitoring service started successfully"
    else
        error "Failed to start bee monitoring service"
        systemctl status bee-monitoring.service
    fi
    
    if systemctl is-active --quiet bee-api.service; then
        log "Bee API service started successfully"
    else
        error "Failed to start bee API service"
        systemctl status bee-api.service
    fi
}

# Display system information
display_info() {
    log "Installation completed successfully!"
    echo
    info "System Information:"
    echo "  Installation Directory: $INSTALL_DIR"
    echo "  Service User: $SERVICE_USER"
    echo "  Configuration: $INSTALL_DIR/config/"
    echo "  Logs: $INSTALL_DIR/logs/"
    echo "  Data: $INSTALL_DIR/data/"
    echo
    info "Access Points:"
    echo "  Local Dashboard: http://$(hostname -I | awk '{print $1}'):5000"
    echo "  API Health Check: http://$(hostname -I | awk '{print $1}'):5000/api/bee/health"
    echo
    info "Service Management:"
    echo "  Check Status: sudo systemctl status bee-monitoring bee-api"
    echo "  View Logs: sudo journalctl -u bee-monitoring -f"
    echo "  Restart Services: sudo systemctl restart bee-monitoring bee-api"
    echo
    info "Configuration Files:"
    echo "  Hardware Config: $INSTALL_DIR/config/hardware_config.json"
    echo "  API Config: $INSTALL_DIR/config/api_config.json"
    echo "  OTA Config: $INSTALL_DIR/config/ota_config.json"
    echo
    warning "IMPORTANT: A reboot is recommended to ensure all hardware interfaces are properly enabled."
    echo "  Run: sudo reboot"
}

# Main installation function
main() {
    log "Starting Digital4.ai Bee Monitoring System installation..."
    
    check_root
    check_raspberry_pi
    
    update_system
    enable_pcie_gen3
    install_dependencies
    check_hailo_runtime
    enable_interfaces
    create_service_user
    create_install_dir
    setup_repository
    setup_python_env
    setup_database
    setup_config
    setup_services
    setup_nginx
    setup_logrotate
    setup_cron
    start_services
    
    display_info
}

# Run main function
main "$@"
