import unittest
import os
import shutil
import tempfile
import numpy as np
from encryptor import USBEncryptor
from face_auth import USBFaceAuth

class TestContainerCryptography(unittest.TestCase):
    def setUp(self):
        self.encryptor = USBEncryptor(iterations=1000) # Fast KDF for testing
        self.temp_dir = tempfile.mkdtemp()
        self.pin = "123456"
        self.salt = b"CryptoShieldSalt"

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.encryptor.cleanup_temp_files()

    def test_key_derivation_determinism(self):
        """Confirms that key derivation is deterministic and distinct for different PINs."""
        key1 = self.encryptor.derive_key(self.pin, self.salt)
        key2 = self.encryptor.derive_key(self.pin, self.salt)
        key_diff = self.encryptor.derive_key("654321", self.salt)
        key_diff_salt = self.encryptor.derive_key(self.pin, b"DifferentSalt123")

        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key_diff)
        self.assertNotEqual(key1, key_diff_salt)
        self.assertEqual(len(key1), 32) # 256 bits key

    def test_encrypt_decrypt_data(self):
        """Tests GCM raw data encryption and decryption integrity."""
        key = self.encryptor.derive_key(self.pin, self.salt)
        secret_message = b"Top secret data chunk!"
        
        # Encrypt
        encrypted = self.encryptor.encrypt_data(secret_message, key)
        self.assertNotEqual(secret_message, encrypted)
        self.assertGreater(len(encrypted), 12) # Nonce (12 bytes) + ciphertext + tag
        
        # Decrypt
        decrypted = self.encryptor.decrypt_data(encrypted, key)
        self.assertEqual(secret_message, decrypted)

        # Decrypt with wrong key should fail
        wrong_key = self.encryptor.derive_key("wrongpin", self.salt)
        with self.assertRaises(Exception):
            self.encryptor.decrypt_data(encrypted, wrong_key)

    def test_vault_lifecycle(self):
        """Tests complete vault setup, file insertion, index mapping, decryption and unprotect flows."""
        # 1. Initialize vault
        key = self.encryptor.initialize_vault(self.temp_dir, self.pin, "TestVault")
        self.assertTrue(self.encryptor.is_vault_initialized(self.temp_dir))
        self.assertEqual(self.encryptor.get_vault_label(self.temp_dir), "TestVault")

        # 2. Add files to vault
        local_src_file = os.path.join(self.temp_dir, "test_doc.txt")
        file_content = b"This is some confidential information inside the vault."
        with open(local_src_file, "wb") as f:
            f.write(file_content)

        vault_rel_path = "documents/test_doc.txt"
        success = self.encryptor.add_file_to_vault(self.temp_dir, key, local_src_file, vault_rel_path)
        self.assertTrue(success)

        # Verify file is added to index and original isn't touched (add_file_to_vault doesn't delete src)
        index = self.encryptor.load_index(self.temp_dir, key)
        self.assertIn(vault_rel_path, index["files"])
        file_id = index["files"][vault_rel_path]["id"]
        self.assertEqual(index["files"][vault_rel_path]["size"], len(file_content))

        # Verify encrypted file exists in .secure_vault/data
        enc_file_path = os.path.join(self.temp_dir, ".secure_vault", "data", file_id)
        self.assertTrue(os.path.exists(enc_file_path))

        # 3. Extract file from vault
        extracted_path = os.path.join(self.temp_dir, "extracted_doc.txt")
        success_extract = self.encryptor.extract_file_from_vault(self.temp_dir, key, file_id, extracted_path)
        self.assertTrue(success_extract)
        
        with open(extracted_path, "rb") as f:
            self.assertEqual(f.read(), file_content)

        # 4. Decrypt temporary file for viewing
        temp_file_path = self.encryptor.decrypt_temp_file(self.temp_dir, key, file_id, "test_doc.txt")
        self.assertTrue(os.path.exists(temp_file_path))
        with open(temp_file_path, "rb") as f:
            self.assertEqual(f.read(), file_content)

        # Cleanup temp viewing files
        self.encryptor.cleanup_temp_files()
        self.assertFalse(os.path.exists(temp_file_path))

        # 5. Delete file from vault
        success_delete = self.encryptor.delete_file_from_vault(self.temp_dir, key, vault_rel_path)
        self.assertTrue(success_delete)
        self.assertFalse(os.path.exists(enc_file_path))
        
        updated_index = self.encryptor.load_index(self.temp_dir, key)
        self.assertNotIn(vault_rel_path, updated_index["files"])


class TestFaceAuthCore(unittest.TestCase):
    def setUp(self):
        self.model_dir = tempfile.mkdtemp()
        self.face_auth = USBFaceAuth(self.model_dir)

    def tearDown(self):
        self.face_auth.clear_model()
        if os.path.exists(self.model_dir):
            shutil.rmtree(self.model_dir)

    def test_face_detector_and_recognizer_flow(self):
        """Creates synthetic face arrays and tests the training/verification API."""
        # Create 15 horizontal gradient grayscale images (200x200) for training
        samples = []
        for i in range(15):
            base_gradient = np.tile(np.arange(200, dtype=np.uint8), (200, 1))
            img = np.clip(base_gradient.astype(int) + i, 0, 255).astype(np.uint8)
            samples.append(img)

        # Train model
        train_success = self.face_auth.train_model(samples)
        self.assertTrue(train_success)
        self.assertTrue(self.face_auth.is_trained)
        self.assertTrue(os.path.exists(self.face_auth.model_path))
        
        # Test verification with a matching sample (similar horizontal gradient)
        test_img = np.clip(np.tile(np.arange(200, dtype=np.uint8), (200, 1)).astype(int) + 7, 0, 255).astype(np.uint8)
        
        is_match, score = self.face_auth.verify_face(test_img)
        self.assertTrue(is_match)
        self.assertLess(score, 65.0)

        # Test verification with a mismatching sample (vertical gradient)
        mismatch_img = np.tile(np.arange(200, dtype=np.uint8).reshape(200, 1), (1, 200))
        is_match_fail, fail_score = self.face_auth.verify_face(mismatch_img)
        self.assertFalse(is_match_fail)
        self.assertGreater(fail_score, 65.0)

if __name__ == "__main__":
    unittest.main()
