import os
import shutil
import tempfile
from encryptor import USBEncryptor

def run_integration_test():
    print("==================================================")
    print("      CRYPTOSHIELD INTEGRATION WORKFLOW TEST      ")
    print("==================================================")

    # 1. Setup mock USB directory
    usb_dir = tempfile.mkdtemp(prefix="mock_usb_")
    print(f"1. Created mock USB drive mountpoint: {usb_dir}")

    # Create original files
    file1_path = os.path.join(usb_dir, "photo.jpg")
    file1_content = b"Fake JPEG Photo Data"
    with open(file1_path, "wb") as f:
        f.write(file1_content)

    doc_dir = os.path.join(usb_dir, "documents")
    os.makedirs(doc_dir)
    file2_path = os.path.join(doc_dir, "notes.txt")
    file2_content = b"Important confidential note contents!"
    with open(file2_path, "wb") as f:
        f.write(file2_content)

    print("   Created original files on mock USB:")
    print(f"     - {os.path.relpath(file1_path, usb_dir)} (size: {len(file1_content)} bytes)")
    print(f"     - {os.path.relpath(file2_path, usb_dir)} (size: {len(file2_content)} bytes)")

    # 2. Lock & Encrypt the USB drive
    encryptor = USBEncryptor(iterations=1000) # Fast KDF for testing
    pin = "1234"
    label = "MySecureUSB"
    
    print(f"\n2. Calling encryptor.lock_drive() with PIN '{pin}' and label '{label}'...")
    success, msg = encryptor.lock_drive(usb_dir, pin, label)
    if not success:
        print(f"[FAILED] lock_drive failed: {msg}")
        return False
    print(f"   Success: {msg}")

    # Verify original files are gone
    print("\n3. Verifying files on mock USB root after locking:")
    root_contents = os.listdir(usb_dir)
    print(f"   USB Root Contents: {root_contents}")
    
    # We expect original files to be deleted
    if os.path.exists(file1_path) or os.path.exists(file2_path):
        print("[FAILED] Original files were not deleted!")
        return False
    print("   ✓ Original plaintext files successfully deleted.")

    # We expect the Unlock launcher to be copied
    launcher_exists = "Unlock" in root_contents or "Unlock.sh" in root_contents
    if not launcher_exists:
        print("[FAILED] Unlock launcher was not copied to USB root!")
        return False
    print("   ✓ Unlock launcher successfully copied to USB root.")

    # We expect the hidden .secure_vault directory to exist
    vault_dir = os.path.join(usb_dir, ".secure_vault")
    if not os.path.exists(vault_dir):
        print("[FAILED] .secure_vault directory was not created!")
        return False
    print("   ✓ Hidden .secure_vault directory successfully created.")

    # 3. Authenticate and load index
    print("\n4. Authenticating and loading vault key/index...")
    try:
        key = encryptor.get_vault_key(usb_dir, pin)
        index = encryptor.load_index(usb_dir, key)
        files_dict = index.get("files", {})
        print(f"   Successfully decrypted index. Found {len(files_dict)} files:")
        for path, info in files_dict.items():
            print(f"     - {path} -> secure ID: {info['id']} (size: {info['size']} bytes)")
        
        if "photo.jpg" not in files_dict or "documents/notes.txt" not in files_dict:
            print("[FAILED] Decrypted index does not contain the original files!")
            return False
        print("   ✓ Index file mapping verified.")
    except Exception as e:
        print(f"[FAILED] Authentication/index decryption failed: {e}")
        return False

    # 4. Add a new file to the vault
    print("\n5. Encrypting and adding a new file 'extra.txt' to the vault...")
    local_extra_file = os.path.join(tempfile.gettempdir(), "temp_extra.txt")
    extra_content = b"This is an extra file added after initialization."
    with open(local_extra_file, "wb") as f:
        f.write(extra_content)
        
    success_add = encryptor.add_file_to_vault(usb_dir, key, local_extra_file, "extra.txt")
    os.remove(local_extra_file)
    if not success_add:
        print("[FAILED] Failed to add file to vault!")
        return False
    
    # Reload index
    index = encryptor.load_index(usb_dir, key)
    files_dict = index.get("files", {})
    if "extra.txt" not in files_dict:
        print("[FAILED] New file was not found in the reloaded index!")
        return False
    print("   ✓ Successfully added file 'extra.txt' to the vault.")

    # 5. Extract files to a destination directory
    extract_dir = tempfile.mkdtemp(prefix="mock_extract_")
    print(f"\n6. Extracting files to restoration folder: {extract_dir}")
    
    for rel_path, info in files_dict.items():
        dest_path = os.path.join(extract_dir, rel_path)
        # Ensure directories exist
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        success_ext = encryptor.extract_file_from_vault(usb_dir, key, info["id"], dest_path)
        if not success_ext:
            print(f"[FAILED] Failed to extract {rel_path}!")
            return False
            
    # Verify contents
    with open(os.path.join(extract_dir, "photo.jpg"), "rb") as f:
        assert f.read() == file1_content
    with open(os.path.join(extract_dir, "documents", "notes.txt"), "rb") as f:
        assert f.read() == file2_content
    with open(os.path.join(extract_dir, "extra.txt"), "rb") as f:
        assert f.read() == extra_content
        
    print("   ✓ Extracted files successfully verified. Contents match original files!")
    shutil.rmtree(extract_dir)

    # 6. Unprotect / Decrypt the USB drive
    print(f"\n7. Calling encryptor.unprotect_drive() to restore USB...")
    success_unprot, msg_unprot = encryptor.unprotect_drive(usb_dir, pin)
    if not success_unprot:
        print(f"[FAILED] unprotect_drive failed: {msg_unprot}")
        return False
    print(f"   Success: {msg_unprot}")

    # Verify everything is back to original
    print("\n8. Verifying USB root contents after unprotecting:")
    final_contents = os.listdir(usb_dir)
    print(f"   USB Root Contents: {final_contents}")
    
    if ".secure_vault" in final_contents:
        print("[FAILED] .secure_vault directory was not deleted!")
        return False
        
    if "Unlock" in final_contents or "Unlock.sh" in final_contents:
        print("[FAILED] Unlock launcher was not deleted from USB root!")
        return False
        
    # Check original files exist
    if not os.path.exists(file1_path) or not os.path.exists(file2_path):
        print("[FAILED] Original files were not restored to USB root!")
        return False
        
    # Check contents
    with open(file1_path, "rb") as f:
        assert f.read() == file1_content
    with open(file2_path, "rb") as f:
        assert f.read() == file2_content
        
    print("   ✓ All original files successfully restored in plaintext.")
    print("   ✓ Vault metadata and data directories deleted.")
    
    shutil.rmtree(usb_dir)
    print("\n==================================================")
    print("   ✓ INTEGRATION WORKFLOW COMPLETED SUCCESSFULLY! ")
    print("==================================================")
    return True

if __name__ == "__main__":
    run_integration_test()
