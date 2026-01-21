import os

import yaml


class TranslationManager:
    def __init__(self, base_path, language="en-US"):
        self.base_path = base_path
        self.language = language
        self.translations = {}
        self.mod_map = {}

    def index_mods(self):
        """
        Scans 'standard' and 'user/mods' to index available mods.
        Populates self.mod_map with {mod_id: mod_path}.
        """
        search_dirs = [
            os.path.join(self.base_path, "standard"),
            os.path.join(self.base_path, "user", "mods"),
        ]

        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue

            for item in os.listdir(search_dir):
                mod_path = os.path.join(search_dir, item)

                # Prevent path traversal / symlink escapes
                search_root = os.path.realpath(search_dir)
                candidate = os.path.realpath(mod_path)
                if os.path.commonpath([search_root, candidate]) != search_root:
                    continue

                if not os.path.isdir(mod_path):
                    continue

                metadata_path = os.path.join(mod_path, "metadata.yml")
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, encoding="utf-8") as f:
                            metadata = yaml.safe_load(f)
                            if metadata and "id" in metadata:
                                self.mod_map[metadata["id"]] = mod_path
                    except Exception as e:
                        print(f"Error reading metadata for {item}: {e}")

    def determine_master(self, save_mod_list):
        """
        Determine the master game version (xcom1 or xcom2) from the mod list.
        Defaults to 'xcom1'.
        """
        for mod_entry in save_mod_list:
            # Mod entry format: "Mod Name ver: Version" -> Need to match name,
            # but simpler to rely on implicit knowledge or just check checking mod_map?
            # Wait, the save format uses names, but metadata uses IDs.
            # We need to map Name -> ID? Or does the save use IDs?
            # Looking at Test Save.sav:
            # - "x-com-files ver: 3.4.1"
            # metadata.yml for that mod has id: x-com-files.
            # So the save string STARTS with the ID.

            mod_id = mod_entry.split(" ver:", 1)[0].strip()

            if mod_id in self.mod_map:
                try:
                    metadata_path = os.path.join(self.mod_map[mod_id], "metadata.yml")
                    with open(metadata_path, encoding="utf-8") as f:
                        metadata = yaml.safe_load(f)
                        if metadata and metadata.get("isMaster"):
                            return metadata.get("master", "xcom1")
                except Exception as e:
                    print(f"Error determining master for {mod_id}: {e}")
        return "xcom1"

    def load_all(self, save_mod_list):
        """
        Loads translations in order: Common -> Standard (Master) -> Mods.
        """
        self.translations = {}

        # 1. Load Common
        print(f"Loading common translations ({self.language})...")
        common_lang = os.path.join(
            self.base_path, "common", "Language", f"{self.language}.yml"
        )
        self._load_file(common_lang)

        # 2. Determine and Load Master
        master = self.determine_master(save_mod_list)
        print(f"Loading master translations ({master})...")
        master_lang = os.path.join(
            self.base_path, "standard", master, "Language", f"{self.language}.yml"
        )
        self._load_file(master_lang)

        # 3. Load Mods
        print("Loading mod translations...")
        for mod_entry in save_mod_list:
            mod_id = mod_entry.split(" ver:", 1)[0].strip()
            if mod_id in self.mod_map:
                print(f"  - Loading translations for: {mod_id}")
                mod_lang = os.path.join(
                    self.mod_map[mod_id], "Language", f"{self.language}.yml"
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
                    self.translations.update(data[self.language])
        except Exception as e:
            print(f"Error loading translation file {path}: {e}")

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
