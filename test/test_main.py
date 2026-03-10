import os
import sys
import unittest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import importlib
from unittest.mock import MagicMock

class TestMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Dynamically load `main.py` making sure no previous mock pollutes the test.
        The trick is to mock the problem dependencies BEFORE importing main.
        """
        cls.orig_ctk = sys.modules.get("customtkinter")
        cls.orig_tk = sys.modules.get("tkinter")

        # We need a dummy CTk class to avoid inheriting from MagicMock
        class DummyCTk:
            def __init__(self, *args, **kwargs):
                pass
            def title(self, *args):
                pass
            def geometry(self, *args):
                pass

        mock_ctk = MagicMock()
        mock_ctk.CTk = DummyCTk

        sys.modules["customtkinter"] = mock_ctk
        sys.modules["tkinter"] = MagicMock()
        sys.modules["tkinter.ttk"] = MagicMock()
        sys.modules["tkinter.messagebox"] = MagicMock()

        # Make sure `main` is completely reloaded
        if "main" in sys.modules:
            del sys.modules["main"]

        import main
        cls.AppClass = main.App

    @classmethod
    def tearDownClass(cls):
        # Restore original modules
        if cls.orig_ctk:
            sys.modules["customtkinter"] = cls.orig_ctk
        else:
            sys.modules.pop("customtkinter", None)

        if cls.orig_tk:
            sys.modules["tkinter"] = cls.orig_tk
        else:
            sys.modules.pop("tkinter", None)
            sys.modules.pop("tkinter.ttk", None)
            sys.modules.pop("tkinter.messagebox", None)

    def setUp(self):
        class MockApp:
            def __init__(self):
                self.missions = {
                    101: {"id": 101, "name": "Operation Falling Star"},
                    102: {"id": 102, "name": "Operation Hidden Chalice"}
                }
            get_mission_by_id = self.AppClass.get_mission_by_id

        self.app = MockApp()

    def test_get_mission_by_id_existing(self):
        mission = self.app.get_mission_by_id(101)
        self.assertIsNotNone(mission)
        self.assertEqual(mission["name"], "Operation Falling Star")

    def test_get_mission_by_id_non_existing(self):
        mission = self.app.get_mission_by_id(999)
        self.assertIsNone(mission)

if __name__ == "__main__":
    unittest.main()
