#!/usr/bin/env bash
# Run KLOC Count Tool
# Usage: bash run.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill any existing instance (cross-platform)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows: use wmic to find and kill python app.py processes
    tasklist //FI "IMAGENAME eq python.exe" 2>/dev/null | grep -q python && \
        wmic process where "commandline like '%app.py%' and name='python.exe'" call terminate >>/dev/null 2>&1 || true
    sleep 1
else
    # macOS/Linux
    pkill -f "python.*app.py" 2>/dev/null || true
    sleep 0.5
fi

echo "Starting KLOC Count Tool..."
python "$SCRIPT_DIR/app.py" &
echo "App started (PID: $!)"
