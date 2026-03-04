#!/usr/bin/env bash
# ============================================================
# Build script for KLOC Count Tool
# Builds portable executables for Windows (.exe) and macOS (.app)
# Requires: pip install pyinstaller
# ============================================================

set -euo pipefail

APP_NAME="KlocCount"
ENTRY="app.py"
ICON_OPT=""

echo "================================="
echo " KLOC Count Tool — Build Script"
echo "================================="
echo ""

# Check pyinstaller
if ! command -v pyinstaller &>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Detect OS
OS="$(uname -s)"
case "$OS" in
    MINGW*|MSYS*|CYGWIN*|Windows*)
        PLATFORM="windows"
        ;;
    Darwin*)
        PLATFORM="macos"
        ;;
    *)
        PLATFORM="linux"
        ;;
esac

echo "Platform: $PLATFORM"
echo "Building $APP_NAME..."
echo ""

if [ "$PLATFORM" = "macos" ]; then
    pyinstaller \
        --onefile \
        --windowed \
        --name "$APP_NAME" \
        --hidden-import=tkcalendar \
        --hidden-import=babel.numbers \
        --collect-data tkcalendar \
        "$ENTRY"

    echo ""
    echo "✓ Build complete!"
    echo "  App: dist/$APP_NAME.app"
    echo ""
    echo "To create a DMG (optional):"
    echo "  brew install create-dmg"
    echo "  create-dmg --volname '$APP_NAME' '$APP_NAME.dmg' dist/$APP_NAME.app"

else
    pyinstaller \
        --onefile \
        --windowed \
        --name "$APP_NAME" \
        --hidden-import=tkcalendar \
        --hidden-import=babel.numbers \
        --collect-data tkcalendar \
        "$ENTRY"

    echo ""
    echo "✓ Build complete!"
    echo "  Executable: dist/$APP_NAME.exe"
fi

echo ""
echo "Note: The target machine must have 'git' and 'cloc' installed in PATH."
