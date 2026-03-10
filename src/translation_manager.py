import logging
import os

import yaml

# Configure logger for this module
logger = logging.getLogger(__name__)


class TranslationManager:
    def __init__(self, data_manager, language="en-US"):
        self.data_manager = data_manager
        self.language = language
        self.translations = {}

    def load_all(self, save_mod_list):
        """
        Loads translations in order: Common -> Standard (Master) -> Mods.
        """
        self.translations = {}
        base_path = self.data_manager.base_path
        master = self.data_manager.master
        mod_map = self.data_manager.mod_map

        logger.info(f"Loading common translations ({self.language})...")
        common_lang = os.path.join(
            base_path, "common", "Language", f"{self.language}.yml"
        )
        self._load_file(common_lang)

        # 2. Determine and Load Master
        logger.info(f"Loading master translations ({master})...")
        master_lang = os.path.join(
            base_path, "standard", master, "Language", f"{self.language}.yml"
        )
        self._load_file(master_lang)

        # 3. Load Mods
        logger.info("Loading mod translations...")
        for mod_entry in save_mod_list:
            mod_id = mod_entry.split(" ver:", 1)[0].strip()
            if mod_id in mod_map:
                logger.debug(f"  - Loading translations for: {mod_id}")
                mod_lang = os.path.join(
                    mod_map[mod_id], "Language", f"{self.language}.yml"
                )
                self._load_file(mod_lang)

    def _load_file(self, path):
        if not os.path.exists(path):
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                # Structure is usually { "en-US": { "STR_KEY": "Value" } }
                if data and self.language in data:
                    payload = data[self.language]
                    if isinstance(payload, dict):
                        self.translations.update(payload)
        except Exception as e:
            logger.error(f"Error loading translation file {path}: {e}")

    def get(self, key):
        """
        Get the translated string for a key. Returns the key if not found.
        """
        if not key:
            return ""

        val = self.translations.get(key, key)

        # Handle list variants (randomized strings) - just take the first one
        if isinstance(val, list) and len(val) > 0:
            return val[0]

        return val

    def get_rank_string(self, rank_index, soldier_type):
        """
        Delegates to GameDataManager for accurate ruleset-based rank string.
        """
        return self.data_manager.get_soldier_rank_string(soldier_type, rank_index)
