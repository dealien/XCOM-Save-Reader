import os
import sys
import unittest

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import view_utils
from reader import ServiceRecord


class TestViewUtils(unittest.TestCase):
    def test_format_service_record_summary(self):
        diary_data = {
            "monthsService": 5,
            "daysWoundedTotal": 10,
            "timesWoundedTotal": 2,
            "unconciousTotal": 1,
            "shotsFiredCounterTotal": 100,
            "shotsLandedCounterTotal": 50,
            "shotAtCounterTotal": 20,
            "hitCounterTotal": 5,
        }
        sr = ServiceRecord(diary_data, {})

        expected = (
            "Months of Service: 5\n"
            "Days Wounded: 10 (Wounded 2 times)\n"
            "Times Unconscious: 1\n"
            "Shots Fired: 100 | Shots Landed: 50\n"
            "Times Shot At: 20 | Times Hit: 5"
        )

        self.assertEqual(view_utils.format_service_record_summary(sr), expected)

    def test_format_death_info(self):
        def translator(x):
            return f"TR[{x}]"

        death_info = {
            "time": "2000-01-01",
            "cause": {
                "race": "STR_SECTOID",
                "rank": "STR_SOLDIER",
                "weapon": "STR_PLASMA_PISTOL",
                "weaponAmmo": "STR_PLASMA_PISTOL_CLIP",
            },
        }

        expected = (
            "\n--- KIA ---\n"
            "Date: 2000-01-01\n"
            "Killed by: TR[STR_SECTOID] (TR[STR_SOLDIER])\n"
            "Weapon: TR[STR_PLASMA_PISTOL] (TR[STR_PLASMA_PISTOL_CLIP])"
        )

        self.assertEqual(view_utils.format_death_info(death_info, translator), expected)

    def test_format_death_info_no_death(self):
        self.assertEqual(view_utils.format_death_info(None, None), "")

    def test_format_death_info_missing_fields(self):
        def translator(x):
            return f"TR[{x}]"

        death_info = {"time": "2000-01-01"}  # cause missing

        expected = (
            "\n--- KIA ---\n"
            "Date: 2000-01-01\n"
            "Killed by: TR[Unknown] (TR[Unknown])\n"
            "Weapon: TR[Unknown] (Unknown)"
        )

        self.assertEqual(view_utils.format_death_info(death_info, translator), expected)

    def test_format_mission_death_detail(self):
        def translator(x):
            return f"TR[{x}]"

        death_info = {
            "cause": {
                "race": "STR_SECTOID",
                "weapon": "STR_PLASMA_PISTOL",
            }
        }

        expected = "KIA: TR[STR_PLASMA_PISTOL] (TR[STR_SECTOID])"
        self.assertEqual(
            view_utils.format_mission_death_detail(death_info, translator), expected
        )


if __name__ == "__main__":
    unittest.main()
