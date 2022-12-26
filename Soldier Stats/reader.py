import csv
import json
import logging
import os
from tkinter import *
from tkinter import filedialog
from tkintertable import TableCanvas, TableModel
import yaml

if os.name == 'posix':
    # Linux
    ROOTDIR = os.path.abspath(os.curdir).replace(';', '')
else:
    # Windows
    ROOTDIR = os.getcwd().replace(';', '')

USERDIR = os.path.join(ROOTDIR, '../user')

# TODO: debug_mode, json_dump, and write_csv should become arguments
debug_mode = True
json_dump = False
write_csv = False

if debug_mode is not True:
    save_file_path = filedialog.askopenfilename(initialdir=USERDIR)
    lvl = logging.INFO
else:
    save_file_path = os.path.join(ROOTDIR, '../user', 'piratez', '_quick_.asav')
    lvl = logging.DEBUG
logging.basicConfig(format='%(name)-4s: %(levelname)-8s [%(asctime)s]: %(message)s', level=lvl)
soldiers_json_file = 'soldiers.json'
soldiers_csv_file = 'soldiers.csv'
DEFAULT_HEADERS = ['ID', 'Base', 'Type', 'Name', 'Rank', 'Missions', 'Kills', 'TUs', 'Stamina', 'Health', 'Bravery',
                   'Reactions', 'Firing', 'Throwing', 'Strength', 'PsiStrength', 'PsiSkill', 'Initial TUs',
                   'Initial Stamina', 'Initial Health', 'Initial Bravery', 'Initial Reactions', 'Initial Firing',
                   'Initial Throwing', 'Initial Strength', 'Initial PsiStrength', 'Initial PsiSkill']


# TODO: Load language data from XCom installation to load soldier type names, etc.


class Soldier:
    def __init__(self, type, id, name, initialstats, currentstats, rank, missions, kills, base):
        self.type = type
        self.id = id
        self.name = name
        self.initialstats = Stats(initialstats)
        self.currentstats = Stats(currentstats)
        self.rank = rank
        self.missions = missions
        self.kills = kills
        self.base = base
        # TODO: Add physical/psi training status
        # TODO: Add current craft
        # TODO: Add inventory and loadout info
        # TODO: Add service record info

    @property
    def soldier_dict(self):
        return {
            'ID': self.id,
            'Base': self.base,
            'Type': self.type,
            'Name': self.name,
            'Rank': self.rank,
            'Missions': self.missions,
            'Kills': self.kills,
            'TUs': self.currentstats.tu,
            'Stamina': self.currentstats.stamina,
            'Health': self.currentstats.health,
            'Bravery': self.currentstats.bravery,
            'Reactions': self.currentstats.reactions,
            'Firing': self.currentstats.firing,
            'Throwing': self.currentstats.throwing,
            'Strength': self.currentstats.strength,
            'PsiStrength': self.currentstats.psistrength,
            'PsiSkill': self.currentstats.psiskill,
            'Initial TUs': self.initialstats.tu,
            'Initial Stamina': self.initialstats.stamina,
            'Initial Health': self.initialstats.health,
            'Initial Bravery': self.initialstats.bravery,
            'Initial Reactions': self.initialstats.reactions,
            'Initial Firing': self.initialstats.firing,
            'Initial Throwing': self.initialstats.throwing,
            'Initial Strength': self.initialstats.strength,
            'Initial PsiStrength': self.initialstats.psistrength,
            'Initial PsiSkill': self.initialstats.psiskill
        }

    def table_list(self, headers: list = None):
        """Generates a list from the soldier's data usable for csv or table creation.
        :type headers: list
        :return:
        """
        if headers is None:
            logging.warning('No headers specified; defaulting to all.')
            headers = DEFAULT_HEADERS
        keys = self.soldier_dict
        row = []
        for j in headers:
            row.append(keys[j])
        return row

    @property
    def table_record(self):
        rec = self.soldier_dict
        return rec


