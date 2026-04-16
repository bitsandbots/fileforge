#!/bin/bash
# Install systemd timer for FileForge scans
# Usage: bash install.sh

set -e

SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy templates, substituting user paths
sed "s|%u|$USER|g; s|%h|$HOME|g" "$SCRIPT_DIR/fileforge-scan.service" > "$SERVICE_DIR/fileforge-scan.service"
cp "$SCRIPT_DIR/fileforge-scan.timer" "$SERVICE_DIR/fileforge-scan.timer"

# Enable and start timer
systemctl --user daemon-reload
systemctl --user enable fileforge-scan.timer
systemctl --user start fileforge-scan.timer

echo "✓ FileForge scan timer installed and started"
systemctl --user status fileforge-scan.timer