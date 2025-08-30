import csv
import json
import os
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


def load_data_from_yaml(file_path, json_dump=False):
    data = ''
    print(f'Loading data from "{os.path.basename(file_path)}"...')
    with open(file_path, 'r') as file:
        for y in yaml.load_all(file, Loader=yaml.FullLoader):
            try:
                type(y['difficulty'])
                data = y
            except KeyError:
                pass

    if json_dump:
        print('Writing converted json data to "data.json"...')
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile)

    return data
