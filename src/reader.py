import json
import logging
import os

import yaml

# Configure logger for this module
logger = logging.getLogger(__name__)


class Soldier:
    def __init__(self, data, base_name, mission_data):
        self.type = data["type"]
        self.id = data["id"]
        self.name = data["name"]
        self.initialstats = Stats(data["initialStats"])
        self.currentstats = Stats(data["currentStats"])
        self.rank = data["rank"]
        self.missions = data.get("missions", 0)
        self.kills = data.get("kills", 0)
        self.base = base_name
        self.service_record = ServiceRecord(data.get("diary", {}), mission_data)
        self.equipmentLayout = data.get("equipmentLayout")

        # Status parsing
        self.recovery = data.get("recovery", 0)
        self.training = data.get("training", False)
        self.psi_training = data.get("psiTraining", False)

        # Death info
        self.death_info = None
        if "death" in data:
            self.death_info = data["death"]
            # Format time if it's a dictionary
            if "time" in self.death_info and isinstance(self.death_info["time"], dict):
                t = self.death_info["time"]
                self.death_info["time"] = (
                    f"{t.get('day', 0):02d}/{t.get('month', 0):02d}/{t.get('year', 0)} "
                    f"{t.get('hour', 0):02d}:{t.get('minute', 0):02d}"
                )
            # If date is missing from death info (it happens),
            # try to infer or leave generic
            elif "time" not in self.death_info:
                self.death_info["time"] = "Unknown"


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
            self.tu = stats["tu"]
            self.stamina = stats["stamina"]
            self.health = stats["health"]
            self.bravery = stats["bravery"]
            self.reactions = stats["reactions"]
            self.firing = stats["firing"]
            self.throwing = stats["throwing"]
            self.strength = stats["strength"]
            self.psistrength = stats["psiStrength"]
            self.psiskill = stats["psiSkill"]

    @property
    def stat_list(self):
        return [
            self.tu,
            self.stamina,
            self.health,
            self.bravery,
            self.reactions,
            self.firing,
            self.throwing,
            self.strength,
            self.psistrength,
            self.psiskill,
        ]


class ServiceRecord:
    def __init__(self, diary_data, mission_data):
        self.commendations = diary_data.get("commendations", [])
        self.kill_list = diary_data.get("killList", [])
        self.mission_id_list = diary_data.get("missionIdList", [])
        self.days_wounded_total = diary_data.get("daysWoundedTotal", 0)
        self.months_service = diary_data.get("monthsService", 0)
        self.unconscious_total = diary_data.get(
            "unconciousTotal", 0
        )  # "unconciousTotal" misspelled in XCOM save files
        self.shot_at_counter_total = diary_data.get("shotAtCounterTotal", 0)
        self.hit_counter_total = diary_data.get("hitCounterTotal", 0)
        self.shots_fired_counter_total = diary_data.get("shotsFiredCounterTotal", 0)
        self.shots_landed_counter_total = diary_data.get("shotsLandedCounterTotal", 0)
        self.times_wounded_total = diary_data.get("timesWoundedTotal", 0)
        self.stat_gain_total = diary_data.get("statGainTotal", 0)

        self.missions = [
            mission_data[mid] for mid in self.mission_id_list if mid in mission_data
        ]


class Mission:
    def __init__(self, mission_data):
        self.id = mission_data.get("id")
        self.name = mission_data.get("markerName")
        time_data = mission_data.get("time", {})
        self.time = (
            f"{time_data.get('day', 0):02d}/{time_data.get('month', 0):02d}/"
            f"{time_data.get('year', 0)}"
        )
        self.region = mission_data.get("region")
        self.type = mission_data.get("type")
        self.success = mission_data.get("success")
        self.alien_race = mission_data.get("alienRace")
        self.injuries = mission_data.get("injuryList", {})


class Base:
    def __init__(self, data, mission_data):
        self.name = data.get("name", "Unknown Base")
        self.lon = data.get("lon")
        self.lat = data.get("lat")

        # Facilities
        self.facilities = [Facility(f) for f in data.get("facilities", [])]

        # Soldiers (Create Soldier objects)
        self.soldiers = []
        if "soldiers" in data:
            for s in data["soldiers"]:
                self.soldiers.append(Soldier(s, self.name, mission_data))

        # Items in storage
        self.items = data.get("items", {})

        # Research
        self.research = [ResearchProject(r) for r in data.get("research", [])]

        # Manufacturing
        self.manufacturing = [
            ManufacturingProject(m) for m in data.get("productions", [])
        ]

        # Transfers
        self.transfers = []
        if "transfers" in data:
            for t in data["transfers"]:
                self.transfers.append(Transfer(t, mission_data))


class Facility:
    def __init__(self, data):
        self.type = data.get("type")
        self.x = data.get("x")
        self.y = data.get("y")
        self.build_time = data.get("buildTime", 0)  # Days remaining, 0 if built


class ResearchProject:
    def __init__(self, data):
        self.project = data.get("project")
        self.assigned = data.get("assigned", 0)
        self.spent = data.get("spent", 0)
        self.cost = data.get("cost", 0)


class ManufacturingProject:
    def __init__(self, data):
        self.item = data.get("item")
        self.assigned = data.get("assigned", 0)
        self.spent = data.get("spent", 0)
        self.amount = data.get("amount", 0)  # Amount ordered


