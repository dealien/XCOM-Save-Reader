import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# Mock tkinter and customtkinter and other GUI stuff before importing SettingsView
class DummyCTk:
    def __init__(self, *args, **kwargs):
        pass

    def title(self, *args, **kwargs):
        pass

    def geometry(self, *args, **kwargs):
        pass

    def mainloop(self, *args, **kwargs):
        pass


class DummyCTkToplevel(DummyCTk):
    pass


ctk_mock = MagicMock()
ctk_mock.CTkToplevel = DummyCTkToplevel
sys.modules["customtkinter"] = ctk_mock

sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter.filedialog"] = MagicMock()
sys.modules["tkinter.messagebox"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()

from src.data_manager import GameDataManager  # noqa: E402
from src.views.settings_view import SettingsView  # noqa: E402


class TestSecurityMakedirs(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_cache_dir_permissions_data_manager(self):
        # We need to mock the _cache_dir to point to our test_dir
        dm = GameDataManager("/fake/path")
        test_cache_dir = os.path.join(self.test_dir, "cache_dm")
        dm._cache_dir = test_cache_dir

        # Call _save_cache (it will likely fail on save but we care about makedirs)
        dm._save_cache("test_key")

        self.assertTrue(os.path.exists(test_cache_dir))
        mode = os.stat(test_cache_dir).st_mode
        import stat

        perm = stat.S_IMODE(mode)

        self.assertEqual(
            oct(perm), "0o700", f"Expected permissions 0700, got {oct(perm)}"
        )

    @patch("src.views.settings_view.subprocess.Popen")
    @patch("src.views.settings_view.os.startfile", create=True)
    def test_cache_dir_permissions_settings_view(self, mock_startfile, mock_popen):
        # Mock controller and data_manager
        mock_controller = MagicMock()
        test_cache_dir = os.path.join(self.test_dir, "cache_view")
        mock_controller.data_manager._cache_dir = test_cache_dir

        # Instantiate SettingsView
        # We use __new__ to avoid __init__ which calls many GUI things
        view = SettingsView.__new__(SettingsView)
        view.controller = mock_controller

        # Call open_cache_dir
        view.open_cache_dir()

        self.assertTrue(os.path.exists(test_cache_dir))
        mode = os.stat(test_cache_dir).st_mode
        import stat

        perm = stat.S_IMODE(mode)

        self.assertEqual(
            oct(perm), "0o700", f"Expected permissions 0700, got {oct(perm)}"
        )


if __name__ == "__main__":
    unittest.main()
