#!/bin/bash
# Setup passwordless SSH to Raspberry Pi
# This script will create SSH keys and configure them properly

set -e

PI_USER="digital4ai"
PI_HOST="192.168.68.66"
PI_ADDR="${PI_USER}@${PI_HOST}"

echo "=============================================="
echo "Passwordless SSH Setup for Raspberry Pi"
echo "=============================================="
echo ""
echo "Target: ${PI_ADDR}"
echo ""

# Step 1: Check if we already have keys
SSH_KEY="${HOME}/.ssh/id_ed25519"
SSH_PUB="${HOME}/.ssh/id_ed25519.pub"

if [ -f "$SSH_KEY" ]; then
    echo "Found existing SSH key: $SSH_KEY"
    read -p "Do you want to use the existing key? (y/N): " use_existing
    if [ "$use_existing" != "y" ] && [ "$use_existing" != "Y" ]; then
        echo "Creating a new key specifically for the Pi..."
        SSH_KEY="${HOME}/.ssh/id_rpi"
        SSH_PUB="${HOME}/.ssh/id_rpi.pub"
        
        if [ -f "$SSH_KEY" ]; then
            echo "Removing old Pi-specific key..."
            rm -f "$SSH_KEY" "$SSH_PUB"
        fi
        
        echo "Generating new Ed25519 key (no passphrase)..."
        ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "mac-to-rpi-${USER}"
        echo "✓ New key created: $SSH_KEY"
    fi
else
    echo "No SSH key found. Creating new Ed25519 key (no passphrase)..."
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "mac-to-rpi-${USER}"
    echo "✓ Key created: $SSH_KEY"
fi

echo ""
echo "Public key:"
cat "$SSH_PUB"
echo ""

# Step 2: Copy key to Pi (this will ask for password one last time)
echo "[1/4] Copying public key to Raspberry Pi..."
echo "You'll need to enter your Pi password ONE LAST TIME:"
echo ""

# Create .ssh directory on Pi if it doesn't exist
ssh "${PI_ADDR}" "mkdir -p ~/.ssh && chmod 700 ~/.ssh" || {
    echo "❌ Failed to create .ssh directory on Pi"
    exit 1
}

# Copy the public key
cat "$SSH_PUB" | ssh "${PI_ADDR}" "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys" || {
    echo "❌ Failed to copy public key"
    exit 1
}

echo "✓ Public key copied"
echo ""

# Step 3: Ensure proper permissions on Pi
echo "[2/4] Setting correct permissions on Pi..."
ssh "${PI_ADDR}" "chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys" || {
    echo "❌ Failed to set permissions"
    exit 1
}
echo "✓ Permissions set correctly"
echo ""

# Step 4: Configure local SSH config for easier connection
echo "[3/4] Configuring local SSH config..."

SSH_CONFIG="${HOME}/.ssh/config"
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

# Remove any existing Pi configuration
sed -i.bak '/^Host raspberry-pi$/,/^$/d' "$SSH_CONFIG" 2>/dev/null || true
sed -i.bak '/^Host rpi$/,/^$/d' "$SSH_CONFIG" 2>/dev/null || true

# Add new configuration
cat >> "$SSH_CONFIG" << EOF

# Raspberry Pi - Bee Monitoring System
Host rpi raspberry-pi
    HostName ${PI_HOST}
    User ${PI_USER}
    IdentityFile ${SSH_KEY}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF

echo "✓ SSH config updated"
echo ""

# Step 5: Test connection
echo "[4/4] Testing passwordless connection..."
echo ""

if ssh -o BatchMode=yes -o ConnectTimeout=5 "${PI_ADDR}" "echo 'Connection successful!'" 2>/dev/null; then
    echo "=============================================="
    echo "✓ SUCCESS! Passwordless SSH is working!"
    echo "=============================================="
    echo ""
    echo "You can now connect with:"
    echo "  ssh ${PI_ADDR}"
    echo "  ssh rpi              # Short alias"
    echo "  ssh raspberry-pi     # Descriptive alias"
    echo ""
    echo "No password needed! 🎉"
else
    echo "❌ Test failed. Trying with verbose output..."
    ssh -v "${PI_ADDR}" "echo 'Testing...'" || true
    echo ""
    echo "If you see 'Permission denied', check:"
    echo "1. Pi's SSH server allows key authentication"
    echo "2. File permissions are correct"
    echo "3. Try: ssh ${PI_ADDR} -v"
fi

echo ""
echo "Cleaning up backup files..."
rm -f "${SSH_CONFIG}.bak"

echo ""
echo "Setup complete!"
