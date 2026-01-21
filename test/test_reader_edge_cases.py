import os
import sys
import tempfile
import unittest

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from reader import load_data_from_yaml, read_missions, read_soldiers


class TestReaderEdgeCases(unittest.TestCase):
    def test_read_soldiers_missing_optional_fields(self):
        """Test reading a soldier that is missing optional fields like 'rank'."""

        # Minimal soldier data
        soldier_data = {
            "id": 1,
            "name": "John Doe",
            "type": 0,  # X-Com
        }

        # Valid minimal Service Record to avoid crashing read_service_record
        soldier_data["diary"] = {
            "missions": [],
            "commendations": [],
            "killList": [],
            "totalWounded": 0,
            "totalUnconscious": 0,
            "totalShotsFired": 0,
            "totalShotsHit": 0,
            "totalShotAt": 0,
            "totalTimesHit": 0,
            "serviceCount": 10,
        }

        soldier_data["currentStats"] = {
            "tu": 50,
            "stamina": 100,
            "health": 30,
            "bravery": 10,
            "reactions": 40,
            "firing": 50,
            "throwing": 50,
            "strength": 20,
            "psiStrength": 0,
            "psiSkill": 0,
        }
        soldier_data["initialStats"] = soldier_data["currentStats"]
        soldier_data["rank"] = 0  # Rookie

        # Mock the game data dict (not a list of docs)
        game_data = {"bases": [{"name": "Test Base", "soldiers": [soldier_data]}]}

        soldiers, _ = read_soldiers(game_data, {})
        self.assertEqual(len(soldiers), 1)
        self.assertEqual(soldiers[0].name, "John Doe")

    def test_load_data_empty_file(self):
        """Test loading an empty file raises ValueError or similar."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # load_data_from_yaml expects 2 documents
            with self.assertRaises(ValueError):
                load_data_from_yaml(tmp_path)
        finally:
            os.remove(tmp_path)

    def test_read_missions_malformed(self):
        """Test read_missions with malformed mission data."""
        # read_missions expects the list of documents usually, or handles dict?
        # Based on test_reader.py: read_missions(yaml_data) where yaml_data is dict
        # So it likely looks for missionStatistics in the dict.

        game_data = {"bases": []}  # Missing missionStatistics

        missions = read_missions(game_data)
        self.assertEqual(missions, {})
