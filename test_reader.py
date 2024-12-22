from tokenize import String

import pytest
import csv
import json
import os
import yaml

from reader import *


def get_path():
    if os.name == 'posix':
        # Linux
        ROOTDIR = os.path.abspath(os.curdir).replace(';', '')
    else:
        # Windows
        ROOTDIR = os.getcwd().replace(';', '')
    file_path = os.path.join(ROOTDIR, 'test', 'Test Save.sav')
    return file_path


def import_yaml(file_path):
    data = ''
    soldiers = []
    soldiercsv = []

    print(f'Loading data from "{os.path.basename(file_path)}"...')
    with open(file_path, 'r') as file:
        for y in yaml.load_all(file, Loader=yaml.FullLoader):
            try:
                type(y['difficulty'])
                data = y
            except KeyError:
                pass
    return data


class TestReader:
    def test_get_path(self):
        """ Ensure get_path() is working """
        path = get_path()
        print(path)
        assert isinstance(path, str), '"path" should be a string'

    def test_import(self):
        """ Ensure data is importing properly """
        imported_data = import_yaml(get_path())
        assert isinstance(imported_data, dict), 'imported_data should be a dict'
        assert 'bases' in imported_data, '"bases" key should be in imported_data'

    def test_read_soldiers(self):
        """ Test the soldier reading functions """
        imported_data = import_yaml(get_path())
        yaml_data = load_data_from_yaml(get_path(), False)
        # print(yaml_data)
        soldier_list = read_soldiers(yaml_data)
        # print(soldier_list)

    def test_read_soldiers_with_json_write(self):
        """ Test the soldier reading functions with json write enabled """
        imported_data = import_yaml(get_path())
        yaml_data = load_data_from_yaml(get_path(), True)
        # print(yaml_data)
        print(f'yaml_data type: {type(yaml_data)}')
        print(f'yaml_data length: {len(yaml_data)}')
        soldier_list = read_soldiers(yaml_data)
        # print(soldier_list)
        print(f'soldier_list type: {type(soldier_list)}')
        print(f'soldier_list length: {len(soldier_list)}')

    def test_make_csv(self):
        imported_data = import_yaml(get_path())
        yaml_data = load_data_from_yaml(get_path(), True)
        csv_data = make_csv(read_soldiers(yaml_data))
        # print(csv_data)
        print(f'csv_data type: {type(csv_data)}')
        print(f'csv_data length: {len(csv_data)}')

    def test_tkinter_install(self):
        main_window = Tk()
        print(f'Arial installed = {"Arial" in tkFont.families()}')
        assert 'Arial' in tkFont.families()