import os
import cv2
import threading
import time
import subprocess
import shutil
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
from face_auth import USBFaceAuth
from encryptor import USBEncryptor
from gui import SecurityGUI

class CryptoshieldApp:
    def __init__(self, root):
        self.root = root
        
        # Local configuration folder for PIN caching
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Core modules
        self.face_auth = USBFaceAuth(self.data_dir)
        self.encryptor = USBEncryptor()
        
        # GUI reference
        self.gui = SecurityGUI(self.root, self)
        
        # Controller state variables
        self.is_enrolling = False
        self.enroll_samples = []
        self.enroll_target_count = 30
        
        self.is_verifying = False
        self.face_match_status = False
        self.face_match_score = 999.0
        self.verification_success_time = 0
        
        # Drive detection states
        self.selected_drive_path = ""
        self.active_drives = []
        self.watcher_running = True
        self.is_auto_unlocking = False
        self.is_unlocking = False
        
        self.vault_key = None # Derived AES key in memory during unlocked session
        
        # Startup camera
        self.gui.start_camera()

        # Start USB Watcher daemon to track removable drives
        self.usb_watcher_thread = threading.Thread(target=self._usb_watcher_daemon, daemon=True)
        self.usb_watcher_thread.start()

    def list_removable_drives(self) -> list[dict]:
        """Queries lsblk to list removable USB drive mountpoints on Linux."""
        try:
            res = subprocess.run(
                ["lsblk", "-o", "NAME,SIZE,RM,TYPE,FSTYPE,MODEL,MOUNTPOINT", "-J"],
                capture_output=True, text=True, check=True
            )
            import json
            data = json.loads(res.stdout)
            drives = []
            
            for dev in data.get("blockdevices", []):
                is_removable = dev.get("rm", False)
                model = dev.get("model", "USB Disk")
                
                # Check if it's removable
                if is_removable:
                    is_system = False
                    if "children" in dev:
                        for child in dev["children"]:
                            mount = child.get("mountpoint")
                            if mount == "/" or mount == "[SWAP]" or (mount and mount.startswith("/boot")):
                                is_system = True
                                break
                    if is_system:
                        continue
                        
                    # Find mountpoints of children
                    if "children" in dev:
                        for child in dev["children"]:
                            mountpoint = child.get("mountpoint")
                            if mountpoint and os.path.exists(mountpoint):
                                drives.append({
                                    "path": mountpoint,
                                    "device": f"/dev/{child['name']}",
                                    "size": child.get("size", "Unknown"),
                                    "fstype": child.get("fstype", "Unknown"),
                                    "model": model,
                                    "label": os.path.basename(mountpoint)
                                })
                    else:
                        mountpoint = dev.get("mountpoint")
                        if mountpoint and os.path.exists(mountpoint):
                            drives.append({
                                "path": mountpoint,
                                "device": f"/dev/{dev['name']}",
                                "size": dev.get("size", "Unknown"),
                                "fstype": dev.get("fstype", "Unknown"),
                                "model": model,
                                "label": os.path.basename(mountpoint)
                            })
            
            # Fallback scanning of common mount directories
            username = os.environ.get("USER", "nishant")
            for base_dir in [f"/media/{username}", f"/run/media/{username}"]:
                if os.path.exists(base_dir):
                    for d in os.listdir(base_dir):
                        full_path = os.path.join(base_dir, d)
                        if os.path.ismount(full_path) or os.path.isdir(full_path):
                            # Avoid duplicates
                            if not any(d_info["path"] == full_path for d_info in drives):
                                drives.append({
                                    "path": full_path,
                                    "device": "Unknown",
                                    "size": "Unknown",
                                    "fstype": "Unknown",
                                    "model": "Removable Drive",
                                    "label": d
                                })
            return drives
        except Exception as e:
            print(f"Error listing removable drives: {e}")
            return []

    def _usb_watcher_daemon(self):
        """
        Actively checks for removable USB drives.
        Refreshes dropdown list and auto-triggers UI lock/unlock states.
        """
        last_paths = set()
        
        while self.watcher_running:
            drives = self.list_removable_drives()
            current_paths = {d["path"] for d in drives}
            
            # Detect changes in USB insertions/removals
            if current_paths != last_paths:
                self.active_drives = drives
                last_paths = current_paths
                
                # Sync GUI dropdown values on main thread safely
                self.root.after(100, lambda d=drives: self.handle_drives_change(d))
                
            time.sleep(1.5)

    def handle_drives_change(self, drives):
        """Triggers updates to dropdown selections and auto-tab switches."""
        self.gui.update_drives_dropdown(drives)
        self.gui.log(f"[USB WATCHER] Removable drives updated. Count: {len(drives)}")
        
        if drives:
            # Check the first detected drive
            first_drive = drives[0]
            self.selected_drive_path = first_drive["path"]
            
            # Load Biometric Model if present on USB
            biometric_path = os.path.join(self.selected_drive_path, ".secure_vault", "biometric.dat")
            if os.path.exists(biometric_path):
                try:
                    shutil.copy(biometric_path, self.face_auth.model_path)
                    self.face_auth.recognizer.read(self.face_auth.model_path)
                    self.face_auth.is_trained = True
                    self.gui.log("Biometric profile loaded from USB drive. Face ID active.")
                except Exception as e:
                    self.gui.log(f"[ERROR] Failed to load biometric model: {e}")
                    self.face_auth.is_trained = False
            else:
                self.face_auth.clear_model()
                
            # Check if vault is initialized
            if self.encryptor.is_vault_initialized(self.selected_drive_path):
                label = self.encryptor.get_vault_label(self.selected_drive_path)
                self.gui.log(f"[USB STATE] Encrypted Vault '{label}' detected on {self.selected_drive_path}. Switch to Access Controller.")
                self.gui.set_status(f"● VAULT DETECTED: {label}", "secure")
                self.gui.show_unlock_tab()
            else:
                self.gui.log(f"[USB STATE] Drive {self.selected_drive_path} has no vault. Switch to Setup Panel.")
                self.gui.set_status("● UNSECURED DRIVE DETECTED", "warning")
                self.gui.show_setup_tab()
        else:
            self.selected_drive_path = ""
            self.vault_key = None
            self.face_auth.clear_model()
            self.gui.log("[USB STATE] No removable USB drives detected.")
            self.gui.set_status("● SCANNING DRIVE", "warning")
            self.encryptor.cleanup_temp_files()
            self.gui.hide_vault_explorer()

    def select_device_by_path(self, path: str):
        """Selected by dropdown select callback."""
        self.selected_drive_path = path
        
        # Load Biometric Model if present on USB
        biometric_path = os.path.join(path, ".secure_vault", "biometric.dat")
        if os.path.exists(biometric_path):
            try:
                shutil.copy(biometric_path, self.face_auth.model_path)
                self.face_auth.recognizer.read(self.face_auth.model_path)
                self.face_auth.is_trained = True
                self.gui.log("Biometric profile loaded from selected USB drive. Face ID active.")
            except Exception as e:
                self.gui.log(f"[ERROR] Failed to load biometric model: {e}")
                self.face_auth.is_trained = False
        else:
            self.face_auth.clear_model()

        if self.encryptor.is_vault_initialized(path):
            label = self.encryptor.get_vault_label(path)
            self.gui.set_status(f"● VAULT DETECTED: {label}", "secure")
            self.gui.show_unlock_tab()
        else:
            self.gui.set_status("● UNSECURED DRIVE DETECTED", "warning")
            self.gui.show_setup_tab()

    def process_camera_frame(self, frame):
        """Biometric webcam alignment and score verification state."""
        face_img, bbox = self.face_auth.detect_face(frame)
        matching_info = {"match": False, "confidence": "", "verifying": False}
        
        if bbox is not None and face_img is not None:
            if self.is_enrolling:
                self.enroll_samples.append(face_img)
                count = len(self.enroll_samples)
                self.gui.enroll_status_lbl.config(
                    text=f"Scanning face: Captured {count}/{self.enroll_target_count} samples...",
                    fg=self.gui.accent_cyan
                )
                
                if count >= self.enroll_target_count:
                    self.is_enrolling = False
                    self.gui.log("Captured face profile. Training biometric signature...")
                    threading.Thread(target=self._train_enrollment_model).start()
            
            elif self.face_auth.is_trained:
                matching_info["verifying"] = True
                is_match, distance = self.face_auth.verify_face(face_img)
                matching_info["match"] = is_match
                matching_info["confidence"] = f"{int(100 - min(distance, 100))}%"
                
                if is_match:
                    self.face_match_status = True
                    self.face_match_score = distance
                    self.verification_success_time = time.time()
                    
                    # Auto-unlock if face is verified and local PIN is available
                    if not self.gui.is_unlocked:
                        self.root.after(100, self._auto_unlock_via_face)
                else:
                    if time.time() - self.verification_success_time > 3.0:
                        self.face_match_status = False
        
        if self.face_auth.is_trained:
            if self.face_match_status:
                self.gui.set_status("● FACE VERIFIED", "success")
            else:
                self.gui.set_status("● AWAITING FACE ID", "secure")
        else:
            self.gui.set_status("● NOT ENROLLED", "warning")
            
        return face_img, bbox, matching_info

    def _train_enrollment_model(self):
        success = self.face_auth.train_model(self.enroll_samples)
        self.enroll_samples.clear()
        
        if success:
            self.gui.log("[SUCCESS] Biometric face profile registered successfully.")
            self.gui.enroll_status_lbl.config(text="Enrollment Complete!", fg=self.gui.accent_green)
            messagebox.showinfo("Biometrics Setup", "Biometric face profile successfully saved!")
        else:
            self.gui.log("[ERROR] Biometric registration failed. Try again under better lighting.")
            self.enroll_status_lbl.config(text="Registration Failed. Try again.", fg=self.gui.accent_red)
        
        self.gui.btn_enroll_face.config(state="normal")

    def handle_face_enrollment(self, pin):
        if self.is_enrolling:
            return
        self.enroll_samples.clear()
        self.is_enrolling = True

    def handle_finalize_vault(self, pin, label="SecureUSB"):
        """Runs the vault encryption setup and encrypts the drive files."""
        if not self.face_auth.is_trained:
            messagebox.showerror("Setup Error", "Please complete step 3 (Biometric Face Scan) first!")
            return
        if not self.selected_drive_path:
            messagebox.showerror("Setup Error", "Please select a target USB directory!")
            return
            
        confirm = messagebox.askyesno(
            "Lock USB Confirmation",
            f"All existing files on drive {self.selected_drive_path} will be moved into the secure encrypted vault.\n\n"
            "Do you want to proceed?",
            icon='info'
        )
        if not confirm:
            return
            
        threading.Thread(target=self._format_vault_thread, args=(pin, label)).start()

    def _format_vault_thread(self, pin, label):
        self.gui.log(f"Encrypting and securing USB drive at {self.selected_drive_path}...")
        self.gui.btn_setup_vault.config(state="disabled")
        
        # 1. Lock drive (creates vault metadata, encrypts files, saves index)
        success, msg = self.encryptor.lock_drive(self.selected_drive_path, pin, label)
        
        if success:
            # 2. Copy the trained biometric model to the USB vault
            biometric_dest = os.path.join(self.selected_drive_path, ".secure_vault", "biometric.dat")
            try:
                shutil.copy(self.face_auth.model_path, biometric_dest)
            except Exception as e:
                self.gui.log(f"[WARNING] Failed to write biometric file to USB: {e}")

            # 3. Save the PIN locally for Face ID auto-unlock
            self._save_local_pin(pin)
            self.gui.log(f"[SUCCESS] {msg}")
            
            messagebox.showinfo("Vault Initialized", f"Vault '{label}' initialized and locked successfully!\nAll files are now encrypted.")
            self.gui.setup_pin_entry.delete(0, tk.END)
            # Sync states
            self.handle_drives_change(self.list_removable_drives())
        else:
            self.gui.log(f"[ERROR] {msg}")
            messagebox.showerror("Error", f"Failed to initialize vault: {msg}")
            
        self.gui.btn_setup_vault.config(state="normal")

    def handle_unlock_request(self, pin):
        """Verifies PIN, derives key, and opens the Secure File Explorer."""
        if self.is_unlocking:
            return
        if not self.selected_drive_path:
            messagebox.showerror("Error", "No USB drive selected!")
            return

        self.is_unlocking = True
        self.gui.log("Deriving AES keys and decrypting indices...")
        threading.Thread(target=self._unlock_vault_thread, args=(pin,)).start()

    def _unlock_vault_thread(self, pin):
        try:
            key = self.encryptor.get_vault_key(self.selected_drive_path, pin)
            self.vault_key = key
            
            # Load index files list
            index = self.encryptor.load_index(self.selected_drive_path, key)
            files_dict = index.get("files", {})
            
            self.is_auto_unlocking = False
            self.is_unlocking = False
            
            # Switch GUI to secure explorer
            self.gui.log(f"[SUCCESS] Vault decrypted. Loaded {len(files_dict)} files.")
            self.gui.show_vault_explorer(files_dict)
            
        except Exception as e:
            self.is_auto_unlocking = False
            self.is_unlocking = False
            self.gui.log(f"[AUTH FAILED] Incorrect PIN or corrupted index: {e}")
            self.gui.entered_pin = ""
            self.gui.pin_display_var.set("RETRY PIN")
            messagebox.showerror("Error", "Authentication Failed. Incorrect PIN.")

    def open_file_locally(self, filepath):
        """Cross-platform helper to open a file with the system default viewer."""
        try:
            if sys.platform.startswith('linux'):
                subprocess.Popen(['xdg-open', filepath])
            elif sys.platform.startswith('win'):
                os.startfile(filepath)
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', filepath])
        except Exception as e:
            self.gui.log(f"[ERROR] Failed to open temporary decrypted file: {e}")

    def handle_open_file(self, rel_path):
        """Decrypts a single file to a temp folder and opens it locally."""
        if not self.vault_key or not self.selected_drive_path:
            return
            
        try:
            index = self.encryptor.load_index(self.selected_drive_path, self.vault_key)
            file_info = index.get("files", {}).get(rel_path)
            if not file_info:
                messagebox.showerror("Error", f"File '{rel_path}' not found in index.")
                return
                
            file_id = file_info["id"]
            filename = os.path.basename(rel_path)
            
            # Decrypt to temp folder
            temp_path = self.encryptor.decrypt_temp_file(self.selected_drive_path, self.vault_key, file_id, filename)
            
            # Open file
            self.gui.log(f"[TEMP DECRYPT] File {filename} opened securely in default viewer.")
            self.open_file_locally(temp_path)
            
        except Exception as e:
            self.gui.log(f"[ERROR] Failed to open file: {e}")
            messagebox.showerror("Error", f"Failed to decrypt file: {e}")

    def add_file_click(self):
        """Triggered to encrypt and add local files to the vault."""
        if not self.vault_key or not self.selected_drive_path:
            return
            
        files = filedialog.askopenfilenames(title="Select Files to Encrypt & Add")
        if not files:
            return
            
        def run_add():
            success_count = 0
            for local_path in files:
                filename = os.path.basename(local_path)
                self.gui.log(f"Encrypting and adding file: {filename}...")
                success = self.encryptor.add_file_to_vault(self.selected_drive_path, self.vault_key, local_path, filename)
                if success:
                    success_count += 1
            
            self.gui.log(f"[SUCCESS] Encrypted and added {success_count}/{len(files)} files to vault.")
            
            # Refresh Treeview
            index = self.encryptor.load_index(self.selected_drive_path, self.vault_key)
            self.gui.populate_explorer(index.get("files", {}))
            
        threading.Thread(target=run_add).start()

    def add_folder_click(self):
        """Triggered to encrypt and add a local folder to the vault recursively."""
        if not self.vault_key or not self.selected_drive_path:
            return
            
        folder = filedialog.askdirectory(title="Select Folder to Encrypt & Add")
        if not folder:
            return
            
        def run_add_folder():
            folder_name = os.path.basename(folder)
            success_count = 0
            total_count = 0
            
            for root, dirs, files in os.walk(folder):
                for file in files:
                    total_count += 1
                    local_path = os.path.join(root, file)
                    rel_path = os.path.relpath(local_path, os.path.dirname(folder))
                    # Standardize relative paths to forward slashes
                    rel_path = rel_path.replace(os.sep, '/')
                    
                    self.gui.log(f"Encrypting and adding: {rel_path}...")
                    success = self.encryptor.add_file_to_vault(self.selected_drive_path, self.vault_key, local_path, rel_path)
                    if success:
                        success_count += 1
                        
            self.gui.log(f"[SUCCESS] Encrypted folder '{folder_name}'. Added {success_count}/{total_count} files.")
            
            # Refresh Treeview
            index = self.encryptor.load_index(self.selected_drive_path, self.vault_key)
            self.gui.populate_explorer(index.get("files", {}))
            
        threading.Thread(target=run_add_folder).start()

    def extract_selected_click(self):
        """Extracts and decrypts selected files/folders to a local destination."""
        if not self.vault_key or not self.selected_drive_path:
            return
            
        selected_items = self.gui.tree.selection()
        if not selected_items:
            messagebox.showinfo("Selection Required", "Please select files or folders to extract.")
            return
            
        dest_dir = filedialog.askdirectory(title="Select Extraction Destination Directory")
        if not dest_dir:
            return
            
        def run_extract():
            index = self.encryptor.load_index(self.selected_drive_path, self.vault_key)
            files_dict = index.get("files", {})
            
            self.gui.log(f"Extracting {len(selected_items)} selected items to {dest_dir}...")
            
            success_count = 0
            for item in selected_items:
                values = self.gui.tree.item(item, "values")
                if not values:
                    continue
                size, item_type, rel_path = values
                
                if item_type == "File":
                    # Decrypt single file
                    file_info = files_dict.get(rel_path)
                    if file_info:
                        dest_path = os.path.join(dest_dir, rel_path)
                        success = self.encryptor.extract_file_from_vault(self.selected_drive_path, self.vault_key, file_info["id"], dest_path)
                        if success:
                            success_count += 1
                else:
                    # Decrypt all files matching folder prefix
                    prefix = rel_path + "/"
                    for path, file_info in files_dict.items():
                        if path.startswith(prefix):
                            dest_path = os.path.join(dest_dir, path)
                            success = self.encryptor.extract_file_from_vault(self.selected_drive_path, self.vault_key, file_info["id"], dest_path)
                            if success:
                                success_count += 1
                                
            self.gui.log(f"[SUCCESS] Extracted successfully.")
            messagebox.showinfo("Extraction Complete", f"Successfully extracted decrypted files to:\n{dest_dir}")
            
        threading.Thread(target=run_extract).start()

    def delete_selected_click(self):
        """Shreds and deletes selected files/folders from the vault."""
        if not self.vault_key or not self.selected_drive_path:
            return
            
        selected_items = self.gui.tree.selection()
        if not selected_items:
            messagebox.showinfo("Selection Required", "Please select items to delete.")
            return
            
        confirm = messagebox.askyesno(
            "Shred & Delete Confirmation",
            "Are you sure you want to permanently delete and secure-shred the selected items?\n"
            "This action cannot be undone.",
            icon="warning"
        )
        if not confirm:
            return
            
        def run_delete():
            index = self.encryptor.load_index(self.selected_drive_path, self.vault_key)
            files_dict = index.get("files", {})
            
            for item in selected_items:
                values = self.gui.tree.item(item, "values")
                if not values:
                    continue
                size, item_type, rel_path = values
                
                if item_type == "File":
                    self.gui.log(f"Shredding file: {rel_path}...")
                    self.encryptor.delete_file_from_vault(self.selected_drive_path, self.vault_key, rel_path)
                else:
                    # Delete folder and all nested files matching prefix
                    prefix = rel_path + "/"
                    paths_to_delete = [p for p in files_dict.keys() if p.startswith(prefix)]
                    for path in paths_to_delete:
                        self.gui.log(f"Shredding file: {path}...")
                        self.encryptor.delete_file_from_vault(self.selected_drive_path, self.vault_key, path)
            
            self.gui.log("[SUCCESS] Selected items shredded and deleted from vault.")
            
            # Refresh Treeview
            updated_index = self.encryptor.load_index(self.selected_drive_path, self.vault_key)
            self.gui.populate_explorer(updated_index.get("files", {}))
            
        threading.Thread(target=run_delete).start()

    def lock_drive_click(self):
        """Locks the vault, clears AES key, shreds temp files, and returns to main screen."""
        self.gui.log("Securing vault and destroying session keys...")
        self.vault_key = None
        self.encryptor.cleanup_temp_files()
        self.gui.hide_vault_explorer()
        self.gui.log("[SUCCESS] Session ended. Drive is secure.")

    def unprotect_drive_click(self):
        """Decrypts all files back to USB root, deletes .secure_vault/ and restores standard USB state."""
        if not self.selected_drive_path:
            return
            
        pin = messagebox.askquestion(
            "Unprotect Pendrive Warning",
            "This action will permanently decrypt all secure vault files back to the USB root directory "
            "and delete the security configuration.\n\n"
            "Are you sure you want to permanently unprotect and restore this drive?",
            icon="warning"
        )
        if pin != 'yes':
            return
            
        # We need the user to input their PIN to decrypt the vault
        pin_dialog = tk.Toplevel(self.root)
        pin_dialog.title("Authentication Required")
        pin_dialog.geometry("300x120")
        pin_dialog.configure(bg=self.gui.bg_dark)
        pin_dialog.resizable(False, False)
        pin_dialog.transient(self.root)
        pin_dialog.grab_set()
        
        tk.Label(pin_dialog, text="Enter PIN to confirm decryption:", bg=self.gui.bg_dark, fg=self.gui.text_white).pack(pady=10)
        pin_entry = tk.Entry(pin_dialog, show="*", font=("Helvetica", 12), bg="#05050a", fg=self.gui.accent_amber, bd=0, justify="center")
        pin_entry.pack(pady=5)
        pin_entry.focus()
        
        def confirm_unprotect():
            entered_pin = pin_entry.get()
            pin_dialog.destroy()
            
            if not entered_pin:
                return
                
            self.gui.log("Running decryption and container cleanup...")
            
            def run_unprotect():
                success, msg = self.encryptor.unprotect_drive(self.selected_drive_path, entered_pin)
                if success:
                    # Clear local credentials
                    pin_file = os.path.join(self.data_dir, "secure_pin.dat")
                    if os.path.exists(pin_file):
                        try:
                            os.remove(pin_file)
                        except Exception:
                            pass
                    self.face_auth.clear_model()
                    self.vault_key = None
                    self.encryptor.cleanup_temp_files()
                    
                    self.gui.log(f"[SUCCESS] {msg}")
                    messagebox.showinfo("Restored", "USB drive successfully decrypted and restored to unprotected state.")
                    self.gui.hide_vault_explorer()
                    # Sync state
                    self.handle_drives_change(self.list_removable_drives())
                else:
                    self.gui.log(f"[ERROR] {msg}")
                    messagebox.showerror("Error", f"Unprotect failed: {msg}")
                    
            threading.Thread(target=run_unprotect).start()
            
        tk.Button(pin_dialog, text="CONFIRM", bg="#14332e", fg=self.gui.accent_green, bd=0, padx=10, command=confirm_unprotect).pack(pady=5)

    def on_closing(self):
        self.watcher_running = False
        self.gui.stop_camera()
        
        # Secure cleanup on exit
        if hasattr(self, 'encryptor'):
            self.encryptor.cleanup_temp_files()
            
        self.root.destroy()

    # ==========================================
    # LOCAL CREDENTIAL AUTO-UNLOCK UTILITIES
    # ==========================================

    def _save_local_pin(self, pin: str):
        """Saves the PIN locally, XOR-obfuscated to prevent plaintext visibility."""
        try:
            pin_file = os.path.join(self.data_dir, "secure_pin.dat")
            xor_key = 0xAA
            obfuscated = bytes([ord(c) ^ xor_key for c in pin])
            with open(pin_file, "wb") as f:
                f.write(obfuscated)
        except Exception as e:
            self.gui.log(f"[ERROR] Failed to save local PIN: {e}")

    def _get_local_pin(self) -> str:
        """Retrieves and de-obfuscates the locally saved PIN."""
        try:
            pin_file = os.path.join(self.data_dir, "secure_pin.dat")
            if os.path.exists(pin_file):
                with open(pin_file, "rb") as f:
                    obfuscated = f.read()
                xor_key = 0xAA
                pin = "".join([chr(b ^ xor_key) for b in obfuscated])
                return pin
        except Exception as e:
            self.gui.log(f"[ERROR] Failed to load local PIN: {e}")
        return ""

    def _auto_unlock_via_face(self):
        """Automatically unlocks the vault using the stored PIN when Face ID matches."""
        if self.gui.is_unlocked or not self.face_match_status or self.is_auto_unlocking:
            return
            
        # Only auto-unlock if a vault exists
        if not self.selected_drive_path or not self.encryptor.is_vault_initialized(self.selected_drive_path):
            return
            
        local_pin = self._get_local_pin()
        if local_pin:
            self.is_auto_unlocking = True
            self.gui.log("[BIO MATCH] Face verified. Auto-unlocking secure vault...")
            self.gui.entered_pin = local_pin
            self.gui.pin_display_var.set("● " * len(local_pin))
            threading.Thread(target=self._unlock_vault_thread, args=(local_pin,)).start()
        else:
            self.gui.log("[WARNING] Face verified but no local PIN found. Enter PIN manually.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoshieldApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
