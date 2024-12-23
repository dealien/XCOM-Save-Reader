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
    def test_get_path(self, printer):
        """ Ensure get_path() is working """
        path = get_path()
        printer(path)
        assert isinstance(path, str), '"path" should be a string'

    def test_import(self, printer):
        """ Ensure data is importing properly """
        imported_data = import_yaml(get_path())
        assert isinstance(imported_data, dict), 'imported_data should be a dict'
        assert 'bases' in imported_data, '"bases" key should be in imported_data'

    def test_read_soldiers(self, printer):
        """ Test the soldier reading functions """
        imported_data = import_yaml(get_path())
        yaml_data = load_data_from_yaml(get_path(), json_dump=False, debug_mode=True)
        # printer(yaml_data)
        soldier_list = read_soldiers(yaml_data)
        # printer(soldier_list)

    def test_read_soldiers_with_json_write(self, printer):
        """ Test the soldier reading functions with json write enabled """
        imported_data = import_yaml(get_path())
        yaml_data = load_data_from_yaml(get_path(), json_dump=False, debug_mode=True)
        # print(yaml_data)
        printer(f'yaml_data type: {type(yaml_data)}')
        printer(f'yaml_data length: {len(yaml_data)}')
        soldier_list = read_soldiers(yaml_data)
        # print(soldier_list)
        printer(f'soldier_list type: {type(soldier_list)}')
        printer(f'soldier_list length: {len(soldier_list)}')

    def test_make_csv(self, printer):
        imported_data = import_yaml(get_path())
        yaml_data = load_data_from_yaml(get_path(), json_dump=False, debug_mode=True)
        csv_data = make_csv(read_soldiers(yaml_data))
        # print(csv_data)
        printer(f'csv_data type: {type(csv_data)}')
        printer(f'csv_data length: {len(csv_data)}')
