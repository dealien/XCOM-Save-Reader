import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock yaml
sys.modules["yaml"] = MagicMock()

# Mock ctk components
class DummyCTk:
    def __init__(self, *args, **kwargs):
        pass

mock_ctk = MagicMock()
mock_ctk.CTk = DummyCTk
sys.modules["customtkinter"] = mock_ctk
sys.modules["tkinter"] = MagicMock()

from main import App

class TestMain(unittest.TestCase):
    def setUp(self):
        # We don't need a real App object, just use the function
        # Or create an object that acts like App just for this method
        class DummyApp:
            def __init__(self):
                self.soldiers = []

            get_soldier_by_id = App.get_soldier_by_id

        self.app = DummyApp()

        # Set up soldiers list
        class DummySoldier:
            def __init__(self, id):
                self.id = id

        self.s1 = DummySoldier(1)
        self.s2 = DummySoldier(2)

        self.app.soldiers = [self.s1, self.s2]

    def test_get_soldier_by_id_valid_int(self):
        soldier = self.app.get_soldier_by_id(1)
        self.assertEqual(soldier, self.s1)

    def test_get_soldier_by_id_valid_str(self):
        soldier = self.app.get_soldier_by_id("2")
        self.assertEqual(soldier, self.s2)

    def test_get_soldier_by_id_not_found(self):
        soldier = self.app.get_soldier_by_id(999)
        self.assertIsNone(soldier)

    def test_get_soldier_by_id_invalid_type_str(self):
        soldier = self.app.get_soldier_by_id("abc")
        self.assertIsNone(soldier)

    def test_get_soldier_by_id_invalid_type_none(self):
        soldier = self.app.get_soldier_by_id(None)
        self.assertIsNone(soldier)

if __name__ == "__main__":
    unittest.main()
