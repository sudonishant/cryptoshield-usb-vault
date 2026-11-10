import os
import tempfile
import unittest

from main import CryptoshieldApp


class TestLocalCredentialHandling(unittest.TestCase):
    def test_pin_is_never_written_or_loaded_from_disk(self):
        with tempfile.TemporaryDirectory() as data_dir:
            app = object.__new__(CryptoshieldApp)
            app.data_dir = data_dir

            legacy_path = os.path.join(data_dir, "secure_pin.dat")
            with open(legacy_path, "wb") as handle:
                handle.write(bytes([ord(char) ^ 0xAA for char in "123456"]))

            self.assertEqual(app._get_local_pin(), "")
            self.assertFalse(os.path.exists(legacy_path))

            app._save_local_pin("654321")
            self.assertFalse(os.path.exists(legacy_path))
            self.assertEqual(app._get_local_pin(), "")


if __name__ == "__main__":
    unittest.main()
