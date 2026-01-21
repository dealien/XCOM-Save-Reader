import os
import sys
import unittest
from unittest.mock import patch

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.translation_manager import TranslationManager


class TestTranslationManagerSecurity(unittest.TestCase):
    @patch("src.translation_manager.os.listdir")
    @patch("src.translation_manager.os.path.isdir")
    @patch("src.translation_manager.os.path.realpath")
    @patch("src.translation_manager.os.path.commonpath")
    def test_index_mods_traversal_prevention(
        self, mock_commonpath, mock_realpath, mock_isdir, mock_listdir
    ):
        # Setup
        base_path = "/app"
        tm = TranslationManager(base_path)

        # Mock search directories to exist
        mock_isdir.side_effect = lambda x: True

        # Mock content of standard directory
        # We'll simulate one valid mod and one malicious symlink
        mock_listdir.return_value = ["MainMod", "MaliciousLink"]

        # Setup paths
        search_dir = os.path.join(base_path, "standard")  # /app/standard
        valid_mod_path = os.path.join(search_dir, "MainMod")
        malicious_mod_path = os.path.join(search_dir, "MaliciousLink")

        # Mock realpath behavior
        def realpath_side_effect(path):
            if path == search_dir:
                return "/real/app/standard"
            if path == valid_mod_path:
                return "/real/app/standard/MainMod"
            if path == malicious_mod_path:
                return "/etc/passwd"  # Points outside!
            return path

        mock_realpath.side_effect = realpath_side_effect

        # Mock commonpath behavior
        # commonpath raises ValueError if paths are on different drives,
        # or returns the common path.
        def commonpath_side_effect(paths):
            root, candidate = paths
            if (
                root == "/real/app/standard"
                and candidate == "/real/app/standard/MainMod"
            ):
                return "/real/app/standard"
            if root == "/real/app/standard" and candidate == "/etc/passwd":
                return "/"
            return os.path.dirname(root)  # Fallback

        mock_commonpath.side_effect = commonpath_side_effect

        # Run
        tm.index_mods()

        # Assertions
        # The valid mod should technically continue to check for metadata.yml
        # The malicious link should result in 'continue' immediately after the check

        # We can't easily check if 'continue' happened directly, but we can check
        # if other operations were performed on the path.
        # For example, os.path.isdir(mod_path) is called AFTER the check.
        # So if we make check return False for isdir, and track calls.

        # Reset mock_isdir to track calls better
        mock_isdir.reset_mock()
        mock_isdir.return_value = True  # Default

        # Run again with monitoring
        tm.index_mods()

        # Check calls to mocked functions
        # valid_mod_path should be checked for isdir (line 36)
        # malicious_mod_path should NOT be checked for isdir because it should hit 'continue' at line 34 (ish)

        # Wait, the code:
        # 34:                 if os.path.commonpath([search_root, candidate]) != search_root:
        # 35:                     continue
        # 36:
        # 37:                 if not os.path.isdir(mod_path): ...

        # Note: In my replacement, I might have shifted lines slightly but logically:
        # The security check is BEFORE isdir check (which was line 36 in original, maybe line 37 in my thought).

        # Let's verify what arguments were passed to os.path.isdir
        # isdir is called for search_dir (line 24) and mod_path (line 36)

        # We expect isdir to be called with search_dir
        # We expect isdir to be called with valid_mod_path
        # We expect isdir NOT to be called with malicious_mod_path IF the traversal check works.

        # Actually, isdir is called at line 24 for search_dir.
        # And line 36 for mod_path.

        # Let's check calls.
        # We have 2 search dirs: standard, user/mods.
        # listdir is called for each.
        # For 'standard', we return ["MainMod", "MaliciousLink"].

        called_paths = [call.args[0] for call in mock_isdir.call_args_list]

        # We expect valid_mod_path to be in called_paths (if it passed security check)
        self.assertIn(
            valid_mod_path, called_paths, "Valid mod path should be processed"
        )

        # We expect malicious_mod_path NOT to be in called_paths (because it failed security check)
        self.assertNotIn(
            malicious_mod_path,
            called_paths,
            "Malicious path should be skipped before isdir check",
        )


if __name__ == "__main__":
    unittest.main()
