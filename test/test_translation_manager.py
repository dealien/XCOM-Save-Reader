import logging
import os
import shutil
import sys
import tempfile

import yaml

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.data_manager import GameDataManager
from src.translation_manager import TranslationManager


class TestTranslationManager:
    def setup_method(self):
        # Create a temporary directory structure mimicking reference
        self.test_dir = tempfile.mkdtemp()
        self.common_lang_dir = os.path.join(self.test_dir, "common", "Language")
        self.xcom1_lang_dir = os.path.join(
            self.test_dir, "standard", "xcom1", "Language"
        )
        self.xcom2_lang_dir = os.path.join(
            self.test_dir, "standard", "xcom2", "Language"
        )
        self.mod1_dir = os.path.join(self.test_dir, "user", "mods", "Mod1")
        self.mod2_dir = os.path.join(self.test_dir, "user", "mods", "Mod2")

        os.makedirs(self.common_lang_dir)
        os.makedirs(self.xcom1_lang_dir)
        os.makedirs(self.xcom2_lang_dir)
        os.makedirs(os.path.join(self.mod1_dir, "Language"))
        os.makedirs(os.path.join(self.mod2_dir, "Language"))

        # Create Metadata files
        with open(
            os.path.join(self.test_dir, "standard", "xcom1", "metadata.yml"), "w"
        ) as f:
            yaml.dump({"id": "xcom1", "isMaster": True, "master": "xcom1"}, f)

        with open(
            os.path.join(self.test_dir, "standard", "xcom2", "metadata.yml"), "w"
        ) as f:
            yaml.dump({"id": "xcom2", "isMaster": True, "master": "xcom2"}, f)

        with open(os.path.join(self.mod1_dir, "metadata.yml"), "w") as f:
            yaml.dump({"id": "mod1"}, f)

        with open(os.path.join(self.mod2_dir, "metadata.yml"), "w") as f:
            yaml.dump({"id": "mod2"}, f)

    def teardown_method(self):
        shutil.rmtree(self.test_dir)

    def test_load_all_precedence(self):
        # Setup language files
        with open(os.path.join(self.common_lang_dir, "en-US.yml"), "w") as f:
            yaml.dump({"en-US": {"STR_COMMON": "Common", "STR_OVERWRITE": "Common"}}, f)

        with open(os.path.join(self.xcom1_lang_dir, "en-US.yml"), "w") as f:
            yaml.dump({"en-US": {"STR_MASTER": "Master", "STR_OVERWRITE": "Master"}}, f)

        with open(os.path.join(self.mod1_dir, "Language", "en-US.yml"), "w") as f:
            yaml.dump({"en-US": {"STR_MOD1": "Mod1", "STR_OVERWRITE": "Mod1"}}, f)

        dm = GameDataManager(self.test_dir)
        dm.index_mods()
        tm = TranslationManager(dm)

        # Load with just Master
        dm.load_all(["xcom1 ver: 1.0"])
        tm.load_all(["xcom1 ver: 1.0"])
        assert tm.get("STR_COMMON") == "Common"
        assert tm.get("STR_MASTER") == "Master"
        assert tm.get("STR_OVERWRITE") == "Master"

        # Load with Mod 1 (should overwrite Master)
        dm.load_all(["xcom1 ver: 1.0", "mod1 ver: 1.0"])
        tm.load_all(["xcom1 ver: 1.0", "mod1 ver: 1.0"])
        assert tm.get("STR_OVERWRITE") == "Mod1"
        assert tm.get("STR_MOD1") == "Mod1"

        # Test missing key fallback
        assert tm.get("STR_MISSING") == "STR_MISSING"

    def test_load_malformed_translation(self):
        """
        Verify that loading a malformed translation file (valid YAML
        but invalid structure) does not crash the manager.
        """
        # Create a malformed translation file (string instead of dict)
        malformed_path = os.path.join(self.common_lang_dir, "en-US.yml")
        with open(malformed_path, "w") as f:
            yaml.dump({"en-US": "This is not a dictionary"}, f)

        dm = GameDataManager(self.test_dir)
        tm = TranslationManager(dm)
        # Should not raise exception
        dm.load_all([])
        tm.load_all([])

        # Verify it didn't load garbage
        assert tm.get("STR_ANYTHING") == "STR_ANYTHING"

    def test_load_file_exception(self, caplog):
        """
        Verify that an exception during file loading is caught and logged.
        """
        # Create a file with invalid YAML to force yaml.safe_load to raise an exception
        invalid_yaml_path = os.path.join(self.common_lang_dir, "en-US.yml")
        with open(invalid_yaml_path, "w") as f:
            f.write("invalid: yaml: :\n  - [")

        dm = GameDataManager(self.test_dir)
        tm = TranslationManager(dm)

        with caplog.at_level(logging.ERROR):
            tm.load_all([])

        # Verify that an error was logged for this file
        assert any(
            f"Error loading translation file {invalid_yaml_path}" in record.getMessage()
            for record in caplog.records
        )
