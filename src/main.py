import logging
import os

import customtkinter as ctk

import reader
from translation_manager import TranslationManager
from views.base_view import BaseView
from views.main_menu import MainMenu
from views.mission_view import MissionView
from views.soldier_list import SoldierListView
from views.soldier_view import SoldierView

# Configure logger for this module
logger = logging.getLogger(__name__)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OpenXCOM Soldier Stats")
        self.geometry("1024x768")
        self.save_data = None
        self.soldiers = []
        self.missions = {}
        self.mission_participants = {}

        # Initialize TranslationManager
        resource_path = self._find_resource_path()
        self.translation_manager = TranslationManager(resource_path)
        self.translation_manager.index_mods()

        # Set appearance mode
        ctk.set_appearance_mode("dark")

        # Container for all frames
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        # Initialize frames
        for F in (MainMenu, SoldierListView, SoldierView, MissionView, BaseView):
            # Pass translation_manager to all views
            # (Requires views to accept **kwargs or specific arg)
            # Modifying views to accept app as main controller,
            # so accessing app.translation_manager is cleaner
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(MainMenu)

    def _find_resource_path(self):
        """
        Locates the directory containing game resources ('common', 'standard', etc.).
        Searches:
        1. Adjacent to this script (Production/Flat layout)
        2. Parent directory (Source layout)
        3. '../reference' from parent (Development layout)
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)

        candidates = [
            script_dir,  # Production: resources next to executable/script
            parent_dir,  # Source root: resources in project root
            os.path.join(parent_dir, "reference"),  # Dev: resources in reference/
        ]

        for path in candidates:
            if os.path.isdir(os.path.join(path, "common")):
                logger.info(f"Found game resources at: {path}")
                return path

        logger.warning("Could not find game resources in standard locations.")
        # Fallback to dev path to avoid immediate crash,
        # though it will likely fail later
        return os.path.join(parent_dir, "reference")

    def show_frame(self, cont, *args):
        frame = self.frames[cont]
        if hasattr(frame, "update_view"):
            frame.update_view(*args)
        frame.tkraise()

    def load_save_file(self):
        file_path = "test/Test Save.sav"

        if file_path:
            logger.info(f"Loading save file: {file_path}")

            mod_list = []
            # Load metadata to get mods list
            try:
                metadata = reader.load_data_from_yaml(file_path, section="meta")
                mod_list = metadata.get("mods", [])
                logger.info(
                    f"Index found {len(mod_list)} mods. Loading translations..."
                )
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                from tkinter import messagebox

                messagebox.showwarning(
                    "Metadata Error",
                    f"Could not load save metadata/mods list.\nError: {e}\n\n"
                    "Translations may be incomplete.",
                )

            # Load translations (safe to call with empty list)
            try:
                self.translation_manager.load_all(mod_list)
            except Exception as e:
                logger.error(f"Error loading translations: {e}")
                from tkinter import messagebox

                messagebox.showwarning(
                    "Translation Error",
                    f"Could not load translations.\nError: {e}",
                )

            # Load game data
            try:
                self.save_data = reader.load_data_from_yaml(file_path, section="game")
                self.missions = reader.read_missions(self.save_data)
                self.bases = reader.read_bases(self.save_data, self.missions)
                self.soldiers, self.mission_participants = reader.read_soldiers(
                    self.save_data, self.missions
                )

                # Enable buttons on main menu
                main_menu_frame = self.frames[MainMenu]
                main_menu_frame.soldiers_button.configure(state="normal")
                main_menu_frame.bases_button.configure(state="normal")
                logger.info(
                    f"Loaded {len(self.bases)} bases, {len(self.soldiers)} soldiers and "
                    f"{len(self.missions)} missions."
                )
            except Exception as e:
                logger.error(f"Error loading game data: {e}")
                from tkinter import messagebox

                messagebox.showerror(
                    "Load Error",
                    f"Could not load save game data.\nError: {e}",
                )

    def get_soldier_by_id(self, soldier_id):
        try:
            sid = int(soldier_id)
            for soldier in self.soldiers:
                if soldier.id == sid:
                    return soldier
        except (ValueError, TypeError):
            pass
        return None

    def get_mission_by_id(self, mission_id):
        return self.missions.get(mission_id)

    def get_mission_participants(self, mission_id):
        return self.mission_participants.get(mission_id, [])

    def show_soldier_view(self, soldier_id):
        self.show_frame(SoldierView, soldier_id)

    def show_mission_view(self, mission_id, from_soldier_id):
        self.show_frame(MissionView, mission_id, from_soldier_id)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app = App()
    app.mainloop()
