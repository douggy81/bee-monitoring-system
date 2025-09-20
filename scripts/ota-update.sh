#!/bin/bash

# Digital4.ai Bee Monitoring System - OTA Update Script
# Automated Over-The-Air updates from GitHub repository

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
BACKUP_DIR="$INSTALL_DIR/backups"
LOG_FILE="$INSTALL_DIR/logs/ota-update.log"
LOCK_FILE="/var/lock/bee-ota-update.lock"

# Logging functions
log() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

error() {
    local message="[ERROR] $1"
    echo -e "${RED}$message${NC}" >&2
    echo "$message" >> "$LOG_FILE"
}

warning() {
    local message="[WARNING] $1"
    echo -e "${YELLOW}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

info() {
    local message="[INFO] $1"
    echo -e "${BLUE}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

# Check if update is already running
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            error "Update already in progress (PID: $pid)"
            exit 1
        else
            warning "Stale lock file found, removing..."
            rm -f "$LOCK_FILE"
        fi
    fi
    
    # Create lock file
    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT
}

# Check if running as root or service user
check_permissions() {
    if [[ $EUID -ne 0 ]] && [[ $(whoami) != "$SERVICE_USER" ]]; then
        error "This script must be run as root or $SERVICE_USER user"
        exit 1
    fi
}

# Load OTA configuration
load_config() {
    local config_file="$INSTALL_DIR/config/ota_config.json"
    
    if [ -f "$config_file" ]; then
        # Parse JSON configuration (requires jq)
        if command -v jq >/dev/null 2>&1; then
            REPO_URL=$(jq -r '.repository // "https://github.com/douggy81/bee-monitoring-system.git"' "$config_file")
            BRANCH=$(jq -r '.branch // "main"' "$config_file")
            AUTO_UPDATE=$(jq -r '.auto_update // true' "$config_file")
            BACKUP_RETENTION=$(jq -r '.backup_retention // 5' "$config_file")
        else
            warning "jq not found, using default configuration"
        fi
    else
        warning "OTA config file not found, using defaults"
    fi
}

# Check for updates
check_for_updates() {
    log "Checking for updates from $REPO_URL (branch: $BRANCH)..."
    
    cd "$INSTALL_DIR/src"
    
    # Fetch latest changes
    sudo -u "$SERVICE_USER" git fetch origin "$BRANCH"
    
    # Get current and remote commit hashes
    local current_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse "origin/$BRANCH")
    
    if [ "$current_commit" = "$remote_commit" ]; then
        info "System is already up to date (commit: ${current_commit:0:8})"
        return 1
    else
        info "Update available:"
        info "  Current: ${current_commit:0:8}"
        info "  Remote:  ${remote_commit:0:8}"
        return 0
    fi
}

