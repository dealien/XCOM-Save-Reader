import os
import sys

# Add src directory to path to allow import of reader
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.reader import *

TEST_SAVE_FILE = os.path.join(os.path.dirname(__file__), '..', 'test', 'Test Save.sav')

class TestReader:
    def test_import(self):
        """ Ensure data is importing properly """
        imported_data = load_data_from_yaml(TEST_SAVE_FILE)
        assert isinstance(imported_data, dict), 'imported_data should be a dict'
        assert 'bases' in imported_data, '"bases" key should be in imported_data'

    def test_read_soldiers(self):
        """ Test the soldier reading functions """
        yaml_data = load_data_from_yaml(TEST_SAVE_FILE)
        soldier_list = read_soldiers(yaml_data)
        assert isinstance(soldier_list, list)
        assert len(soldier_list) > 0
        assert isinstance(soldier_list[0], Soldier)


    def test_read_soldiers_with_json_write(self):
        """ Test the soldier reading functions with json write enabled """
        yaml_data = load_data_from_yaml(TEST_SAVE_FILE, json_dump=True)
        soldier_list = read_soldiers(yaml_data)
        assert isinstance(soldier_list, list)
        assert len(soldier_list) > 0
        assert os.path.exists('data.json')
        os.remove('data.json')


    def test_make_csv(self):
        yaml_data = load_data_from_yaml(TEST_SAVE_FILE)
        csv_data = make_csv(read_soldiers(yaml_data))
        assert isinstance(csv_data, list)
        assert len(csv_data) > 1 # Header + at least one soldier
        assert len(csv_data[0]) == 27 # Check for correct number of columns

    def test_read_service_record(self):
        """ Test that service record data is read correctly """
        yaml_data = load_data_from_yaml(TEST_SAVE_FILE)
        soldier_list = read_soldiers(yaml_data)
        veronica = None
        for soldier in soldier_list:
            if soldier.name == "Veronica Steele":
                veronica = soldier
                break

        assert veronica is not None, "Veronica Steele not found in soldier list"

        sr = veronica.service_record
        assert isinstance(sr, ServiceRecord)
        assert len(sr.missions) == 22
        assert len(sr.commendations) == 19
        assert len(sr.kill_list) > 0
        assert sr.days_wounded_total == 116
