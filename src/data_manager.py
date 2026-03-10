import hashlib
import json
import logging
import os
import tempfile

import yaml

logger = logging.getLogger(__name__)


class GameDataManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.mod_map = {}
        self.master_mod_map = {}
        self.master = "xcom1"

        # Parsed databases
        self.items = {}
        self.soldiers = {}
        self.manufacture = {}
        self.facilities = {}
        self.extraSprites = {}

        # Cache directory in OS temp folder
        self._cache_dir = os.path.join(
            tempfile.gettempdir(), "xcom-save-reader", "cache"
        )
        self.is_loaded = False

    def clear_cache(self):
        """Remove all cached ruleset files."""
        if os.path.isdir(self._cache_dir):
            for f in os.listdir(self._cache_dir):
                fp = os.path.join(self._cache_dir, f)
                try:
                    os.remove(fp)
                except OSError:
                    pass
            logger.info("Ruleset cache cleared.")

    def index_mods(self):
        """
        Scans 'standard' and 'user/mods' to index available mods.
        Populates self.mod_map with {mod_id: mod_path}.
        """
        self.mod_map.clear()
        self.master_mod_map.clear()
        search_dirs = [
            os.path.join(self.base_path, "standard"),
            os.path.join(self.base_path, "user", "mods"),
        ]

        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue

            for item in os.listdir(search_dir):
                mod_path = os.path.join(search_dir, item)

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
                                mod_id = metadata["id"]
                                self.mod_map[mod_id] = mod_path
                                if metadata.get("isMaster"):
                                    self.master_mod_map[mod_id] = metadata.get(
                                        "master", "xcom1"
                                    )
                    except Exception as e:
                        logger.error(f"Error reading metadata for {item}: {e}")

    def determine_master(self, save_mod_list):
        """
        Determine the master game version (xcom1 or xcom2).
        """
        for mod_entry in save_mod_list:
            mod_id = mod_entry.split(" ver:", 1)[0].strip()
            if mod_id in self.master_mod_map:
                return self.master_mod_map[mod_id]
        return "xcom1"

    def load_all(self, save_mod_list):
        """
        Loads ruleset data in order: Common -> Standard (Master) -> Mods.
        Uses a persistent JSON cache keyed by the mod list hash.
        """
        if not self.mod_map or not self.master_mod_map:
            self.index_mods()

        self.master = self.determine_master(save_mod_list)

        # Try loading from cache first
        cache_key = self._compute_cache_key(save_mod_list)
        if self._load_cache(cache_key):
            logger.info("Loaded ruleset data from cache.")
            self.is_loaded = True
            return

        # Reset data
        self.items = {}
        self.soldiers = {}
        self.manufacture = {}
        self.facilities = {}
        self.extraSprites = {}

        # 1. Load Common
        logger.info("Loading common rulesets...")
        common_path = os.path.join(self.base_path, "common")
        self._load_rulesets(os.path.join(common_path, "Ruleset"), common_path)

        # 2. Determine and Load Master
        logger.info(f"Loading master rulesets ({self.master})...")
        master_path = os.path.join(self.base_path, "standard", self.master)
        self._load_rulesets(os.path.join(master_path, "Ruleset"), master_path)

        # 3. Load Mods based on load order
        logger.info("Loading user mod rulesets...")
        for mod_entry in save_mod_list:
            mod_id = mod_entry.split(" ver:", 1)[0].strip()
            if mod_id in self.mod_map:
                mod_path = self.mod_map[mod_id]
                ruleset_dir = os.path.join(mod_path, "Ruleset")

                # Check for individual ruleset files in mod root
                # (OpenXcom supports a single ruleset named after the mod)
                mod_rul = os.path.join(mod_path, f"{mod_id}.rul")
                if os.path.exists(mod_rul):
                    self._parse_file(mod_rul, mod_path)

                # OR, check Ruleset directory if it exists
                if os.path.isdir(ruleset_dir):
                    self._load_rulesets(ruleset_dir, mod_path)

        # Save to cache
        self._save_cache(cache_key)
        self.is_loaded = True

    def _compute_cache_key(self, save_mod_list):
        """
        Produce a hash from the base path, mod list, and
        modification times of all .rul files that would be loaded.
        """
        raw = self.base_path + "|" + "|".join(save_mod_list)

        # Collect mtimes from all ruleset files to detect on-disk changes
        rul_dirs = [
            os.path.join(self.base_path, "common", "Ruleset"),
            os.path.join(self.base_path, "standard", self.master, "Ruleset"),
        ]
        for mod_entry in save_mod_list:
            mod_id = mod_entry.split(" ver:", 1)[0].strip()
            if mod_id in self.mod_map:
                mod_path = self.mod_map[mod_id]
                mod_rul = os.path.join(mod_path, f"{mod_id}.rul")
                if os.path.exists(mod_rul):
                    raw += f"|{mod_rul}:{os.path.getmtime(mod_rul)}"
                rul_dir = os.path.join(mod_path, "Ruleset")
                if os.path.isdir(rul_dir):
                    rul_dirs.append(rul_dir)

        for rul_dir in rul_dirs:
            if not os.path.isdir(rul_dir):
                continue
            for fn in sorted(os.listdir(rul_dir)):
                if fn.endswith(".rul"):
                    fp = os.path.join(rul_dir, fn)
                    raw += f"|{fp}:{os.path.getmtime(fp)}"

        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _get_cache_path(self, cache_key):
        return os.path.join(self._cache_dir, f"rulesets_{cache_key}.json")

    def _load_cache(self, cache_key):
        """
        Attempt to load cached data. Returns True on success.
        """
        path = self._get_cache_path(cache_key)
        if not os.path.exists(path):
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.items = data.get("items", {})
            self.soldiers = data.get("soldiers", {})
            self.manufacture = data.get("manufacture", {})
            self.facilities = data.get("facilities", {})
            self.extraSprites = data.get("extraSprites", {})
            return True
        except Exception as e:
            logger.warning(f"Cache read failed, will re-parse: {e}")
            try:
                os.remove(path)
                logger.info(f"Removed corrupt cache file: {path}")
            except OSError:
                pass
            return False

    def _save_cache(self, cache_key):
        """
        Persist compiled ruleset data to a JSON cache file.
        """
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
            path = self._get_cache_path(cache_key)
            data = {
                "items": self.items,
                "soldiers": self.soldiers,
                "manufacture": self.manufacture,
                "facilities": self.facilities,
                "extraSprites": self.extraSprites,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            logger.info(f"Saved ruleset cache to {path}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _load_rulesets(self, path, source_dir):
        """
        Loads all .rul files in a directory in alphabetical order.

        Alphabetical ordering guarantees deterministic merge precedence:
        later files overwrite fields set by earlier ones.
        """
        if not os.path.exists(path):
            return

        for filename in sorted(os.listdir(path)):
            if filename.endswith(".rul"):
                self._parse_file(os.path.join(path, filename), source_dir)

    def _parse_file(self, file_path, source_dir):
        """
        Parses a single YAML ruleset file and merges it into the master data.
        """
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                # Mod rulesets can have multiple documents separated by ---
                docs = yaml.safe_load_all(f)
                for doc in docs:
                    if not doc:
                        continue

                    self._merge_list_to_dict(
                        doc.get("items", []), self.items, source_dir
                    )
                    self._merge_list_to_dict(
                        doc.get("soldiers", []), self.soldiers, source_dir
                    )
                    self._merge_list_to_dict(
                        doc.get("manufacture", []), self.manufacture, source_dir
                    )
                    self._merge_list_to_dict(
                        doc.get("facilities", []), self.facilities, source_dir
                    )
                    self._merge_list_to_dict(
                        doc.get("extraSprites", []), self.extraSprites, source_dir
                    )

        except Exception as e:
            logger.error(f"Error parsing ruleset {file_path}: {e}")

    def _merge_list_to_dict(self, source_list, target_dict, source_dir):
        """
        OpenXcom YAML defines entities as lists of dicts with a 'type' field.
        We merge them into a dictionary keyed by 'type', updating properties.
        """
        if not source_list:
            return

        for item in source_list:
            if not isinstance(item, dict):
                continue

            ent_type = item.get("type") or item.get("name")
            if not ent_type:
                continue
            if ent_type not in target_dict:
                target_dict[ent_type] = item
            else:
                # Merge logic - in OXCE, modifying a ruleset item updates
                # only the specified fields.
                # For dicts inside dicts, recursive update might be needed,
                # but simplified version here:
                for k, v in item.items():
                    target_dict[ent_type][k] = v

            # Inject source directory so we can resolve relative paths
            target_dict[ent_type]["_source_dir"] = source_dir

    def get_soldier_rank_string(self, soldier_type, rank_index):
        """
        Get the localization string for a given rank index of a given soldier type.
        """
        if soldier_type in self.soldiers:
            soldier_def = self.soldiers[soldier_type]
            rank_strings = soldier_def.get("rankStrings", [])

            # Rank strings can be lists.
            if rank_strings and isinstance(rank_strings, list):
                if isinstance(rank_index, int) and 0 <= rank_index < len(rank_strings):
                    return rank_strings[rank_index]

        # Fallback standard ranks
        ranks = [
            "STR_ROOKIE",
            "STR_SQUADDIE",
            "STR_SERGEANT",
            "STR_CAPTAIN",
            "STR_COLONEL",
            "STR_COMMANDER",
        ]
        if isinstance(rank_index, int) and 0 <= rank_index < len(ranks):
            return ranks[rank_index]

        return f"STR_RANK_{rank_index}"

    def get_item(self, item_type):
        return self.items.get(item_type, {})

    def get_manufacture(self, project_type):
        return self.manufacture.get(project_type, {})

    def get_facility(self, facility_type):
        return self.facilities.get(facility_type, {})
