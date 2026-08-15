#!/bin/bash
# ==================================================
#          CRYPTOSHIELD SECURE VAULT LAUNCHER      
# ==================================================
# This script launches the decryptor interface from the USB root or hidden folder.

# Get current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo "      CRYPTOSHIELD // BIOMETRIC VAULT UNLOCKER    "
echo "=================================================="
echo "Launch directory: $DIR"

# Determine target directory context
if [ -f "main.py" ]; then
    CWD_DIR="$DIR"
elif [ -f ".cryptoshield/main.py" ]; then
    CWD_DIR="$DIR/.cryptoshield"
else
    echo "[ERROR] Security files are missing. Drive might be corrupted."
    read -p "Press Enter to exit..."
    exit 1
fi

# 1. Check Python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is required to run the unlocker but was not found."
    echo "Please install python3 on this host system."
    read -p "Press Enter to exit..."
    exit 1
fi

# 2. Setup virtual environment in /tmp (handles FAT32/exFAT symlink limits)
VENV_DIR="/tmp/cryptoshield_venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Initializing secure environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    echo "Downloading secure dependencies (OpenCV, Cryptography, Pillow)..."
    # Pip install using requirements file from CWD
    pip install -r "$CWD_DIR/requirements.txt"
else
    source "$VENV_DIR/bin/activate"
fi

# 3. Launch the Secure Vault UI from correct context
echo "Launching interface..."
cd "$CWD_DIR"
python3 main.py

# 4. Deactivate venv
deactivate
