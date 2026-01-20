import customtkinter as ctk


from views.main_menu import MainMenu
import reader
from views.soldier_list import SoldierListView
from views.soldier_view import SoldierView
from views.mission_view import MissionView
from views.base_view import BaseView


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OpenXCOM Soldier Stats")
        self.geometry("1024x768")
        self.save_data = None
        self.soldiers = []
        self.missions = {}
        self.mission_participants = {}

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
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(MainMenu)

    def show_frame(self, cont, *args):
        frame = self.frames[cont]
        if hasattr(frame, "update_view"):
            frame.update_view(*args)
        frame.tkraise()

    def load_save_file(self):
        file_path = "test/Test Save.sav"

        if file_path:
            print(f"Loading save file: {file_path}")
            self.save_data = reader.load_data_from_yaml(file_path)
            self.missions = reader.read_missions(self.save_data)
            self.soldiers, self.mission_participants = reader.read_soldiers(
                self.save_data, self.missions
            )

            # Enable buttons on main menu
            main_menu_frame = self.frames[MainMenu]
            main_menu_frame.soldiers_button.configure(state="normal")
            main_menu_frame.bases_button.configure(state="normal")
            print(
                f"Loaded {len(self.soldiers)} soldiers and {len(self.missions)} missions."
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
    app = App()
    app.mainloop()
