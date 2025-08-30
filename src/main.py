import customtkinter as ctk
from tkinter import filedialog
import os

from views.main_menu import MainMenu
import reader
from views.soldier_list import SoldierListView
from views.soldier_view import SoldierView
from views.base_view import BaseView

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OpenXCOM Soldier Stats")
        self.geometry("1024x768")
        self.save_data = None
        self.soldiers = []

        # Set appearance mode
        ctk.set_appearance_mode("dark")

        # Container for all frames
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        # Initialize frames (will be uncommented as they are created)
        for F in (MainMenu, SoldierListView, SoldierView, BaseView):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(MainMenu)

    def show_frame(self, cont):
        frame = self.frames[cont]
        if hasattr(frame, 'update_view'):
            frame.update_view()
        frame.tkraise()

    def load_save_file(self):
        # In a real scenario, we'd use a file dialog.
        # For this headless environment, we'll hardcode the path.
        # initial_dir = os.path.join(os.getcwd(), 'user')
        # file_path = filedialog.askopenfilename(initialdir=initial_dir)

        file_path = 'test/Test Save.sav'

        if file_path:
            print(f"Loading save file: {file_path}")
            self.save_data = reader.load_data_from_yaml(file_path)
            self.soldiers = reader.read_soldiers(self.save_data)

            # Enable buttons on main menu
            main_menu_frame = self.frames[MainMenu]
            main_menu_frame.soldiers_button.configure(state="normal")
            main_menu_frame.bases_button.configure(state="normal") # Will be a placeholder
            print(f"Loaded {len(self.soldiers)} soldiers.")

    def get_soldier_by_id(self, soldier_id):
        # soldier_id from the treeview is a string, but soldier.id is an int.
        try:
            sid = int(soldier_id)
            for soldier in self.soldiers:
                if soldier.id == sid:
                    return soldier
        except ValueError:
            pass
        return None

    def show_soldier_view(self, soldier_id):
        frame = self.frames[SoldierView]
        frame.update_view(soldier_id)
        frame.tkraise()


if __name__ == "__main__":
    app = App()
    app.mainloop()
