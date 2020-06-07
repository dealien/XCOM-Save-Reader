import csv
import json
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

debugmode = True
jsondump = False

if debugmode is True:
    file_path = os.path.join(ROOTDIR, 'user', 'piratez', '_quick_.asav')
else:
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(initialdir=USERDIR)


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

if jsondump is True:
    print('Writing converted json data to "data.json"...')
    with open('data.json', 'w') as outfile:
        json.dump(data, outfile)

soldiers = read_soldiers(data)
soldiercsv = make_csv(soldiers)

print('Writing CSV soldier list to "soldiers.csv"...')
with open('soldiers.csv', 'w', newline='') as csvfile:
    wr = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
    wr.writerows(soldiercsv)


# # Original ScrollableFrame class copied from https://blog.tecladocode.com/tkinter-scrollable-frames/
# class ScrollableFrame(ttk.Frame):
#     def __init__(self, container, *args, **kwargs):
#         super().__init__(container, *args, **kwargs)
#         canvas = tk.Canvas(self)
#         scrollbary = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
#         scrollbarx = ttk.Scrollbar(self, orient="horizontal", command=canvas.xview)
#         self.scrollable_frame = ttk.Frame(canvas)
#         self.scrollable_frame.bind(
#                 "<Configure>",
#                 lambda e: canvas.configure(
#                         scrollregion=canvas.bbox("all")
#                 )
#         )
#         canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
#         canvas.configure(yscrollcommand=scrollbary.set)
#         canvas.configure(xscrollcommand=scrollbarx.set)
#         scrollbarx.pack(side="bottom", fill="x")
#         scrollbary.pack(side="right", fill="y")
#         canvas.pack(side="left", fill="both", expand=True)
#
#
# class ScrollableTable:
#     def __init__(self, table_data):
#         frame = ScrollableFrame(root)
#
#         for i in range(len(table_data)):
#             for j in range(len(table_data[0])):
#                 if i is 0:  # Bold the header row
#                     self.e = Entry(frame.scrollable_frame, width=20, fg='black', font=('Arial', 12, 'bold'))
#                 else:
#                     self.e = Entry(frame.scrollable_frame, width=20, fg='black', font=('Arial', 12))
#                 self.e.grid(row=i, column=j)
#                 self.e.insert(END, table_data[i][j])
#         frame.pack(fill="both", expand=True)
#
#
# def create_gui():
#     root.title("XCOM Soldier Viewer")
#     width = 1600
#     height = 900
#     screen_width = root.winfo_screenwidth()
#     screen_height = root.winfo_screenheight()
#     x = (screen_width / 2) - (width / 2)
#     y = (screen_height / 2) - (height / 2)
#     root.geometry("%dx%d+%d+%d" % (width, height, x, y))
#     root.resizable(0, 0)
#
#     t = ScrollableTable(soldiercsv)


def create_gui():
    root.title("XCOM Soldier Viewer")
    width = 1600
    height = 900
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)
    root.geometry("%dx%d+%d+%d" % (width, height, x, y))
    root.resizable(0, 0)

    tframe = Frame(root)
    tframe.pack(fill="both", expand=True)
    table = TableCanvas(tframe, editable=False)
    table.importCSV('soldiers.csv')
    table.show()
    table.update()


root = Tk()

create_gui()
root.mainloop()
