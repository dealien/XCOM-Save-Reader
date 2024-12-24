from reader import *


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


class TestArgs:
    def __init__(self, file, debug, json_dump):
        self.file = file
        self.debug = debug
        self.json_dump = json_dump


class TestReader:
    def test_get_path(self, printer):
        """ Ensure get_path() is working with no input file """
        args = TestArgs(None, True, True)
        path = get_file_path(args)
        printer(path)
        assert isinstance(path, str), '"path" should be a string'

    def test_get_path_with_file(self, printer):
        args = TestArgs('test/Test Save.sav', True, True)
        path = get_file_path(args)
        printer(path)
        assert isinstance(path, str), '"path" should be a string'

    def test_import(self, printer):
        """ Ensure data is importing properly """
        args = TestArgs(None, True, True)
        imported_data = import_yaml(get_file_path(args))
        assert isinstance(imported_data, dict), 'imported_data should be a dict'
        assert 'bases' in imported_data, '"bases" key should be in imported_data'

    def test_read_soldiers(self, printer):
        """ Test the soldier reading functions """
        args = TestArgs(None, True, True)
        imported_data = import_yaml(get_file_path(args))
        yaml_data = load_data_from_yaml(get_file_path(args), args)
        soldier_list = read_soldiers(yaml_data)

    def test_read_soldiers_with_json_write(self, printer):
        """ Test the soldier reading functions with json write enabled """
        args = TestArgs(None, True, True)
        imported_data = import_yaml(get_file_path(args))
        yaml_data = load_data_from_yaml(get_file_path(args), args)
        printer(f'yaml_data type: {type(yaml_data)}')
        printer(f'yaml_data length: {len(yaml_data)}')
        soldier_list = read_soldiers(yaml_data)
        printer(f'soldier_list type: {type(soldier_list)}')
        printer(f'soldier_list length: {len(soldier_list)}')

    def test_make_csv(self, printer):
        args = TestArgs(None, True, True)
        imported_data = import_yaml(get_file_path(args))
        yaml_data = load_data_from_yaml(get_file_path(args), args)
        csv_data = make_csv(read_soldiers(yaml_data))
        printer(f'csv_data type: {type(csv_data)}')
        printer(f'csv_data length: {len(csv_data)}')
