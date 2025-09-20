#!/bin/bash

# Digital4.ai Bee Monitoring System - Raspberry Pi Deployment Script
# One-command deployment to Raspberry Pi

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/douggy81/bee-monitoring-system.git"
BRANCH="main"
PI_USER="pi"
PI_HOST=""
INSTALL_DIR="/opt/bee-monitoring"

# Logging functions
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

# Display usage
usage() {
    echo "Usage: $0 [OPTIONS] PI_HOST"
    echo ""
    echo "Deploy Digital4.ai Bee Monitoring System to Raspberry Pi"
    echo ""
    echo "Arguments:"
    echo "  PI_HOST                 Raspberry Pi hostname or IP address"
    echo ""
    echo "Options:"
    echo "  -u, --user USER         SSH username (default: pi)"
    echo "  -b, --branch BRANCH     Git branch to deploy (default: main)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.1.100"
    echo "  $0 -u ubuntu raspberrypi.local"
    echo "  $0 --branch development 10.0.0.50"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--user)
            PI_USER="$2"
            shift 2
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            error "Unknown option $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "$PI_HOST" ]; then
                PI_HOST="$1"
            else
                error "Multiple hosts specified"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$PI_HOST" ]; then
    error "Raspberry Pi host not specified"
    usage
    exit 1
fi

# Test SSH connection
test_ssh_connection() {
    log "Testing SSH connection to $PI_USER@$PI_HOST..."
    
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$PI_USER@$PI_HOST" exit 2>/dev/null; then
        error "Cannot connect to $PI_USER@$PI_HOST"
        info "Please ensure:"
        info "  1. SSH is enabled on the Raspberry Pi"
        info "  2. SSH keys are set up or password authentication is enabled"
        info "  3. The hostname/IP address is correct"
        info "  4. The username is correct (try 'pi' or 'ubuntu')"
        exit 1
    fi
    
    log "SSH connection successful"
}

# Deploy to Raspberry Pi
deploy_to_pi() {
    log "Starting deployment to $PI_USER@$PI_HOST..."
    
    # Create deployment script
    cat > /tmp/deploy_bee_monitoring.sh << 'EOF'
#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}" >&2; }
warning() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
info() { echo -e "${BLUE}[INFO] $1${NC}"; }

REPO_URL="$1"
BRANCH="$2"
INSTALL_DIR="/opt/bee-monitoring"

log "Deploying Digital4.ai Bee Monitoring System..."
log "Repository: $REPO_URL"
log "Branch: $BRANCH"
log "Install Directory: $INSTALL_DIR"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

# Update system
log "Updating system packages..."
apt update && apt upgrade -y

# Install git if not present
if ! command -v git >/dev/null 2>&1; then
    log "Installing git..."
    apt install -y git
fi

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    log "Updating existing installation..."
    cd "$INSTALL_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    log "Cloning repository..."
    git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

# Make setup script executable
chmod +x "$INSTALL_DIR/scripts/setup.sh"

# Run setup script
log "Running automated setup..."
"$INSTALL_DIR/scripts/setup.sh"

log "Deployment completed successfully!"
log "Access the dashboard at: http://$(hostname -I | awk '{print $1}'):5000"
EOF

    # Copy and execute deployment script
    scp /tmp/deploy_bee_monitoring.sh "$PI_USER@$PI_HOST:/tmp/"
    
    log "Executing deployment on Raspberry Pi..."
    ssh "$PI_USER@$PI_HOST" "sudo bash /tmp/deploy_bee_monitoring.sh '$REPO_URL' '$BRANCH'"
    
    # Cleanup
    rm /tmp/deploy_bee_monitoring.sh
    ssh "$PI_USER@$PI_HOST" "rm /tmp/deploy_bee_monitoring.sh"
    
    log "Deployment completed successfully!"
}

# Get Raspberry Pi IP for dashboard access
get_pi_info() {
    log "Getting Raspberry Pi information..."
    
    local pi_ip=$(ssh "$PI_USER@$PI_HOST" "hostname -I | awk '{print \$1}'")
    local pi_hostname=$(ssh "$PI_USER@$PI_HOST" "hostname")
    
    info "Raspberry Pi Information:"
    echo "  Hostname: $pi_hostname"
    echo "  IP Address: $pi_ip"
    echo "  Dashboard URL: http://$pi_ip:5000"
    echo "  API Health Check: http://$pi_ip:5000/api/bee/health"
    echo ""
    info "Service Management Commands:"
    echo "  Check Status: ssh $PI_USER@$PI_HOST 'sudo systemctl status bee-monitoring bee-api'"
    echo "  View Logs: ssh $PI_USER@$PI_HOST 'sudo journalctl -u bee-monitoring -f'"
    echo "  Restart Services: ssh $PI_USER@$PI_HOST 'sudo systemctl restart bee-monitoring bee-api'"
    echo ""
    info "OTA Update Commands:"
    echo "  Manual Update: ssh $PI_USER@$PI_HOST 'sudo /opt/bee-monitoring/scripts/ota-update.sh'"
    echo "  Check for Updates: ssh $PI_USER@$PI_HOST 'sudo /opt/bee-monitoring/scripts/ota-update.sh --check-only'"
}

# Main deployment process
main() {
    log "Digital4.ai Bee Monitoring System - Raspberry Pi Deployment"
    log "Target: $PI_USER@$PI_HOST"
    log "Branch: $BRANCH"
    echo ""
    
    test_ssh_connection
    deploy_to_pi
    get_pi_info
    
    log "Deployment process completed!"
    warning "Remember to reboot the Raspberry Pi to ensure all hardware interfaces are enabled:"
    echo "  ssh $PI_USER@$PI_HOST 'sudo reboot'"
}

# Run main function
main "$@"
