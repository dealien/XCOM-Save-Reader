import csv
import json
import logging
import os
import tkinter as tk
import tkinter.ttk as ttk
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

USERDIR = os.path.join(ROOTDIR, 'user')

# TODO: debug_mode and json_dump should become arguments
debug_mode = True
json_dump = True

if debug_mode is True:
    save_file_path = os.path.join(ROOTDIR, 'user', 'piratez', '_quick_.asav')
    l = logging.DEBUG
else:
    save_file_path = filedialog.askopenfilename(initialdir=USERDIR)
    l = logging.INFO
logging.basicConfig(format='%(name)-4s: %(levelname)-8s [%(asctime)s]: %(message)s', level=l)

soldiers_json_file = 'soldiers.json'
soldiers_csv_file = 'soldiers.csv'


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


def read_soldiers(_data):
    _soldiers = []
    logging.info('Reading soldier data...')
    for base in _data['bases']:
        logging.debug(f'Loading soldiers from {base["name"]}...')
        try:
            len(base['soldiers'])
        except KeyError as e:
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
    logging.info('Creating CSV data...')
    headers = ['ID', 'Base', 'Type', 'Name', 'Rank', 'Missions', 'Kills', 'TUs', 'Stamina', 'Health', 'Bravery',
               'Reactions', 'Firing', 'Throwing', 'Strength', 'PsiStrength', 'PsiSkill', 'Initial TUs',
               'Initial Stamina', 'Initial Health', 'Initial Bravery', 'Initial Reactions', 'Initial Firing',
               'Initial Throwing', 'Initial Strength', 'Initial PsiStrength', 'Initial PsiSkill']
    csv_list = [headers]
    for i in _soldiers:
        keys = {
            'ID': i.id,
            'Base': i.base,
            'Type': i.type,
            'Name': i.name,
            'Rank': i.rank,
            'Missions': i.missions,
            'Kills': i.kills,
            'TUs': i.currentstats.tu,
            'Stamina': i.currentstats.stamina,
            'Health': i.currentstats.health,
            'Bravery': i.currentstats.bravery,
            'Reactions': i.currentstats.reactions,
            'Firing': i.currentstats.firing,
            'Throwing': i.currentstats.throwing,
            'Strength': i.currentstats.strength,
            'PsiStrength': i.currentstats.psistrength,
            'PsiSkill': i.currentstats.psiskill,
            'Initial TUs': i.initialstats.tu,
            'Initial Stamina': i.initialstats.stamina,
            'Initial Health': i.initialstats.health,
            'Initial Bravery': i.initialstats.bravery,
            'Initial Reactions': i.initialstats.reactions,
            'Initial Firing': i.initialstats.firing,
            'Initial Throwing': i.initialstats.throwing,
            'Initial Strength': i.initialstats.strength,
            'Initial PsiStrength': i.initialstats.psistrength,
            'Initial PsiSkill': i.initialstats.psiskill
        }
        row = []
        for j in headers:
            # logging.debug(f'j = {j}')
            # logging.debug(f'keys[j] = {keys[j]}')
            row.append(keys[j])
        csv_list.append(row)
    return csv_list


def create_soldier_table(csv_data):
    root.title("XCOM Soldier Viewer")
    width = 1600
    height = 900
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)
    root.geometry("%dx%d+%d+%d" % (width, height, x, y))
    root.resizable(1, 1)

    tframe = Frame(root)
    tframe.pack(fill="both", expand=True)
    table = TableCanvas(tframe, read_only=True)
    table.maxcellwidth = 800
    table.importCSV(soldiers_csv_file)
    table.show()
    table.adjustColumnWidths()
    table.autoResizeColumns()
    table.redraw()
    table.update()


def read_save(file):
    logging.info(f'Loading data from "{os.path.basename(save_file_path)}"...')
    with open(file, 'r') as file:
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

    logging.info(f'Writing CSV soldier list to "{soldiers_csv_file}"...')
    with open(soldiers_csv_file, 'w', newline='') as csv_file:
        wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        wr.writerows(_soldier_csv)
    return _soldiers, _soldier_csv


root = Tk()
data = ''
soldiers, soldier_csv = read_save(save_file_path)
create_soldier_table(soldier_csv)

root.mainloop()