class Transfer:
    def __init__(self, data, mission_data):
        self.hours = data.get("hours", 0)
        self.soldier = None
        self.item_id = None
        self.item_qty = 0

        if "soldier" in data:
            # Soldier transfer
            # Note: Soldier parsing needs base name, but it's in transit.
            # We can use "In Transit" or destination if known contextually (but here local).
            # The transfer list belongs to the *destination* base in the save file structure.
            self.soldier = Soldier(data["soldier"], "In Transit", mission_data)
        elif "itemId" in data:
            # Item transfer
            self.item_id = data.get("itemId")
            self.item_qty = data.get("itemQty", 0)


def read_missions(data_):
    missions_ = {}
    logger.info("Reading mission data...")
    if "missionStatistics" in data_:
        for m in data_["missionStatistics"]:
            missions_[m["id"]] = Mission(m)
    return missions_


def read_bases(data_, mission_data):
    bases_ = []
    logger.info("Reading base data...")
    if "bases" in data_:
        for b in data_["bases"]:
            bases_.append(Base(b, mission_data))
    return bases_


def read_soldiers(data_, mission_data):
    # Backward compatibility wrapper if we still simply need all soldiers list
    # But ideally valid usage is via read_bases now.
    # However, existing main.py uses this. Let's maintain it by extracting from bases.
    soldiers_ = []
    mission_participants = {}
    logger.info("Reading soldier data (flat list)...")

    # Extract from active bases
    if "bases" in data_:
        for base in data_["bases"]:
            try:
                for s in base["soldiers"]:
                    soldier_ = Soldier(s, base["name"], mission_data)
                    soldiers_.append(soldier_)
            except KeyError:
                pass

    # Extract dead soldiers
    if "deadSoldiers" in data_:
        for s in data_["deadSoldiers"]:
            soldier_ = Soldier(s, "KIA", mission_data)
            soldiers_.append(soldier_)

    # Create a map of mission IDs to participating soldiers
    for soldier in soldiers_:
        for mission_id in soldier.service_record.mission_id_list:
            if mission_id not in mission_participants:
                mission_participants[mission_id] = []
            mission_participants[mission_id].append(soldier)

    return soldiers_, mission_participants


def make_csv(soldiers_):
    csvlist = [
        [
            "ID",
            "Base",
            "Type",
            "Name",
            "Rank",
            "Missions",
            "Kills",
            "TUs",
            "Stamina",
            "Health",
            "Bravery",
            "Reactions",
            "Firing",
            "Throwing",
            "Strength",
            "PsiStrength",
            "PsiSkill",
            "Initial TUs",
            "Initial Stamina",
            "Initial Health",
            "Initial Bravery",
            "Initial Reactions",
            "Initial Firing",
            "Initial Throwing",
            "Initial Strength",
            "Initial PsiStrength",
            "Initial PsiSkill",
            "Recovery Info",
        ]
    ]
    for i in soldiers_:
        recovery_info = ""
        if i.recovery > 0:
            recovery_info = f"Wounded ({i.recovery} days)"
        if i.training:
            recovery_info += " Training" if not recovery_info else ", Training"
        if i.psi_training:
            recovery_info += " Psi Training" if not recovery_info else ", Psi Training"

        row = [
            i.id,
            i.base,
            i.type,
            i.name,
            i.rank,
            i.missions,
            i.kills,
            i.currentstats.tu,
            i.currentstats.stamina,
            i.currentstats.health,
            i.currentstats.bravery,
            i.currentstats.reactions,
            i.currentstats.firing,
            i.currentstats.throwing,
            i.currentstats.strength,
            i.currentstats.psistrength,
            i.currentstats.psiskill,
            i.initialstats.tu,
            i.initialstats.stamina,
            i.initialstats.health,
            i.initialstats.bravery,
            i.initialstats.reactions,
            i.initialstats.firing,
            i.initialstats.throwing,
            i.initialstats.strength,
            i.initialstats.psistrength,
            i.initialstats.psiskill,
            recovery_info,
        ]
        csvlist.append(row)
    return csvlist


def load_data_from_yaml(file_path, json_dump=False, section="game"):
    """
    Load data from a YAML file.
    :param file_path: Path to the YAML file.
    :param json_dump: Whether to dump the loaded data to a JSON file (debug).
    :param section: "game" to return the document with 'difficulty',
                    "meta" to return the document with 'name'.
    :return: The requested document dictionary.
    """
    logger.info(
        f'Loading data from "{os.path.basename(file_path)}" (section: {section})...'
    )

    found_data = None

    with open(file_path, encoding="utf-8") as file:
        # Load all documents; yaml.load_all returns a generator
        documents = list(yaml.safe_load_all(file))

    # Fail if not exactly 2 documents (healthy saves always have 2 documents)
    if len(documents) != 2:
        raise ValueError(
            f"Expected 2 YAML documents in {file_path}, found {len(documents)}"
        )

    for doc in documents:
        if not isinstance(doc, dict):
            continue

        if section == "game":
            if "difficulty" in doc:
                found_data = doc
                break
        elif section == "meta":
            if "name" in doc:
                found_data = doc
                break

    if found_data is None:
        # Fallback/Error handling: if we couldn't find the specific section,
        # checking if the file only had one document might be relevant,
        # but strictly adhering to the plan:
        raise ValueError(f"Could not find section '{section}' in {file_path}")

    if json_dump:
        logger.info('Writing converted json data to "data.json"...')
        with open("data.json", "w") as outfile:
            json.dump(found_data, outfile)

    return found_data
