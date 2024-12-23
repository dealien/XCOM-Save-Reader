import csv
import json
import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import *
from tkinter import filedialog
from tkinter import font as tkFont
import yaml


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


def read_soldiers(data_):
    soldiers_ = []
    print('Reading soldier data...')
    for base in data_['bases']:
        try:
            for s in base['soldiers']:
                soldier_ = Soldier(s['type'], s['id'], s['name'], s['initialStats'], s['currentStats'], s['rank'],
                                   s['missions'], s['kills'], base['name'])
                soldiers_.append(soldier_)
        except KeyError:
            pass
    return soldiers_


def make_csv(soldiers_):
    csvlist = [
        ['ID', 'Base', 'Type', 'Name', 'Rank', 'Missions', 'Kills', 'TUs', 'Stamina', 'Health', 'Bravery', 'Reactions',
         'Firing', 'Throwing', 'Strength', 'PsiStrength', 'PsiSkill', 'Initial TUs', 'Initial Stamina',
         'Initial Health', 'Initial Bravery', 'Initial Reactions', 'Initial Firing', 'Initial Throwing',
         'Initial Strength', 'Initial PsiStrength', 'Initial PsiSkill']]
    for i in soldiers_:
        row = [i.id, i.base, i.type, i.name, i.rank, i.missions, i.kills, i.currentstats.tu, i.currentstats.stamina,
               i.currentstats.health, i.currentstats.bravery, i.currentstats.reactions, i.currentstats.firing,
               i.currentstats.throwing, i.currentstats.strength, i.currentstats.psistrength, i.currentstats.psiskill,
               i.initialstats.tu, i.initialstats.stamina, i.initialstats.health, i.initialstats.bravery,
               i.initialstats.reactions, i.initialstats.firing, i.initialstats.throwing, i.initialstats.strength,
               i.initialstats.psistrength, i.initialstats.psiskill]
        csvlist.append(row)
    return csvlist


def get_file_path(args):
    if os.name == 'posix':
        # Linux
        ROOTDIR = os.path.abspath(os.curdir).replace(';', '')
    else:
        # Windows
        ROOTDIR = os.getcwd().replace(';', '')

    USERDIR = os.path.join(ROOTDIR, 'user')

    if args.file:
        file_path = os.path.join(ROOTDIR, args.file)
    elif args.debug is True:
        file_path = os.path.join(ROOTDIR, 'user', 'x-com-files', '_quick_.asav')
    else:
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(initialdir=USERDIR)
    return file_path


def load_data_from_yaml(file_path, args, return_csv=False):
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

    if args.json_dump is True:
        print('Writing converted json data to "data.json"...')
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile)

    soldiers = read_soldiers(data)
    soldiercsv = make_csv(soldiers)

    print('Writing CSV soldier list to "soldiers.csv"...')
    with open('soldiers.csv', 'w', newline='') as csvfile:
        wr = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        wr.writerows(soldiercsv)
    if return_csv:
        return soldiercsv
    else:
        return data


def load_csv(tree, data):
    # Define columns
    tree["columns"] = data[0]

    # Format columns
    for col in data[0]:
        tree.column(col, anchor="center")
        tree.heading(col, text=col, anchor="center")

    # Insert rows
    for row in data[1:]:
        tree.insert("", tk.END, values=row)


def create_treeview(root, data):
    columns = data[0]
    tree = ttk.Treeview(root, columns=columns, show="headings")

    # Set column headings
    for col in columns:
        tree.heading(col, text=col.upper())

    # Insert data into the Treeview
    for row in data[1:]:
        tree.insert("", tk.END, values=row)

    return tree


def resize_columns(tree):
    for col in tree["columns"]:
        tree.column(col, width=tkFont.Font().measure(tree.heading(col, "text")))
        for item in tree.get_children():
            width = tkFont.Font().measure(tree.set(item, col))
            if tree.column(col, 'width') < width:
                tree.column(col, width=width)


class TableWindow:
    def __init__(self, root, data):
        width = 1600
        height = 900
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        root.geometry("%dx%d+%d+%d" % (width, height, x, y))
        root.resizable(0, 0)

        tframe = Frame(root)
        tframe.pack(fill=tk.BOTH, expand=True)
        tree = create_treeview(tframe, data)
        resize_columns(tree)
        tree.pack(fill=tk.BOTH, expand=True)
