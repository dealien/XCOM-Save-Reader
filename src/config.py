import json
import logging
import os

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"


class Config:
    def __init__(self):
        self.game_dir = ""
        self._load()

    def _get_config_path(self):
        # Store config centrally Next to main.py or parent dir, depending on layout.
        # But for portability, using the same logic as _find_resource_path candidates
        # to find where config should live, or simply user root.
        # Let's put it next to the executable/script directory or project root.

        # A simple approach: store it in the same directory as main.py (src/) or parent.
        # We will use parent directory of src/ so it persists across runs.
        src_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(src_dir)
        return os.path.join(parent_dir, CONFIG_FILE)

    def _load(self):
        path = self._get_config_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.game_dir = data.get("game_dir", "")
                    logger.info(f"Loaded config from {path}")
            except Exception as e:
                logger.error(f"Failed to load user config: {e}")

    def save(self):
        path = self._get_config_path()
        try:
            data = {"game_dir": self.game_dir}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                logger.info(f"Saved config to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user config: {e}")
            return False
