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
    "yaml": sys.modules.get("yaml"),
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
    AppClass = None
    SoldierViewClass = None
    MissionViewClass = None

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

            def mainloop(self, *args, **kwargs):
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
        sys.modules["yaml"] = MagicMock()

        # Make sure `main` is completely reloaded
        if "main" in sys.modules:
            del sys.modules["main"]

        import main
        from views.soldier_view import SoldierView
        from views.mission_view import MissionView

        cls.AppClass = main.App
        cls.SoldierViewClass = SoldierView
        cls.MissionViewClass = MissionView

    def setUp(self):
        class MockAppForTest:
            def __init__(self, app_class):
                self.app_class = app_class
                self.soldiers = []
                self.missions = {
                    101: {"id": 101, "name": "Operation Falling Star"},
                    102: {"id": 102, "name": "Operation Hidden Chalice"},
                }
                self.mission_participants = {}
                self.frames = {}

                self.show_soldier_view = app_class.show_soldier_view
                self.show_mission_view = app_class.show_mission_view
                self.get_soldier_by_id = app_class.get_soldier_by_id
                self.get_mission_by_id = app_class.get_mission_by_id
                self.get_mission_participants = app_class.get_mission_participants
                self.show_frame = MagicMock()

        self.app = MockAppForTest(self.AppClass)

        class DummySoldier:
            def __init__(self, sid):
                self.id = sid
        self.s1 = DummySoldier(1)
        self.s2 = DummySoldier(2)
        self.app.soldiers = [self.s1, self.s2]

    def test_show_soldier_view(self):
        self.app.show_soldier_view(123)
        self.app.show_frame.assert_called_once_with(self.SoldierViewClass, 123)

    def test_show_mission_view(self):
        self.app.show_mission_view(456, 123)
        self.app.show_frame.assert_called_once_with(self.MissionViewClass, 456, 123)

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

    def test_get_mission_by_id_existing(self):
        mission = self.app.get_mission_by_id(101)
        self.assertIsNotNone(mission)
        self.assertEqual(mission["name"], "Operation Falling Star")

    def test_get_mission_by_id_non_existing(self):
        mission = self.app.get_mission_by_id(999)
        self.assertIsNone(mission)

    def test_get_mission_participants(self):
        self.app.mission_participants = {1: [1, 2], 2: [3]}
        self.assertEqual(self.app.get_mission_participants(1), [1, 2])
        self.assertEqual(self.app.get_mission_participants(3), [])

    def test_show_frame(self):
        # Restore actual show_frame method to test it
        self.app.show_frame = self.AppClass.show_frame.__get__(self.app)

        mock_frame = MagicMock()
        mock_cont = MagicMock()
        self.app.frames = {mock_cont: mock_frame}

        self.app.show_frame(mock_cont, "arg1", "arg2")

        mock_frame.update_view.assert_called_once_with("arg1", "arg2")
        mock_frame.tkraise.assert_called_once()

    def test_show_frame_no_update_view(self):
        # Restore actual show_frame method to test it
        self.app.show_frame = self.AppClass.show_frame.__get__(self.app)

        class MockFrameWithoutUpdateView:
            def __init__(self):
                self.tkraise = MagicMock()

        mock_frame = MockFrameWithoutUpdateView()
        mock_cont = MagicMock()
        self.app.frames = {mock_cont: mock_frame}

        self.app.show_frame(mock_cont, "arg1")

        mock_frame.tkraise.assert_called_once()

if __name__ == "__main__":
    unittest.main()