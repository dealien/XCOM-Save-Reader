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
    "tkinter.filedialog": sys.modules.get("tkinter.filedialog"),
    "yaml": sys.modules.get("yaml"),  # Added from HEAD
    "PIL": sys.modules.get("PIL"),
    "PIL.Image": sys.modules.get("PIL.Image"),
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
        sys.modules["tkinter.filedialog"] = MagicMock()
        sys.modules["yaml"] = MagicMock()  # Added from HEAD
        sys.modules["PIL"] = MagicMock()
        sys.modules["PIL.Image"] = MagicMock()

        # Make sure `main` is completely reloaded
        if "main" in sys.modules:
            del sys.modules["main"]

        import main

        cls.AppClass = main.App

    def setUp(self):
        class MockApp:
            def __init__(self):
                self.soldiers = []  # From HEAD
                self.missions = {  # From incoming
                    101: {"id": 101, "name": "Operation Falling Star"},
                    102: {"id": 102, "name": "Operation Hidden Chalice"},
                }

            get_soldier_by_id = (
                self.AppClass.get_soldier_by_id
            )  # From HEAD, adapted to use AppClass
            get_mission_by_id = self.AppClass.get_mission_by_id  # From incoming
            show_soldier_view = self.AppClass.show_soldier_view
            show_mission_view = self.AppClass.show_mission_view

        self.app = MockApp()
        self.app.show_frame = MagicMock()

        # Set up soldiers list (from HEAD)
        class DummySoldier:
            def __init__(self, id):
                self.id = id

        self.s1 = DummySoldier(1)
        self.s2 = DummySoldier(2)

        self.app.soldiers = [self.s1, self.s2]

    # Tests from HEAD branch
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
        self.app.show_frame.assert_called_once_with(
            main.SoldierView, 123, "PreviousView"
        )

    def test_show_mission_view(self):
        import main

        self.app.show_frame.reset_mock()
        self.app.show_mission_view(456, 123)
        self.app.show_frame.assert_called_once_with(main.MissionView, 456, 123)

    def test_load_save_file_with_path(self):
        """Test load_save_file loads the specified file."""
        import main

        app = self.AppClass.__new__(self.AppClass)
        app.save_data = None
        app.bases = []
        app.soldiers = []
        app.missions = {}
        app.mission_participants = {}
        app.data_manager = MagicMock()
        app.translation_manager = MagicMock()
        app.frames = {main.MainMenu: MagicMock()}

        with unittest.mock.patch("reader.load_data_from_yaml") as mock_load:
            mock_load.return_value = {"mods": [], "difficulty": 0}
            with unittest.mock.patch("reader.read_missions", return_value={}):
                with unittest.mock.patch("reader.read_bases", return_value=[]):
                    with unittest.mock.patch(
                        "reader.read_soldiers", return_value=([], {})
                    ):
                        app.load_save_file(file_path="test/Test Save.sav")

            # Verify load_data_from_yaml was called with the path
            mock_load.assert_any_call("test/Test Save.sav", section="meta")
            mock_load.assert_any_call(
                "test/Test Save.sav",
                json_dump=False,
                section="game",
            )

    def test_load_save_file_with_json_dump(self):
        """Test load_save_file passes json_dump flag through."""
        import main

        app = self.AppClass.__new__(self.AppClass)
        app.save_data = None
        app.bases = []
        app.soldiers = []
        app.missions = {}
        app.mission_participants = {}
        app.data_manager = MagicMock()
        app.translation_manager = MagicMock()
        app.frames = {main.MainMenu: MagicMock()}

        with unittest.mock.patch("reader.load_data_from_yaml") as mock_load:
            mock_load.return_value = {"mods": [], "difficulty": 0}
            with unittest.mock.patch("reader.read_missions", return_value={}):
                with unittest.mock.patch("reader.read_bases", return_value=[]):
                    with unittest.mock.patch(
                        "reader.read_soldiers", return_value=([], {})
                    ):
                        app.load_save_file(file_path="test.sav", json_dump=True)

            mock_load.assert_any_call("test.sav", json_dump=True, section="game")

    def test_load_save_file_opens_dialog_when_no_path(self):
        """Test that file dialog opens when no file_path is given."""
        import main

        app = self.AppClass.__new__(self.AppClass)
        app.save_data = None
        app.bases = []
        app.soldiers = []
        app.missions = {}
        app.mission_participants = {}
        app.data_manager = MagicMock()
        app.translation_manager = MagicMock()
        app.frames = {main.MainMenu: MagicMock()}

        # Configure the already-mocked tkinter.filedialog
        mock_filedialog = sys.modules["tkinter"].filedialog
        mock_filedialog.askopenfilename = MagicMock(return_value="selected.sav")

        with unittest.mock.patch("reader.load_data_from_yaml") as mock_load:
            mock_load.return_value = {
                "mods": [],
                "difficulty": 0,
            }
            with unittest.mock.patch("reader.read_missions", return_value={}):
                with unittest.mock.patch("reader.read_bases", return_value=[]):
                    with unittest.mock.patch(
                        "reader.read_soldiers",
                        return_value=([], {}),
                    ):
                        app.load_save_file()

            mock_filedialog.askopenfilename.assert_called_once()
            mock_load.assert_any_call("selected.sav", section="meta")

    def test_load_save_file_dialog_cancelled(self):
        """Test that cancelling the dialog does nothing."""
        app = self.AppClass.__new__(self.AppClass)
        app.data_manager = MagicMock()

        # Configure the already-mocked tkinter.filedialog
        mock_filedialog = sys.modules["tkinter"].filedialog
        mock_filedialog.askopenfilename = MagicMock(return_value="")

        with unittest.mock.patch("reader.load_data_from_yaml") as mock_load:
            app.load_save_file()
            mock_load.assert_not_called()

    def test_clear_cache(self):
        """Test data_manager.clear_cache removes cache files."""
        import os
        import tempfile

        from data_manager import GameDataManager

        dm = GameDataManager(tempfile.gettempdir())
        dm._cache_dir = os.path.join(tempfile.gettempdir(), "xcom-test-cache")
        os.makedirs(dm._cache_dir, exist_ok=True)

        # Create a dummy cache file
        dummy = os.path.join(dm._cache_dir, "test_cache.json")
        with open(dummy, "w") as f:
            f.write("{}")

        self.assertTrue(os.path.exists(dummy))
        dm.clear_cache()
        self.assertFalse(os.path.exists(dummy))

        # Cleanup
        os.rmdir(dm._cache_dir)


if __name__ == "__main__":
    unittest.main()
