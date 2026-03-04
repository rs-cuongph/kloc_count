#!/usr/bin/env bash
# Run KLOC Count Tool
# Usage: bash run.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill any existing instance
pkill -f "python.*app.py" 2>/dev/null || true

echo "Starting KLOC Count Tool..."
python "$SCRIPT_DIR/app.py" &
echo "App started (PID: $!)"
