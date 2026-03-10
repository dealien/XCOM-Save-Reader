import os
import shutil
import sys
import tempfile

import yaml

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.data_manager import GameDataManager


class TestGameDataManager:
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

    def test_index_mods(self):
        dm = GameDataManager(self.test_dir)
        dm.index_mods()

        assert "xcom1" in dm.mod_map
        assert "xcom2" in dm.mod_map
        assert "mod1" in dm.mod_map
        assert "mod2" in dm.mod_map
        assert dm.mod_map["mod1"] == self.mod1_dir

    def test_index_mods_metadata_error(self, caplog):
        """
        Verify that a malformed metadata.yml does not crash indexing
        and logs an appropriate error message.
        """
        import logging

        # Create a mod with a malformed metadata.yml
        bad_mod_dir = os.path.join(self.test_dir, "user", "mods", "BadMod")
        os.makedirs(bad_mod_dir, exist_ok=True)
        bad_metadata_path = os.path.join(bad_mod_dir, "metadata.yml")

        # Write invalid YAML
        with open(bad_metadata_path, "w") as f:
            f.write("id: [unclosed list")

        dm = GameDataManager(self.test_dir)

        with caplog.at_level(logging.ERROR):
            dm.index_mods()

        # The bad mod should not be in the mod map
        assert bad_mod_dir not in dm.mod_map.values()

        # Verify the error was logged
        error_logs = [
            record.getMessage()
            for record in caplog.records
            if record.levelname == "ERROR"
        ]
        assert any("Error reading metadata for BadMod" in msg for msg in error_logs)

    def test_determine_master(self):
        dm = GameDataManager(self.test_dir)
        dm.index_mods()

        # Default
        assert dm.determine_master([]) == "xcom1"

        assert dm.determine_master(["xcom2 ver: 1.0"]) == "xcom2"
        assert dm.determine_master(["xcom1 ver: 1.0"]) == "xcom1"

    def test_get_rank_string(self):
        dm = GameDataManager(self.test_dir)
        # Test standard ranks
        assert dm.get_soldier_rank_string("STR_SOLDIER", 0) == "STR_ROOKIE"
        assert dm.get_soldier_rank_string("STR_SOLDIER", 2) == "STR_SERGEANT"
        assert dm.get_soldier_rank_string("STR_SOLDIER", 5) == "STR_COMMANDER"

        # Test out of bounds
        assert dm.get_soldier_rank_string("STR_SOLDIER", 6) == "STR_RANK_6"
        assert dm.get_soldier_rank_string("STR_SOLDIER", -1) == "STR_RANK_-1"

    def _create_ruleset(self, mod_dir, ruleset_data):
        """Helper to write a .rul file into a mod's Ruleset directory."""
        ruleset_dir = os.path.join(mod_dir, "Ruleset")
        os.makedirs(ruleset_dir, exist_ok=True)
        with open(os.path.join(ruleset_dir, "test.rul"), "w") as f:
            yaml.dump(ruleset_data, f)

    def test_cache_created_on_first_load(self):
        """Cache file should be written after parsing rulesets."""
        self._create_ruleset(
            self.mod1_dir,
            {"items": [{"type": "STR_RIFLE", "weight": 8}]},
        )
        dm = GameDataManager(self.test_dir)
        dm.index_mods()

        mod_list = ["xcom1 ver: 1.0", "mod1 ver: 1.0"]
        dm.load_all(mod_list)

        # Verify data was parsed
        assert "STR_RIFLE" in dm.items
        assert dm.items["STR_RIFLE"]["weight"] == 8

        # Verify cache file exists
        cache_key = dm._compute_cache_key(mod_list)
        cache_path = dm._get_cache_path(cache_key)
        assert os.path.exists(cache_path)

    def test_cache_hit_on_second_load(self):
        """Second load with same mod list should use the cache."""
        self._create_ruleset(
            self.mod1_dir,
            {"items": [{"type": "STR_RIFLE", "weight": 8}]},
        )
        dm = GameDataManager(self.test_dir)
        dm.index_mods()

        mod_list = ["xcom1 ver: 1.0", "mod1 ver: 1.0"]
        dm.load_all(mod_list)  # First load: parses and caches

        # Create a second manager pointing to the same dirs
        dm2 = GameDataManager(self.test_dir)
        dm2.index_mods()
        dm2._cache_dir = dm._cache_dir  # Share cache dir
        dm2.load_all(mod_list)  # Should hit cache

        # Data should be identical
        assert "STR_RIFLE" in dm2.items
        assert dm2.items["STR_RIFLE"]["weight"] == 8

    def test_cache_miss_on_different_mod_list(self):
        """Different mod list should produce a different cache key."""
        dm = GameDataManager(self.test_dir)
        dm.index_mods()

        list_a = ["xcom1 ver: 1.0", "mod1 ver: 1.0"]
        list_b = ["xcom1 ver: 1.0", "mod2 ver: 2.0"]

        key_a = dm._compute_cache_key(list_a)
        key_b = dm._compute_cache_key(list_b)

        assert key_a != key_b

    def test_merge_list_to_dict_name_key(self):
        """Manufacture rulesets use 'name' instead of 'type'."""
        dm = GameDataManager(self.test_dir)
        target = {}
        source = [
            {"name": "STR_LASER_RIFLE", "time": 400, "cost": 20000},
            {"name": "STR_LASER_PISTOL", "time": 300, "cost": 8000},
        ]
        dm._merge_list_to_dict(source, target, self.test_dir)

        assert "STR_LASER_RIFLE" in target
        assert target["STR_LASER_RIFLE"]["time"] == 400
        assert "STR_LASER_PISTOL" in target
        assert target["STR_LASER_PISTOL"]["cost"] == 8000

    def test_merge_list_to_dict_skips_no_key(self):
        """Entries without 'type' or 'name' should be skipped."""
        dm = GameDataManager(self.test_dir)
        target = {}
        source = [
            {"category": "STR_WEAPON"},  # no type or name
            {"type": "STR_RIFLE", "weight": 5},
        ]
        dm._merge_list_to_dict(source, target, self.test_dir)

        assert len(target) == 1
        assert "STR_RIFLE" in target
