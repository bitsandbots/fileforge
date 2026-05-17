#!/bin/bash
# Install systemd user units for FileForge
# Usage: bash install.sh [--scan|--server|--all]
# Default: --all (installs both scan timer and web server service)

set -e

MODE="${1:---all}"
SERVICE_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$SERVICE_DIR"

copy_scan_files() {
    sed "s|%h|$HOME|g" "$SCRIPT_DIR/fileforge-scan.service" > "$SERVICE_DIR/fileforge-scan.service"
    cp "$SCRIPT_DIR/fileforge-scan.timer" "$SERVICE_DIR/fileforge-scan.timer"
}

copy_server_files() {
    sed "s|%h|$HOME|g" "$SCRIPT_DIR/fileforge-server.service" > "$SERVICE_DIR/fileforge-server.service"
}

enable_scan() {
    systemctl --user enable fileforge-scan.timer
    systemctl --user start fileforge-scan.timer
    echo "✓ fileforge-scan.timer installed and started"
}

enable_server() {
    systemctl --user enable fileforge-server.service
    systemctl --user start fileforge-server.service
    echo "✓ fileforge-server.service installed and started"
    echo "  Web UI: http://127.0.0.1:8082"
}

case "$MODE" in
    --scan)
        copy_scan_files
        systemctl --user daemon-reload
        enable_scan
        ;;
    --server)
        copy_server_files
        systemctl --user daemon-reload
        enable_server
        ;;
    --all)
        copy_scan_files
        copy_server_files
        systemctl --user daemon-reload
        enable_scan
        enable_server
        ;;
    -h|--help)
        echo "Usage: $0 [--scan|--server|--all]"
        echo "  --scan    Install daily scan timer only"
        echo "  --server  Install web UI server only"
        echo "  --all     Install both (default)"
        exit 0
        ;;
    *)
        echo "Usage: $0 [--scan|--server|--all]" >&2
        exit 1
        ;;
esac

echo
echo "Status:"
systemctl --user --no-pager status fileforge-scan.timer fileforge-server.service 2>/dev/null || true
