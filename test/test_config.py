import json
import os
from unittest.mock import mock_open, patch

from src.config import Config


class TestConfig:
    @patch("os.path.exists")
    def test_init_defaults(self, mock_exists):
        """Verify game_dir is empty when no config file exists."""
        mock_exists.return_value = False
        config = Config()
        assert config.game_dir == ""

    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"game_dir": "/path/to/game"}',
    )
    def test_load_success(self, mock_file, mock_exists):
        """Verify Config() loads game_dir correctly when file exists."""
        mock_exists.return_value = True
        config = Config()
        assert config.game_dir == "/path/to/game"
        mock_file.assert_called_once()

    @patch("os.path.exists")
    @patch("builtins.open", side_effect=Exception("Read error"))
    def test_load_failure(self, mock_file, mock_exists):
        """Verify game_dir remains empty and exception is handled on load failure."""
        mock_exists.return_value = True
        config = Config()
        assert config.game_dir == ""

    @patch("os.path.exists")
    def test_save_success(self, mock_exists):
        """Verify config.save() returns True and writes expected JSON."""
        mock_exists.return_value = False
        config = Config()
        config.game_dir = "/new/path"

        with patch("builtins.open", mock_open()) as mock_file:
            result = config.save()
            assert result is True

            # Get all data written to the file
            handle = mock_file()
            # Join all calls to write()
            written_data = "".join(call.args[0] for call in handle.write.call_args_list)
            assert json.loads(written_data) == {"game_dir": "/new/path"}

    @patch("os.path.exists")
    def test_save_failure(self, mock_exists):
        """Verify config.save() returns False and handles exception on save failure."""
        mock_exists.return_value = False
        config = Config()

        with patch("builtins.open", side_effect=Exception("Write error")):
            result = config.save()
            assert result is False

    def test_get_config_path(self):
        """Verify _get_config_path() returns correct path."""
        config = Config()
        path = config._get_config_path()
        assert path.endswith("config.json")
        # Should be in parent of src
        src_dir = os.path.dirname(os.path.abspath(Config.__init__.__code__.co_filename))
        parent_dir = os.path.dirname(src_dir)
        expected_path = os.path.join(parent_dir, "config.json")
        # Use os.path.abspath to normalize paths for comparison
        assert os.path.abspath(path) == os.path.abspath(expected_path)