# Create backup
create_backup() {
    log "Creating system backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="backup_$timestamp"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$backup_path"
    
    # Backup source code
    cp -r "$INSTALL_DIR/src" "$backup_path/"
    
    # Backup configuration
    cp -r "$INSTALL_DIR/config" "$backup_path/"
    
    # Backup database
    cp "$INSTALL_DIR/data"/*.db "$backup_path/" 2>/dev/null || true
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "timestamp": "$timestamp",
    "commit": "$(cd "$INSTALL_DIR/src" && git rev-parse HEAD)",
    "branch": "$BRANCH",
    "created_by": "ota-update",
    "system_info": {
        "hostname": "$(hostname)",
        "kernel": "$(uname -r)",
        "uptime": "$(uptime -p)"
    }
}
EOF
    
    # Set proper ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$backup_path"
    
    log "Backup created: $backup_path"
    echo "$backup_path" > "$INSTALL_DIR/.last_backup"
}

# Cleanup old backups
cleanup_backups() {
    log "Cleaning up old backups (keeping $BACKUP_RETENTION)..."
    
    cd "$BACKUP_DIR"
    
    # Remove old backups, keeping only the specified number
    ls -1t backup_* 2>/dev/null | tail -n +$((BACKUP_RETENTION + 1)) | xargs -r rm -rf
    
    log "Backup cleanup completed"
}

# Stop services
stop_services() {
    log "Stopping services..."
    
    systemctl stop bee-monitoring.service || warning "Failed to stop bee-monitoring service"
    systemctl stop bee-api.service || warning "Failed to stop bee-api service"
    
    # Wait for services to stop
    sleep 3
    
    log "Services stopped"
}

# Start services
start_services() {
    log "Starting services..."
    
    systemctl start bee-monitoring.service
    systemctl start bee-api.service
    
    # Wait for services to start
    sleep 5
    
    log "Services started"
}

# Update source code
update_source() {
    log "Updating source code..."
    
    cd "$INSTALL_DIR/src"
    
    # Pull latest changes
    sudo -u "$SERVICE_USER" git pull origin "$BRANCH"
    
    # Update submodules if any
    sudo -u "$SERVICE_USER" git submodule update --init --recursive
    
    log "Source code updated successfully"
}

# Update Python dependencies
update_dependencies() {
    log "Updating Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Activate virtual environment and update dependencies
    sudo -u "$SERVICE_USER" bash -c "
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r src/requirements.txt --upgrade
    "
    
    log "Dependencies updated successfully"
}

# Update configuration files
update_config() {
    log "Updating configuration files..."
    
    # Check for new configuration files
    local src_config="$INSTALL_DIR/src/config"
    local dest_config="$INSTALL_DIR/config"
    
    # Update configuration files that don't exist
    for config_file in "$src_config"/*.json; do
        local filename=$(basename "$config_file")
        if [ ! -f "$dest_config/$filename" ]; then
            info "Adding new configuration file: $filename"
            cp "$config_file" "$dest_config/"
            chown "$SERVICE_USER:$SERVICE_USER" "$dest_config/$filename"
        fi
    done
    
    log "Configuration files updated"
}

# Update systemd services
update_services() {
    log "Updating systemd services..."
    
    # Copy updated service files
    cp "$INSTALL_DIR/src/config/systemd"/*.service /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    log "Systemd services updated"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd "$INSTALL_DIR"
    
    # Run migration script if it exists
    if [ -f "src/scripts/migrate_database.py" ]; then
        sudo -u "$SERVICE_USER" bash -c "
            source venv/bin/activate
            python src/scripts/migrate_database.py
        "
        log "Database migrations completed"
    else
        info "No database migrations found"
    fi
}

# Verify update
verify_update() {
    log "Verifying update..."
    
    # Check if services are running
    local services_ok=true
    
    if ! systemctl is-active --quiet bee-monitoring.service; then
        error "bee-monitoring service is not running"
        services_ok=false
    fi
    
    if ! systemctl is-active --quiet bee-api.service; then
        error "bee-api service is not running"
        services_ok=false
    fi
    
    # Check API health
    local api_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/bee/health || echo "000")
    
    if [ "$api_health" != "200" ]; then
        error "API health check failed (HTTP $api_health)"
        services_ok=false
    fi
    
    if [ "$services_ok" = true ]; then
        log "Update verification successful"
        return 0
    else
        error "Update verification failed"
        return 1
    fi
}

# Rollback to previous version
rollback() {
    error "Rolling back to previous version..."
    
    local last_backup=$(cat "$INSTALL_DIR/.last_backup" 2>/dev/null || echo "")
    
    if [ -z "$last_backup" ] || [ ! -d "$last_backup" ]; then
        error "No backup found for rollback"
        return 1
    fi
    
    # Stop services
    stop_services
    
    # Restore from backup
    rm -rf "$INSTALL_DIR/src"
    cp -r "$last_backup/src" "$INSTALL_DIR/"
    cp -r "$last_backup/config"/* "$INSTALL_DIR/config/"
    
    # Set proper ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/src" "$INSTALL_DIR/config"
    
    # Update systemd services
    update_services
    
    # Start services
    start_services
    
    # Verify rollback
    if verify_update; then
        log "Rollback completed successfully"
        return 0
    else
        error "Rollback verification failed"
        return 1
    fi
}

# Send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Log notification
    if [ "$status" = "success" ]; then
        log "UPDATE SUCCESS: $message"
    else
        error "UPDATE FAILED: $message"
    fi
    
    # Send webhook notification if configured
    local webhook_url=$(jq -r '.webhook_url // empty' "$INSTALL_DIR/config/ota_config.json" 2>/dev/null || echo "")
    
    if [ -n "$webhook_url" ]; then
        curl -s -X POST "$webhook_url" \
            -H "Content-Type: application/json" \
            -d "{\"status\":\"$status\",\"message\":\"$message\",\"hostname\":\"$(hostname)\",\"timestamp\":\"$(date -Iseconds)\"}" \
            >/dev/null 2>&1 || warning "Failed to send webhook notification"
    fi
}

# Main update function
main() {
    log "Starting OTA update process..."
    
    check_lock
    check_permissions
    load_config
    
    # Check for updates
    if ! check_for_updates; then
        log "No updates available"
        exit 0
    fi
    
    # Create backup
    create_backup
    cleanup_backups
    
    # Perform update
    stop_services
    
    if update_source && update_dependencies && update_config && update_services && run_migrations; then
        start_services
        
        # Verify update
        if verify_update; then
            local commit=$(cd "$INSTALL_DIR/src" && git rev-parse --short HEAD)
            send_notification "success" "Update completed successfully (commit: $commit)"
            log "OTA update completed successfully"
        else
            # Rollback on verification failure
            if rollback; then
                send_notification "warning" "Update failed verification, rollback successful"
            else
                send_notification "error" "Update failed and rollback failed"
                error "CRITICAL: Update and rollback both failed!"
                exit 1
            fi
        fi
    else
        error "Update process failed"
        start_services  # Try to start services anyway
        
        if rollback; then
            send_notification "warning" "Update failed, rollback successful"
        else
            send_notification "error" "Update failed and rollback failed"
            error "CRITICAL: Update and rollback both failed!"
            exit 1
        fi
    fi
}

# Handle command line arguments
case "${1:-}" in
    --check-only)
        load_config
        if check_for_updates; then
            echo "Updates available"
            exit 0
        else
            echo "No updates available"
            exit 1
        fi
        ;;
    --force)
        log "Forcing update (skipping update check)..."
        main
        ;;
    --rollback)
        rollback
        ;;
    *)
        main
        ;;
esac
