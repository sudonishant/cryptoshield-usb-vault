#!/bin/bash
# ==================================================
#       CRYPTOSHIELD STANDALONE BINARY BUILDER      
# ==================================================

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo "      COMPILING CRYPTOSHIELD SECURE VAULT        "
echo "=================================================="

# 1. Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[ERROR] Virtual environment 'venv' not found. Please setup requirements first."
    exit 1
fi

# 2. Ensure PyInstaller is installed
if ! pip show pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# 3. Clean previous builds
echo "Cleaning old build artifacts..."
rm -rf build dist Unlock.spec

# 4. Compile main.py into a single binary
# We bundle cv2, cryptography, PIL, tkinter, and local files into a single binary
echo "Running PyInstaller compiler..."
pyinstaller --onefile --windowed --name Unlock main.py

# 5. Check output
if [ -f "dist/Unlock" ]; then
    echo "=================================================="
    echo "[SUCCESS] Standalone executable compiled!"
    echo "Binary location: dist/Unlock"
    echo "Size: $(du -sh dist/Unlock | cut -f1)"
    echo "=================================================="
else
    echo "[ERROR] Compilation failed. Check build logs."
    exit 1
fi
