#!/bin/bash
# ==================================================
#    CRYPTOSHIELD BACKGROUND DAEMON INSTALLER      
# ==================================================

echo "=================================================="
echo "    INSTALLING CRYPTOSHIELD AUTO-POPUP DAEMON     "
echo "=================================================="

BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
DAEMON_SCRIPT="$BIN_DIR/cryptoshield-daemon.py"
DESKTOP_ENTRY="$AUTOSTART_DIR/cryptoshield-daemon.desktop"

# Create directories if they don't exist
mkdir -p "$BIN_DIR"
mkdir -p "$AUTOSTART_DIR"

# 1. Write the Python daemon script
echo "Writing daemon background script to $DAEMON_SCRIPT..."
cat << 'EOF' > "$DAEMON_SCRIPT"
import os
import json
import subprocess
import time
import sys

USER = os.environ.get('USER', 'nishant')
active_pid = None
active_path = None
# Local path to the compiled Unlock executable
UNLOCK_EXE = f"/home/nishant/.gemini/antigravity/scratch/secure-usb-lock/dist/Unlock"

def get_vault_mountpoints():
    """Checks for any mounted removable USB devices that contain a secure vault."""
    try:
        # Run lsblk to list mountpoints of removable devices
        res = subprocess.run(
            ["lsblk", "-o", "NAME,RM,TYPE,MOUNTPOINT", "-J"],
            capture_output=True, text=True
        )
        data = json.loads(res.stdout)
        mountpoints = []
        for dev in data.get("blockdevices", []):
            is_removable = dev.get("rm", False)
            if is_removable:
                if "children" in dev:
                    for child in dev["children"]:
                        mount = child.get("mountpoint")
                        if mount and os.path.exists(mount):
                            mountpoints.append(mount)
                else:
                    mount = dev.get("mountpoint")
                    if mount and os.path.exists(mount):
                        mountpoints.append(mount)
                        
        # Check standard OS mount directories
        for base_dir in [f"/media/{USER}", f"/run/media/{USER}"]:
            if os.path.exists(base_dir):
                for d in os.listdir(base_dir):
                    full_path = os.path.join(base_dir, d)
                    if (os.path.ismount(full_path) or os.path.isdir(full_path)) and full_path not in mountpoints:
                        mountpoints.append(full_path)
                        
        # Filter for paths containing .secure_vault/vault.meta
        vaults = []
        for m in mountpoints:
            meta_path = os.path.join(m, ".secure_vault", "vault.meta")
            if os.path.exists(meta_path):
                vaults.append(m)
        return vaults
    except Exception:
        return []

try:
    while True:
        vaults = get_vault_mountpoints()
        
        if vaults:
            vault_path = vaults[0]
            if active_path != vault_path:
                active_path = vault_path
                # Only launch if not already running
                if active_pid is None or active_pid.poll() is not None:
                    env = os.environ.copy()
                    if "DISPLAY" not in env:
                        env["DISPLAY"] = ":0"
                    home_dir = os.path.expanduser(f"~{USER}")
                    xauth_path = os.path.join(home_dir, ".Xauthority")
                    if os.path.exists(xauth_path):
                        env["XAUTHORITY"] = xauth_path
                    
                    # Run the compiled local executable or python script
                    if os.path.exists(UNLOCK_EXE):
                        active_pid = subprocess.Popen([UNLOCK_EXE], env=env)
                    else:
                        active_pid = subprocess.Popen(
                            ["python3", "main.py"],
                            cwd="/home/nishant/.gemini/antigravity/scratch/secure-usb-lock",
                            env=env
                        )
        else:
            # USB ejected or no vault present
            if active_path is not None:
                active_path = None
                if active_pid is not None and active_pid.poll() is None:
                    active_pid.terminate()
                    active_pid = None
                    
        time.sleep(1.5)
except KeyboardInterrupt:
    sys.exit(0)
EOF

chmod +x "$DAEMON_SCRIPT"

# 2. Write the Autostart Desktop Entry
echo "Creating login autostart entry at $DESKTOP_ENTRY..."
cat << EOF > "$DESKTOP_ENTRY"
[Desktop Entry]
Type=Application
Exec=python3 $DAEMON_SCRIPT
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=CryptoShield USB Daemon
Comment=Listens for secure USB insertions and pops up unlock screen
EOF

chmod +x "$DESKTOP_ENTRY"

# 3. Start the daemon right now in the background
pkill -f "cryptoshield-daemon.py" 2>/dev/null
nohup python3 "$DAEMON_SCRIPT" >/dev/null 2>&1 &

echo "=================================================="
echo "[SUCCESS] Autostart daemon installed and started!"
echo "Any secured USB drive inserted will now automatically"
echo "trigger the Face & PIN authentication GUI."
echo "=================================================="
