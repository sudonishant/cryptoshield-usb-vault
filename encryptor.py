import os
import json
import uuid
import shutil
import tempfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.backends import default_backend

class USBEncryptor:
    def __init__(self, iterations=100_000):
        self.iterations = iterations
        self.temp_dirs = []

    def derive_key(self, pin: str, salt: bytes) -> bytes:
        """Derives a strong 256-bit AES key from the numeric PIN using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=SHA256(),
            length=32, # 256 bits
            salt=salt,
            iterations=self.iterations,
            backend=default_backend()
        )
        return kdf.derive(pin.encode('utf-8'))

    def encrypt_data(self, data: bytes, key: bytes) -> bytes:
        """Encrypts data using AES-256-GCM and prepends a random 12-byte nonce."""
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_data(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypts data using AES-256-GCM (expects 12-byte nonce prepended)."""
        if len(encrypted_data) < 12:
            raise ValueError("Encrypted data is too short")
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def is_vault_initialized(self, usb_path: str) -> bool:
        """Checks if a secure vault is initialized on the USB drive."""
        meta_path = os.path.join(usb_path, ".secure_vault", "vault.meta")
        return os.path.exists(meta_path)

    def get_vault_label(self, usb_path: str) -> str:
        """Gets the vault label from the metadata."""
        meta_path = os.path.join(usb_path, ".secure_vault", "vault.meta")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                return meta.get("label", "CryptoShield Vault")
            except Exception:
                pass
        return "CryptoShield Vault"

    def initialize_vault(self, usb_path: str, pin: str, label: str) -> bytes:
        """Initializes a new vault on the USB drive. Returns the derived key."""
        vault_dir = os.path.join(usb_path, ".secure_vault")
        data_dir = os.path.join(vault_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        salt = os.urandom(16)
        key = self.derive_key(pin, salt)

        # Write metadata
        meta = {
            "salt": salt.hex(),
            "iterations": self.iterations,
            "label": label
        }
        meta_path = os.path.join(vault_dir, "vault.meta")
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        # Write empty index
        index_data = {"files": {}, "label": label}
        encrypted_index = self.encrypt_data(json.dumps(index_data).encode("utf-8"), key)
        index_path = os.path.join(vault_dir, "index.enc")
        with open(index_path, "wb") as f:
            f.write(encrypted_index)

        # On Windows, try to hide the directory
        if os.name == 'nt':
            import subprocess
            subprocess.run(["attrib", "+H", vault_dir], capture_output=True)

        # Copy launcher binary/script if available
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            launcher_src = os.path.join(app_dir, "dist", "Unlock")
            if os.path.exists(launcher_src):
                shutil.copy2(launcher_src, os.path.join(usb_path, "Unlock"))
                try:
                    os.chmod(os.path.join(usb_path, "Unlock"), 0o755)
                except Exception:
                    pass
            else:
                shell_launcher = os.path.join(app_dir, "Unlock.sh")
                if os.path.exists(shell_launcher):
                    shutil.copy2(shell_launcher, os.path.join(usb_path, "Unlock.sh"))
                    try:
                        os.chmod(os.path.join(usb_path, "Unlock.sh"), 0o755)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Failed to copy launcher to USB root: {e}")

        return key

    def get_vault_key(self, usb_path: str, pin: str) -> bytes:
        """Derives and returns the vault key from PIN if correct, else raises exception."""
        meta_path = os.path.join(usb_path, ".secure_vault", "vault.meta")
        if not os.path.exists(meta_path):
            raise FileNotFoundError("Vault metadata not found")

        with open(meta_path, "r") as f:
            meta = json.load(f)

        salt = bytes.fromhex(meta["salt"])
        iterations = meta.get("iterations", self.iterations)
        
        # Derive key
        kdf = PBKDF2HMAC(
            algorithm=SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        key = kdf.derive(pin.encode('utf-8'))
        
        # Verify key by trying to decrypt index
        index_path = os.path.join(usb_path, ".secure_vault", "index.enc")
        if os.path.exists(index_path):
            with open(index_path, "rb") as f:
                encrypted_index = f.read()
            # This will raise an InvalidTag error if the key is incorrect
            self.decrypt_data(encrypted_index, key)
            
        return key

    def load_index(self, usb_path: str, key: bytes) -> dict:
        """Decrypts and loads the vault index."""
        index_path = os.path.join(usb_path, ".secure_vault", "index.enc")
        if not os.path.exists(index_path):
            return {"files": {}}
        with open(index_path, "rb") as f:
            encrypted_index = f.read()
        decrypted = self.decrypt_data(encrypted_index, key)
        return json.loads(decrypted.decode("utf-8"))

    def save_index(self, usb_path: str, key: bytes, index: dict):
        """Encrypts and saves the vault index."""
        index_path = os.path.join(usb_path, ".secure_vault", "index.enc")
        encrypted = self.encrypt_data(json.dumps(index).encode("utf-8"), key)
        with open(index_path, "wb") as f:
            f.write(encrypted)

    def secure_shred(self, path: str):
        """Securely shreds a file by overwriting with random data/zeros before removal."""
        if os.path.exists(path) and os.path.isfile(path):
            try:
                size = os.path.getsize(path)
                with open(path, "r+b") as f:
                    f.seek(0)
                    f.write(os.urandom(size))
                    f.flush()
                    os.fsync(f.fileno())
                    f.seek(0)
                    f.write(b'\x00' * size)
                    f.flush()
                    os.fsync(f.fileno())
                with open(path, "w") as f:
                    f.truncate(0)
                os.remove(path)
            except Exception:
                try:
                    os.remove(path)
                except Exception:
                    pass

    def lock_drive(self, usb_path: str, pin: str, label: str) -> tuple[bool, str]:
        """
        Locks the USB drive. Encrypts all existing files on the drive,
        moves them to the hidden .secure_vault/data folder, and creates index.enc.
        """
        try:
            # 1. Initialize vault if not done
            if not self.is_vault_initialized(usb_path):
                key = self.initialize_vault(usb_path, pin, label)
            else:
                key = self.get_vault_key(usb_path, pin)

            index = self.load_index(usb_path, key)
            vault_dir = os.path.join(usb_path, ".secure_vault")
            data_dir = os.path.join(vault_dir, "data")
            
            # List of names of executable launchers to ignore
            launchers = ["Unlock", "Unlock.exe", "Unlock.sh", "build_binary.sh", "install_daemon.sh"]

            # 2. Scan and encrypt all files
            for root, dirs, files in os.walk(usb_path):
                # Ignore .secure_vault folder
                if ".secure_vault" in root.split(os.sep):
                    continue
                # Ignore hidden directories (starting with .)
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    # Skip launchers
                    if file in launchers:
                        continue
                    
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, usb_path)
                    
                    # Generate a unique ID for this file
                    file_id = str(uuid.uuid4())
                    dest_path = os.path.join(data_dir, file_id)
                    
                    # Read and encrypt
                    with open(full_path, "rb") as f:
                        plaintext = f.read()
                    
                    encrypted_data = self.encrypt_data(plaintext, key)
                    with open(dest_path, "wb") as f:
                        f.write(encrypted_data)
                    
                    # Add to index
                    index["files"][rel_path] = {
                        "id": file_id,
                        "size": len(plaintext)
                    }
                    
                    # Shred original file
                    self.secure_shred(full_path)

            # 3. Save index
            self.save_index(usb_path, key, index)

            # 4. Delete empty folders (excluding .secure_vault)
            for root, dirs, files in os.walk(usb_path, topdown=False):
                if ".secure_vault" in root.split(os.sep):
                    continue
                if root == usb_path:
                    continue
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                except Exception:
                    pass

            return True, "Lock successful."
        except Exception as e:
            return False, f"Lock failed: {e}"

    def add_file_to_vault(self, usb_path: str, key: bytes, local_src_path: str, relative_dest_path: str) -> bool:
        """Encrypts and adds a local file to the vault on the USB drive."""
        try:
            vault_dir = os.path.join(usb_path, ".secure_vault")
            data_dir = os.path.join(vault_dir, "data")
            
            # Read plaintext
            with open(local_src_path, "rb") as f:
                plaintext = f.read()
                
            file_id = str(uuid.uuid4())
            dest_path = os.path.join(data_dir, file_id)
            
            # Encrypt and save
            encrypted_data = self.encrypt_data(plaintext, key)
            with open(dest_path, "wb") as f:
                f.write(encrypted_data)
                
            # Update index
            index = self.load_index(usb_path, key)
            index["files"][relative_dest_path] = {
                "id": file_id,
                "size": len(plaintext)
            }
            self.save_index(usb_path, key, index)
            return True
        except Exception as e:
            print(f"Failed to add file to vault: {e}")
            return False

    def extract_file_from_vault(self, usb_path: str, key: bytes, file_id: str, local_dest_path: str) -> bool:
        """Decrypts a file from the vault to a local destination."""
        try:
            encrypted_path = os.path.join(usb_path, ".secure_vault", "data", file_id)
            if not os.path.exists(encrypted_path):
                return False
                
            with open(encrypted_path, "rb") as f:
                encrypted_data = f.read()
                
            decrypted = self.decrypt_data(encrypted_data, key)
            
            # Ensure parent directories exist
            os.makedirs(os.path.dirname(local_dest_path), exist_ok=True)
            with open(local_dest_path, "wb") as f:
                f.write(decrypted)
            return True
        except Exception as e:
            print(f"Failed to extract file: {e}")
            return False

    def delete_file_from_vault(self, usb_path: str, key: bytes, relative_path: str) -> bool:
        """Deletes a file from the vault index and shreds its encrypted chunk."""
        try:
            index = self.load_index(usb_path, key)
            if relative_path not in index["files"]:
                return False
                
            file_info = index["files"][relative_path]
            file_id = file_info["id"]
            
            # Shred the encrypted file
            encrypted_path = os.path.join(usb_path, ".secure_vault", "data", file_id)
            self.secure_shred(encrypted_path)
            
            # Update index
            del index["files"][relative_path]
            self.save_index(usb_path, key, index)
            return True
        except Exception as e:
            print(f"Failed to delete file from vault: {e}")
            return False

    def decrypt_temp_file(self, usb_path: str, key: bytes, file_id: str, original_name: str) -> str:
        """Decrypts a file to a secure temporary directory and returns the path."""
        try:
            encrypted_path = os.path.join(usb_path, ".secure_vault", "data", file_id)
            if not os.path.exists(encrypted_path):
                raise FileNotFoundError("Encrypted file not found")
                
            with open(encrypted_path, "rb") as f:
                encrypted_data = f.read()
                
            decrypted = self.decrypt_data(encrypted_data, key)
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="cryptoshield_")
            self.temp_dirs.append(temp_dir)
            
            temp_file_path = os.path.join(temp_dir, original_name)
            with open(temp_file_path, "wb") as f:
                f.write(decrypted)
                
            return temp_file_path
        except Exception as e:
            print(f"Temp decryption failed: {e}")
            raise

    def cleanup_temp_files(self):
        """Shreds and removes all temporary directories/files created during the session."""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            self.secure_shred(os.path.join(root, file))
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Failed to clean up temp dir {temp_dir}: {e}")
        self.temp_dirs = []

    def unprotect_drive(self, usb_path: str, pin: str) -> tuple[bool, str]:
        """
        Decrypts all vault contents back to their original paths on the USB root,
        shreds/deletes `.secure_vault` folder, and restores normal drive state.
        """
        try:
            if not self.is_vault_initialized(usb_path):
                return False, "Vault is not initialized on this drive."

            key = self.get_vault_key(usb_path, pin)
            index = self.load_index(usb_path, key)
            
            # 1. Decrypt all files back to USB root
            for rel_path, file_info in index["files"].items():
                file_id = file_info["id"]
                dest_path = os.path.join(usb_path, rel_path)
                
                # Extract
                success = self.extract_file_from_vault(usb_path, key, file_id, dest_path)
                if not success:
                    return False, f"Failed to decrypt file: {rel_path}"

            # 2. Shred all encrypted chunks and index/metadata
            vault_dir = os.path.join(usb_path, ".secure_vault")
            for root, dirs, files in os.walk(vault_dir):
                for file in files:
                    self.secure_shred(os.path.join(root, file))
            
            # Delete directory tree
            shutil.rmtree(vault_dir)

            # Delete launcher files from USB root if they exist
            launchers = ["Unlock", "Unlock.exe", "Unlock.sh"]
            for launcher in launchers:
                launcher_path = os.path.join(usb_path, launcher)
                if os.path.exists(launcher_path):
                    try:
                        self.secure_shred(launcher_path)
                    except Exception:
                        try:
                            os.remove(launcher_path)
                        except Exception:
                            pass
            
            return True, "Vault successfully removed. USB is unprotected."
        except Exception as e:
            return False, f"Unprotect failed: {e}"
