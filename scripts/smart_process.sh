#!/bin/bash
################################################################################
# smart_process.sh - Intelligent Video Processing Wrapper
#
# Automatically manages NumPy versions for ByteTrack compatibility
# Handles both detection and tracking workflows seamlessly
#
# Usage:
#   ./smart_process.sh bytetrack INPUT OUTPUT [--backend cpu] [--fps 120]
#   ./smart_process.sh detect INPUT OUTPUT [--backend hailo] [--fps 30]
#
# Date: October 13, 2025
# Status: ACTIVE PRODUCTION
################################################################################

set -e  # Exit on error

COMMAND=$1

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_numpy_version() {
    python3 << EOF
import numpy as np
version = tuple(map(int, np.__version__.split('.')[:3]))
print(f"{version[0]}.{version[1]}.{version[2]}")
EOF
}

upgrade_numpy() {
    log_info "Upgrading NumPy for ByteTrack compatibility..."
    
    # Save current version
    CURRENT_NUMPY=$(check_numpy_version)
    log_info "Current NumPy: $CURRENT_NUMPY"
    
    # Upgrade (using sudo for system-wide install)
    sudo pip3 install --upgrade 'numpy>=1.25.2' --break-system-packages > /tmp/numpy_upgrade.log 2>&1
    
    NEW_NUMPY=$(check_numpy_version)
    log_success "NumPy upgraded to $NEW_NUMPY"
}

downgrade_numpy() {
    log_info "Restoring NumPy for Hailo compatibility..."
    
    # Downgrade to Hailo-compatible version (using sudo for system-wide)
    sudo pip3 install 'numpy==1.23.3' --break-system-packages > /tmp/numpy_downgrade.log 2>&1
    
    RESTORED_NUMPY=$(check_numpy_version)
    log_success "NumPy restored to $RESTORED_NUMPY"
}

# Check if we have required arguments
if [ -z "$COMMAND" ]; then
    log_error "Missing command!"
    echo ""
    echo "Usage:"
    echo "  $0 bytetrack INPUT OUTPUT [--backend cpu] [--fps 120]"
    echo "  $0 detect INPUT OUTPUT [--backend hailo] [--fps 30]"
    echo ""
    echo "Examples:"
    echo "  # ByteTrack processing (with automatic NumPy management)"
    echo "  $0 bytetrack input.mp4 output_tracked.mp4 --backend cpu --fps 120"
    echo ""
    echo "  # Detection only (Hailo - fast)"
    echo "  $0 detect input.mp4 output_detected.mp4 --backend hailo --fps 30"
    exit 1
fi

shift  # Remove command, keep rest of arguments

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."  # Go to project root

case $COMMAND in
    "bytetrack"|"track")
        log_info "Starting ByteTrack processing..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Check if tracking module exists
        if [ ! -d "tracking" ]; then
            log_error "ByteTrack tracking module not found!"
            log_info "Please deploy tracking module first"
            exit 1
        fi
        
        # Upgrade NumPy
        log_info "Step 1/3: Preparing environment..."
        upgrade_numpy
        
        # Run ByteTrack
        log_info "Step 2/3: Processing video with ByteTrack..."
        echo ""
        
        python3 scripts/process_bee_bytetrack_with_metadata.py "$@"
        EXIT_CODE=$?
        
        echo ""
        
        # Always restore NumPy, even if processing failed
        log_info "Step 3/3: Cleaning up..."
        downgrade_numpy
        
        # Check if processing succeeded
        if [ $EXIT_CODE -eq 0 ]; then
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_success "ByteTrack processing complete!"
            log_info "NumPy restored for Hailo compatibility"
        else
            log_error "ByteTrack processing failed (exit code: $EXIT_CODE)"
            log_warning "NumPy has been restored to Hailo-compatible version"
            exit $EXIT_CODE
        fi
        ;;
        
    "detect"|"detection")
        log_info "Starting detection processing..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Check NumPy version
        NUMPY_VERSION=$(check_numpy_version)
        log_info "NumPy version: $NUMPY_VERSION (Hailo-compatible)"
        
        # Run detection
        python3 scripts/process_video_with_health_metrics.py "$@"
        EXIT_CODE=$?
        
        echo ""
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_success "Detection processing complete!"
        else
            log_error "Detection processing failed (exit code: $EXIT_CODE)"
            exit $EXIT_CODE
        fi
        ;;
        
    "check"|"status")
        # Check system status
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "System Status Check"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        # Check NumPy
        NUMPY_VERSION=$(check_numpy_version)
        echo "📦 NumPy: $NUMPY_VERSION"
        
        if [[ "$NUMPY_VERSION" == "1.23.3" ]]; then
            echo "   ✅ Hailo-compatible (detection ready)"
            echo "   ⚠️  ByteTrack requires upgrade (use smart_process.sh)"
        elif [[ "$NUMPY_VERSION" > "1.25.0" ]]; then
            echo "   ✅ ByteTrack-compatible (tracking ready)"
            echo "   ⚠️  Hailo requires downgrade (automatic after tracking)"
        fi
        
        echo ""
        
        # Check models
        if [ -f "../models/yolo11m_bee_best.hef" ]; then
            echo "📊 Hailo Model: ✅ Found"
        else
            echo "📊 Hailo Model: ❌ Missing"
        fi
        
        if [ -f "../models/yolo11m_bee_best.onnx" ]; then
            echo "📊 ONNX Model: ✅ Found"
        else
            echo "📊 ONNX Model: ❌ Missing"
        fi
        
        echo ""
        
        # Check tracking
        if [ -d "tracking" ]; then
            echo "🔍 ByteTrack: ✅ Installed"
        else
            echo "🔍 ByteTrack: ❌ Not installed"
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ;;
        
    "help"|"--help"|"-h")
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Smart Processing Wrapper - Help"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "COMMANDS:"
        echo ""
        echo "  bytetrack INPUT OUTPUT [OPTIONS]"
        echo "    Process video with ByteTrack tracking"
        echo "    Automatically manages NumPy versions"
        echo "    Use --backend cpu (required for ByteTrack)"
        echo ""
        echo "  detect INPUT OUTPUT [OPTIONS]"
        echo "    Process video with detection only (no tracking)"
        echo "    Use --backend hailo (fast) or --backend cpu"
        echo ""
        echo "  check"
        echo "    Check system status and dependencies"
        echo ""
        echo "OPTIONS:"
        echo "  --backend {hailo|cpu}   Choose inference backend"
        echo "  --fps NUMBER            Override video FPS"
        echo ""
        echo "EXAMPLES:"
        echo ""
        echo "  # Track bees with ByteTrack (CPU + NumPy auto-managed)"
        echo "  $0 bytetrack input.mp4 tracked.mp4 --backend cpu --fps 120"
        echo ""
        echo "  # Detect bees only (Hailo - fast)"
        echo "  $0 detect input.mp4 detected.mp4 --backend hailo --fps 30"
        echo ""
        echo "  # Check system status"
        echo "  $0 check"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ;;
        
    *)
        log_error "Unknown command: $COMMAND"
        echo ""
        echo "Available commands: bytetrack, detect, check, help"
        echo "Run '$0 help' for more information"
        exit 1
        ;;
esac

exit 0
