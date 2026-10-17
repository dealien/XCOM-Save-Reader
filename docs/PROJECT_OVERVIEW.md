# XCOM Save Reader — Project Overview

> **Audience:** human contributors and AI coding agents.
> For end-user setup, see [README.md](../README.md). For vanilla binary file formats, see [VANILLA_BINARY_FORMATS.md](VANILLA_BINARY_FORMATS.md).

| | |
| --- | --- |
| **Repository** | [dealien/XCOM-Save-Reader](https://github.com/dealien/XCOM-Save-Reader) |
| **App title** | OpenXCOM Soldier Stats |
| **Language** | Python 3.10+ |
| **GUI toolkit** | CustomTkinter |
| **Default branch** | `main` |
| **License** | None yet (no `LICENSE` file in repo root) |

## Contents

1. [Purpose and Goals](#1-purpose-and-goals)
2. [Current Status](#2-current-status)
3. [Architecture](#3-architecture)
4. [Open Issues and Roadmap](#4-open-issues-and-roadmap)
5. [Contributor Guide](#5-contributor-guide)

---

## 1. Purpose and Goals

XCOM Save Reader is a Python desktop application and CLI utility that reads, parses, and visualizes save files from [OpenXcom](https://openxcom.org/) (the open-source re-implementation of *UFO: Enemy Unknown / X-COM: UFO Defense*), including OpenXcom Extended (OXCE) and modded games.

**Goals:**

- **Save file inspection** — Parse OpenXcom YAML saves (`.sav`) into domain objects and display them in a GUI.
- **Soldier analytics** — Rosters across all bases: initial vs. current `Stats`, rank, missions, kills, service records (`ServiceRecord`), and equipment layout.
- **Base and strategic tracking** — Facilities (`Facility`), research (`ResearchProject`), manufacturing (`ManufacturingProject`), and transfers (`Transfer`).
- **Mission history** — Mission logs (`Mission`), outcomes, and kill statistics.
- **Ruleset, mod, and localization integration** — Load vanilla and mod `.rul` rulesets and language files so internal IDs (e.g. `STR_SERGEANT`) resolve to readable names and sprites.
- **Data export** — Export soldier data to CSV (`make_csv` in `src/reader.py`).

---

## 2. Current Status

### Summary

- **Working:** End-to-end YAML save parser, ruleset cache, CLI, multi-view GUI, test suite, and Ruff CI.
- **Main limitation:** Only plain-text YAML rulesets (`.rul`, `.yaml`, `.yml`) and external image files (e.g. mod `extraSprites` PNGs) are supported. Vanilla binary assets (`.PCK`, `.TAB`, `.SPK`, `.BDY`, `.SCR`, `.DAT`) cannot be decoded yet. This blocks vanilla base layouts ([#26](https://github.com/dealien/XCOM-Save-Reader/issues/26)) and vanilla item/rank sprites ([#25](https://github.com/dealien/XCOM-Save-Reader/issues/25)). See [VANILLA_BINARY_FORMATS.md](VANILLA_BINARY_FORMATS.md).

### Feature Status

| Component | Status | Notes |
| --- | --- | --- |
| YAML save parser (`src/reader.py`) | ✅ Complete | Soldiers, stats, diaries, inventory, bases, facilities, research, manufacturing, transfers, missions; CSV export. |
| Ruleset & mod cache (`src/data_manager.py`) | ✅ Complete (backend) | `GameDataManager` indexes rulesets/mods with disk caching; cache dirs use `0o700` permissions ([PR #46](https://github.com/dealien/XCOM-Save-Reader/pull/46)). |
| Localization (`src/translation_manager.py`) | 🟡 Partial | Loads translations; not yet wired into all views (e.g. ranks, [#24](https://github.com/dealien/XCOM-Save-Reader/issues/24)). |
| Desktop GUI (`src/main.py`, `src/views/`) | 🟢 Functional | `MainMenu`, `SoldierList`, `SoldierView`, `BaseView`, `MissionView`, `SettingsView`. |
| CLI (`src/main.py`) | ✅ Complete | `save_file`, `--debug`, `--json-dump`, `--clear-cache` (see [Running](#running-the-app)). |
| Tests & linting (`test/`, `.github/workflows/ruff.yml`) | ✅ Complete | `pytest` + `pytest-cov`; Ruff in GitHub Actions. |
| TFTD support | ⏳ Planned | [#2](https://github.com/dealien/XCOM-Save-Reader/issues/2) |

---

## 3. Architecture

### Dependencies

Defined in `requirements.txt` and `pyproject.toml`:

| Purpose | Packages |
| --- | --- |
| GUI & rendering | `customtkinter`, `Pillow`, `darkdetect` |
| Parsing & CLI output | `PyYAML`, `colorama` |
| Testing & linting | `pytest`, `pytest-cov`, `coverage`, `ruff` |

### Directory Layout

```text
XCOM-Save-Reader/
├── .github/workflows/ruff.yml   # CI: Ruff lint checks
├── .vscode/                     # Editor settings and launch configs
├── docs/                        # Project documentation (this file)
├── reference/                   # Dev-only copy of game/mod files (common/, standard/, user/mods/); not shipped to end users
├── src/
│   ├── main.py                  # Entry point, CLI parser, root `App` window / view navigation
│   ├── reader.py                # .sav YAML parser + data models (Soldier, Base, Mission, ...)
│   ├── data_manager.py          # GameDataManager: ruleset/mod indexing and caching
│   ├── translation_manager.py   # TranslationManager: string ID -> localized text
│   ├── resource_manager.py      # ResourceManager: image/asset path resolution
│   ├── inventory_formatter.py   # Soldier equipment slot formatting
│   ├── config.py                # Config: persists preferences to user/config.json
│   ├── view_utils.py            # Shared UI helpers
│   └── views/
│       ├── main_menu.py         # Home screen and save loader
│       ├── soldier_list.py      # Table of all soldiers
│       ├── soldier_view.py      # Single-soldier dossier (stats, diary, equipment)
│       ├── base_view.py         # Facilities, research, manufacturing, transfers
│       ├── mission_view.py      # Mission history and kill summaries
│       └── settings_view.py     # Path and preference configuration
├── test/                        # pytest suite (one test_<module>.py per module) + Test Save.sav
├── user/                        # Runtime: config.json and ruleset cache
├── Copy Current Saves.bat       # Helper: copy saves from the game
└── Load Soldier List.bat        # Helper: launch the reader
```

### Data Flow

1. **YAML loading** — `.sav` files are YAML, usually two documents separated by `---` (header with version and mod load order, then campaign state). `src/reader.py` loads them with `yaml.safe_load`.
2. **Model hydration** — data is turned into model objects:
   - `read_bases()` → `Base` objects with nested `Facility`, `ResearchProject`, `ManufacturingProject`, `Transfer`, plus stationed soldiers.
   - `read_soldiers()` → `Soldier` objects with initial/current `Stats`, `ServiceRecord`, and inventory.
   - `read_missions()` → `Mission` records (alien race, mission/UFO type, location, kills).
3. **Ruleset & mod caching** — parsing every `.rul` file on each launch is slow, so `GameDataManager` writes a cache under `user/` (`0o700` permissions). Clear it with `--clear-cache`.
4. **Load order** — rulesets and translations load in this order: `common/` → `standard/` → mods (in the order listed in the save header). Later entries override earlier ones.

---

## 4. Open Issues and Roadmap

Snapshot of open [GitHub issues](https://github.com/dealien/XCOM-Save-Reader/issues), accurate as of **2026-10-15**. Check GitHub for the current list.

| Issue | Title | Notes |
| --- | --- | --- |
| [#27](https://github.com/dealien/XCOM-Save-Reader/issues/27) | Quick-load most recent save | Detect and load the newest `.sav` on startup or via a button. |
| [#26](https://github.com/dealien/XCOM-Save-Reader/issues/26) | Visual base layout using game images | 6×6 facility grid in `base_view.py`. **Blocked** by #25. |
| [#25](https://github.com/dealien/XCOM-Save-Reader/issues/25) | Load data from game and mod files | Loader exists in `data_manager.py`; still needs wiring into all views. |
| [#24](https://github.com/dealien/XCOM-Save-Reader/issues/24) | Display translated soldier rank | Use `TranslationManager` in `soldier_view.py`. Depends on #25. |
| [#10](https://github.com/dealien/XCOM-Save-Reader/issues/10) | Filter/search in soldier list | Search by name, base, or status in `soldier_list.py`. |
| [#9](https://github.com/dealien/XCOM-Save-Reader/issues/9) | Sorting in soldier list | Sort columns (rank, kills, missions, stats) in `soldier_list.py`. |
| [#4](https://github.com/dealien/XCOM-Save-Reader/issues/4) | Refactor soldier inventory display | `soldier_view.py`, `inventory_formatter.py`. |
| [#2](https://github.com/dealien/XCOM-Save-Reader/issues/2) | TFTD ruleset support | Extend `GameDataManager` and `reader.py`. |

**Good next tasks:** #24 (rank translation), #9 and #10 (sort/filter). All three are self-contained and the backend support already exists.

---

## 5. Contributor Guide

### Setup

Always use the project virtual environment (`.venv`). Do not use global Python.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Running the App

```powershell
.\.venv\Scripts\python.exe src/main.py [save_file] [-d] [-j] [--clear-cache]
```

| Argument | Description |
| --- | --- |
| `save_file` | Optional path to a save to load on startup. |
| `-d`, `--debug` | Auto-load `test/Test Save.sav`. |
| `-j`, `--json-dump` | Dump loaded save data to JSON. |
| `--clear-cache` | Clear the ruleset cache before loading. |

### Testing and Linting

Run these before every commit (CI enforces Ruff):

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=src
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
```

Each module in `src/` has a matching `test/test_<module>.py`.

### Conventions and Pitfalls

- **Assume keys may be missing.** OpenXcom leaves out empty keys (e.g. no `bases`, no `diary` for rookies, no `research`/`transfers`). Use `.get(key, default)` instead of `[key]`, and add tests for missing keys ([PR #45](https://github.com/dealien/XCOM-Save-Reader/pull/45)). Never assume two saves have the same structure.
- **Parse YAML safely.** Always use `yaml.safe_load`, never `yaml.load`. Cache directories under `user/` must use `0o700` permissions ([PR #46](https://github.com/dealien/XCOM-Save-Reader/pull/46)).
- **Keep caches fresh.** Caches must invalidate and regenerate automatically when rulesets change (e.g. modified/added/removed `.rul` files, mod updates, or a different mod load order). `--clear-cache` is a manual override, not the primary mechanism.
- **Keep views decoupled.** Views in `src/views/` talk to each other through the parent `App` (`src/main.py`) and helpers in `src/view_utils.py`. Test with the shared fixtures in `test/conftest.py`, using real `App` instances where possible ([PR #42](https://github.com/dealien/XCOM-Save-Reader/pull/42)).
- **Support every target.** Code must work with vanilla X-COM, OXCE, and user-installed mods.
- **Respect load order.** Rulesets and translations must follow the mod order in the save header.
