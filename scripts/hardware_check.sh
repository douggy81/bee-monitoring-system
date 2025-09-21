#!/bin/bash
# Digital4.ai - Bee Monitoring System
# Quick hardware check for Camera (rpicam) and Hailo AI HAT+ (PCIe)

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure Hailo logs are written to a writable directory
: "${HAILORT_LOG_DIR:=/tmp}"
export HAILORT_LOG_DIR

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERR]${NC} $1"; }

CAMERA_OK=0
HAILO_PCIE_OK=0
HAILO_RUNTIME_OK=0

# Camera check
if command -v rpicam-hello >/dev/null 2>&1; then
  if rpicam-hello --list-cameras >/tmp/rpicam_list.txt 2>&1; then
    ok "rpicam-hello detected cameras:" 
    cat /tmp/rpicam_list.txt | sed 's/^/    /'
    CAMERA_OK=1
  else
    warn "rpicam-hello present but could not list cameras (headless or no camera?)"
  fi
else
  err "rpicam-hello not found. Install with: sudo apt install -y rpicam-apps"
fi

# Hailo PCIe presence check
if command -v lspci >/dev/null 2>&1; then
  if lspci -nn | grep -Ei 'hailo|1e60' >/tmp/hailo_pcie.txt 2>&1; then
    ok "Hailo device detected on PCIe:"
    cat /tmp/hailo_pcie.txt | sed 's/^/    /'
    HAILO_PCIE_OK=1
  else
    warn "No Hailo device detected on PCIe (check power/PCIe enablement)."
  fi
else
  err "lspci not found. Install with: sudo apt install -y pciutils"
fi

# Hailo runtime check
if command -v hailortcli >/dev/null 2>&1; then
  if hailortcli --version >/tmp/hailo_ver.txt 2>&1; then
    ok "Hailo runtime installed: $(cat /tmp/hailo_ver.txt)"
    HAILO_RUNTIME_OK=1
    echo "Device info:"
    if hailortcli device-info >/tmp/hailo_dev.txt 2>&1; then
      cat /tmp/hailo_dev.txt | sed 's/^/    /'
    else
      # Fallback with sudo in case udev permissions require elevated access
      if sudo HAILORT_LOG_DIR=/tmp hailortcli device-info >/tmp/hailo_dev.txt 2>&1; then
        ok "hailortcli device-info (sudo) succeeded:"
        cat /tmp/hailo_dev.txt | sed 's/^/    /'
      else
        warn "hailortcli device-info failed; ensure device is initialized and firmware is loaded."
      fi
    fi
    echo "Identify via fw-control:"
    if hailortcli fw-control identify >/tmp/hailo_ident.txt 2>&1; then
      cat /tmp/hailo_ident.txt | sed 's/^/    /'
    else
      warn "hailortcli fw-control identify failed; verify driver/firmware versions and PCIe Gen 3 setting."
    fi
  else
    warn "hailortcli present but version check failed."
  fi
else
  warn "Hailo runtime not installed (hailortcli not found)."
  echo "Install HailoRT per docs: https://hailo.ai/developer-zone/"
fi

# Summary
echo
echo "Summary:"
[ "$CAMERA_OK" -eq 1 ] && ok "Camera: OK" || err "Camera: NOT OK"
[ "$HAILO_PCIE_OK" -eq 1 ] && ok "Hailo PCIe: OK" || warn "Hailo PCIe: NOT DETECTED"
[ "$HAILO_RUNTIME_OK" -eq 1 ] && ok "Hailo Runtime: OK" || warn "Hailo Runtime: NOT INSTALLED"

exit 0
