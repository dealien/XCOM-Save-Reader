# OpenXCOM Soldier Stats

A tool to read OpenXCOM save files and display statistics about your soldiers and bases.

## Setup

1. Ensure you have Python 3.10+ installed.
2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

```bash
python src/main.py [save_file] [-d] [-j] [--clear-cache]
```

This will launch the application and open the main menu.

### Command Line Options

| Argument | Description |
| --- | --- |
| `save_file` | Path to a save file to load on startup (optional). |
| `-d`, `--debug` | Auto-load `test/Test Save.sav` for quick debugging. |
| `-j`, `--json-dump` | Dump the loaded save data to `data.json`. |
| `--clear-cache` | Clear the ruleset cache before loading. |

If no save file is provided and `-d` is not set, the application will prompt you with a file selection dialog when you click "Load Save File".