class Stats:
    def __init__(self, stats):
        if type(stats) is list:
            self.tu = stats[0]
            self.stamina = stats[1]
            self.health = stats[2]
            self.bravery = stats[3]
            self.reactions = stats[4]
            self.firing = stats[5]
            self.throwing = stats[6]
            self.strength = stats[7]
            self.psistrength = stats[8]
            self.psiskill = stats[9]
        else:
            self.tu = stats['tu']
            self.stamina = stats['stamina']
            self.health = stats['health']
            self.bravery = stats['bravery']
            self.reactions = stats['reactions']
            self.firing = stats['firing']
            self.throwing = stats['throwing']
            self.strength = stats['strength']
            self.psistrength = stats['psiStrength']
            self.psiskill = stats['psiSkill']

    @property
    def stat_list(self):
        return [self.tu, self.stamina, self.health, self.bravery, self.reactions, self.firing, self.throwing,
                self.strength, self.psistrength, self.psiskill]


def read_save(file_to_read):
    logging.info(f'Loading data from "{os.path.basename(save_file_path)}"...')
    with open(file_to_read, 'r') as file:
        for y in yaml.load_all(file, Loader=yaml.FullLoader):
            try:
                type(y['difficulty'])
                _data = y
            except KeyError:
                pass
    _soldiers = read_soldiers(_data)
    _soldier_csv = make_csv(_soldiers)
    if json_dump is True:
        logging.info(f'Writing converted json data to "{soldiers_json_file}"...')
        with open(soldiers_json_file, 'w') as outfile:
            json.dump(_data, outfile)
    return _soldiers, _soldier_csv


def read_soldiers(_data):
    """
    :type _data: dict
    :return:
    """
    _soldiers = []
    logging.info('Reading soldier data...')
    for base in _data['bases']:
        logging.debug(f'Loading soldiers from {base["name"]}...')
        try:
            len(base['soldiers'])
        except KeyError:
            logging.debug(f'Base {base["name"]} has no soldiers; skipping...')
            pass
        else:
            for s in base['soldiers']:
                try:
                    logging.debug(f'Reading {s["name"]}\'s data')
                    _soldier = Soldier(s['type'], s['id'], s['name'], s['initialStats'], s['currentStats'], s['rank'],
                                       s['missions'], s['kills'], base['name'])
                    _soldiers.append(_soldier)
                except KeyError as e:
                    logging.error(f'Error when loading data for {s["name"]}: {e} is not defined.')
                pass
    return _soldiers


def make_csv(_soldiers):
    """
    :type _soldiers: list
    :rtype: list
    """
    logging.info('Creating CSV data...')
    headers = DEFAULT_HEADERS
    csv_list = [headers]
    for i in _soldiers:
        row = i.table_list(headers)
        csv_list.append(row)
    if write_csv is True:
        logging.info(f'Writing CSV soldier list to "{soldiers_csv_file}"...')
        with open(soldiers_csv_file, 'w', newline='') as csv_file:
            wr = csv.writer(csv_file, quoting=csv.QUOTE_NONE)
            wr.writerows(csv_list)
    return csv_list


def make_table_dict(data):
    """
    :param data: A list of soldiers to put in the table
    :type data: list
    :return:
    """
    table_dict = {}
    for i in data:
        table_dict[i.id] = i.table_record
    return table_dict


def create_soldier_table(data):
    """
    :type data: list
    """
    logging.debug('Creating table...')
    root.title("XCOM Soldier Viewer")
    width = 1600
    height = 900
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)
    root.geometry("%dx%d+%d+%d" % (width, height, x, y))
    root.resizable(1, 1)
    tframe.pack(fill="both", expand=True)
    model.importDict(make_table_dict(data))
    # table.importCSV(soldiers_csv_file)
    logging.info('Showing table...')
    table.show()
    table.adjustColumnWidths()
    table.autoResizeColumns()
    table.redraw()
    table.update()
    return tframe, table, model


def sort_table(col):
    logging.debug("Sorting table by column: " + col)
    table.sortTable(columnName=col)
    table.redraw()


root = Tk()
tframe = Frame(root, relief=RAISED, borderwidth=1)
model = TableModel()
table = TableCanvas(tframe, model=model, read_only=True, showkeynamesinheader=True)
soldiers, soldier_csv = read_save(save_file_path)
create_soldier_table(soldiers)
sort_column = StringVar(root)
sort_column.set(DEFAULT_HEADERS[0])
sort_selector = OptionMenu(root, sort_column, *DEFAULT_HEADERS, command=sort_table)
sort_selector.pack(side=LEFT, padx=5, pady=5)
# sort_button = Button(root, text="SORT", command=sort_table)
# sort_button.pack()
sort_table(sort_column.get())
root.mainloop()
