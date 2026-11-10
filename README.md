# CryptoShield USB Secure Vault

CryptoShield is a local Python/Tkinter prototype that puts a password-derived encrypted vault inside a mounted removable drive. It can enroll a face with OpenCV, detect removable Linux volumes, move files into the vault, open decrypted temporary copies, extract files, and delete vault entries.

It is **not a secure USB device, a hardware-backed key store, or a production security product**. The host computer, its Python environment, the webcam, the USB controller, and the operating system all remain part of the trusted computing base. Read the limitations before placing sensitive data in a vault.

## What is implemented

- AES-GCM encryption for vault index and file contents. Each encrypted value has a random 12-byte nonce prepended to it.
- A 256-bit key derived from the user-entered PIN with PBKDF2-HMAC-SHA256. A vault stores its random salt and PBKDF2 iteration count in `.secure_vault/vault.meta`.
- A hidden `.secure_vault/` directory containing encrypted file blobs, an encrypted index, metadata, and (after enrollment) the OpenCV face model.
- Linux removable-drive discovery through `lsblk`, with fallback checks under `/media/$USER` and `/run/media/$USER`.
- A Tkinter UI for vault setup, face enrollment, unlock, add, extract, view, delete, lock, and permanent unprotect/restore operations.

Face recognition is an additional local signal, not a replacement for the PIN. The current controller explicitly keeps the vault locked after a face match and asks for the PIN. No PIN is persisted for automatic unlock; legacy `data/secure_pin.dat` files are removed when encountered.

## Requirements

- Linux with Python 3, Tkinter, `lsblk`, and a working webcam.
- A mounted removable drive with enough free space for encrypted copies during setup.
- Python packages listed in [`requirements.txt`](requirements.txt). `opencv-contrib-python` is required because the face recognizer uses OpenCV's LBPH module; the standard `opencv-python` package is not sufficient.

Tkinter may need to be installed through the operating system (for example, the `python3-tk` package on Debian/Ubuntu). The repository does not declare or install OS packages.

## Quick start

From a clone of this repository:

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

The application starts scanning for mounted removable drives. The setup flow is:

1. Select an unsecured removable drive.
2. Capture the face profile in the webcam view (the controller collects 30 samples; the recognizer requires at least 10).
3. Enter a PIN and vault label, then confirm the lock operation.
4. After initialization, select the vault and enter the PIN to unlock it. A face match alone does not unlock the vault.

The setup operation encrypts files found on the drive, moves encrypted blobs under `.secure_vault/data/`, writes an encrypted index, and removes the original files. Test this with disposable files and a disposable drive first. Keep an independent backup; a failed operation, damaged drive, wrong PIN, or corrupted index can make data unavailable.

### Optional launcher

`Unlock.sh` can be used from a checkout that contains `main.py`:

```bash
chmod +x Unlock.sh
./Unlock.sh
```

The launcher creates or reuses `/tmp/cryptoshield_venv` and installs the requirements there. It therefore needs network access the first time and writes outside the repository. It does not make the application portable to an arbitrary computer. The script's `.cryptoshield/main.py` branch is retained for the USB-layout convention, but this repository does not include that layout by default.

## Architecture

```text
main.py
  ├─ CryptoshieldApp: drive watcher, UI state, PIN flow, vault actions
  ├─ USBFaceAuth (face_auth.py): Haar detection + LBPH enrollment/verification
  ├─ USBEncryptor (encryptor.py): PBKDF2, AES-GCM, index, file lifecycle
  └─ SecurityGUI (gui.py): Tkinter setup/access/explorer screens

Mounted drive/
  ├─ .secure_vault/
  │   ├─ vault.meta       # JSON: salt, iteration count, label (not the PIN)
  │   ├─ index.enc        # AES-GCM encrypted path-to-blob index
  │   ├─ biometric.dat    # OpenCV face model copied during setup
  │   └─ data/<uuid>      # AES-GCM encrypted file blobs
  └─ Unlock.sh or Unlock  # optional launcher copied during initialization
```

The testable encryption API is in `USBEncryptor`. `initialize_vault()` creates metadata and an empty encrypted index; `lock_drive()` encrypts files already on the drive; `add_file_to_vault()` adds local files without deleting the source; `extract_file_from_vault()` writes plaintext to a chosen destination; and `unprotect_drive()` restores plaintext files and removes the vault. The GUI's “open” action decrypts a file into a temporary directory before passing it to the system viewer.

## Safe usage and privacy warnings

- Treat the PIN as the only vault credential and use a strong, unique value. The project does not provide PIN recovery.
- Face matching uses a normal 2D webcam, Haar detection, and LBPH. There is no liveness, depth, infrared, anti-spoofing, or multi-user access control. A photo/video or a poor match may defeat or block the biometric check.
- The enrolled face model is copied to the removable drive as `biometric.dat`. Anyone who can read the drive can obtain that biometric artifact; it is not an encrypted hardware template.
- Opening a file creates a plaintext temporary copy under the system temporary directory. The app attempts to shred temporary files when the session closes, but viewers, swap, backups, crash dumps, and filesystem/flash wear-leveling can retain data.
- The “secure shred” routine overwrites regular files before removal, but this is not a reliable guarantee on USB flash media or other wear-levelled storage.
- File contents are read into memory before encryption/decryption. Large files may consume substantial RAM, and interrupted locking should be treated as a possible data-loss event.
- A compromised host can capture the PIN, webcam frames, plaintext, or in-memory key. The software cannot protect against malware, a hostile OS, physical flash-chip extraction, or an untrusted USB port.
- The vault is a directory on an existing filesystem; it does not create a protected partition or unlock storage in hardware. It requires this code and its dependencies on the host.
- Verify the target drive carefully before confirming setup or unprotect. Unprotect permanently returns files to plaintext on the drive and deletes the vault configuration.

## Testing

The repository includes unit tests for key derivation, AES-GCM integrity, vault file lifecycle, face-recognizer behavior, and the no-local-PIN policy:

```bash
. venv/bin/activate
python -m unittest discover -v
```

The end-to-end mock-drive workflow is a separate script (not auto-discovered by `unittest`):

```bash
python test_workflow.py
```

It uses temporary directories and a reduced PBKDF2 iteration count for speed; that setting is only for the test. Tests do not prove the security of a real USB device, webcam, host, filesystem, or deployment.

## Files and generated data

- `data/` is created beside `main.py` at runtime for local application state. The current code deliberately does not store a PIN there.
- `venv/`, `/tmp/cryptoshield_venv`, `build/`, `dist/`, and `__pycache__/` are local/generated artifacts.
- `build_binary.sh` is an optional PyInstaller helper. Inspect it before use: it installs PyInstaller into the active environment and removes `build/`, `dist/`, and `Unlock.spec` as part of its cleanup.
- `install_daemon.sh` writes a login autostart daemon under `$HOME/.local/bin` and `$HOME/.config/autostart`, starts a background process, and contains machine-specific paths. It is not required for the normal application flow and is not a portable installer.

## Project purpose and limitations

This project is useful as an educational demonstration of authenticated encryption, a local vault index, removable-drive detection, and the gap between a software prototype and a tamper-resistant USB security product. It should not be presented as equivalent to a FIPS-certified device, a secure element, full-disk encryption, or a production biometric access system. Hardware-backed key storage, liveness detection, recovery/rollback design, secure update delivery, and a threat model for the host and flash controller would all be needed for a real security product.
