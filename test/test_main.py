import os
import sys
import unittest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import importlib
from unittest.mock import MagicMock

_original_modules = {
    "customtkinter": sys.modules.get("customtkinter"),
    "tkinter": sys.modules.get("tkinter"),
    "tkinter.ttk": sys.modules.get("tkinter.ttk"),
    "tkinter.messagebox": sys.modules.get("tkinter.messagebox"),
}

def tearDownModule():
    """Restore sys.modules to prevent test pollution."""
    for mod_name, original_mod in _original_modules.items():
        if original_mod is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = original_mod

    # Remove the imported modules so they can be cleanly re-imported by other tests
    sys.modules.pop("main", None)
    for mod in list(sys.modules.keys()):
        if mod.startswith("views."):
            sys.modules.pop(mod, None)


class TestMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Dynamically load `main.py` making sure no previous mock pollutes the test.
        The trick is to mock the problem dependencies BEFORE importing main.
        """
        # We need a dummy CTk class to avoid inheriting from MagicMock
        class DummyCTk:
            def __init__(self, *args, **kwargs):
                pass
            def title(self, *args):
                pass
            def geometry(self, *args):
                pass

        class DummyCTkFrame:
            def __init__(self, master=None, **kwargs):
                self.master = master
                self.winfo_children = MagicMock(return_value=[])

            def grid(self, **kwargs):
                pass

            def pack(self, **kwargs):
                pass

            def grid_rowconfigure(self, index, weight=1):
                pass

            def grid_columnconfigure(self, index, weight=1):
                pass

            def destroy(self):
                pass

        mock_ctk = MagicMock()
        mock_ctk.CTk = DummyCTk
        mock_ctk.CTkFrame = DummyCTkFrame

        sys.modules["customtkinter"] = mock_ctk
        sys.modules["tkinter"] = MagicMock()
        sys.modules["tkinter.ttk"] = MagicMock()
        sys.modules["tkinter.messagebox"] = MagicMock()

        # Make sure `main` is completely reloaded
        if "main" in sys.modules:
            del sys.modules["main"]

        import main
        cls.AppClass = main.App

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
