import os
import sys
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

_original_modules = {
    "customtkinter": sys.modules.get("customtkinter"),
    "tkinter": sys.modules.get("tkinter"),
    "tkinter.ttk": sys.modules.get("tkinter.ttk"),
    "tkinter.messagebox": sys.modules.get("tkinter.messagebox"),
    "yaml": sys.modules.get("yaml"),  # Added from HEAD
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
    sys.modules.pop("reader", None)
    sys.modules.pop("config", None)
    sys.modules.pop("data_manager", None)
    sys.modules.pop("resource_manager", None)
    sys.modules.pop("translation_manager", None)
    sys.modules.pop("inventory_formatter", None)
    sys.modules.pop("view_utils", None)

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
        sys.modules["yaml"] = MagicMock()  # Added from HEAD

        # Make sure `main` and its direct dependencies are completely reloaded
        # so they use the mocked dependencies
        for mod in ["main", "reader", "config", "data_manager", "resource_manager", "translation_manager", "inventory_formatter", "view_utils"]:
            sys.modules.pop(mod, None)

        import main

        cls.AppClass = main.App

    def setUp(self):
        self.app = self.AppClass.__new__(self.AppClass)
        self.app.missions = {
            101: {"id": 101, "name": "Operation Falling Star"},
            102: {"id": 102, "name": "Operation Hidden Chalice"},
        }
        self.app.show_frame = MagicMock()

        # Set up soldiers list (from HEAD)
        class DummySoldier:
            def __init__(self, id):
                self.id = id

        self.s1 = DummySoldier(1)
        self.s2 = DummySoldier(2)

        self.app.soldiers = [self.s1, self.s2]

    # Tests from HEAD branch
    def test_app_instance_get_soldier_by_id_valid_int(self):
        soldier = self.app.get_soldier_by_id(1)
        self.assertEqual(soldier, self.s1)

    def test_app_instance_get_soldier_by_id_valid_str(self):
        soldier = self.app.get_soldier_by_id("2")
        self.assertEqual(soldier, self.s2)

    def test_app_instance_get_soldier_by_id_not_found(self):
        soldier = self.app.get_soldier_by_id(999)
        self.assertIsNone(soldier)

    def test_app_instance_get_soldier_by_id_invalid_type_str(self):
        soldier = self.app.get_soldier_by_id("abc")
        self.assertIsNone(soldier)

    def test_app_instance_get_soldier_by_id_invalid_type_none(self):
        soldier = self.app.get_soldier_by_id(None)
        self.assertIsNone(soldier)

    # Tests from incoming branch
    def test_get_mission_by_id_existing(self):
        mission = self.app.get_mission_by_id(101)
        self.assertIsNotNone(mission)
        self.assertEqual(mission["name"], "Operation Falling Star")

    def test_get_mission_by_id_non_existing(self):
        mission = self.app.get_mission_by_id(999)
        self.assertIsNone(mission)

    def test_show_soldier_view(self):
        import main
        self.app.show_frame.reset_mock()
        self.app.show_soldier_view(123)
        self.app.show_frame.assert_called_once_with(main.SoldierView, 123, None)

    def test_show_soldier_view_with_previous(self):
        import main
        self.app.show_frame.reset_mock()
        self.app.show_soldier_view(123, previous_view="PreviousView")
        self.app.show_frame.assert_called_once_with(main.SoldierView, 123, "PreviousView")

    def test_show_mission_view(self):
        import main
        self.app.show_frame.reset_mock()
        self.app.show_mission_view(456, 123)
        self.app.show_frame.assert_called_once_with(main.MissionView, 456, 123)


if __name__ == "__main__":
    unittest.main()
