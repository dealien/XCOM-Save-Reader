import customtkinter as ctk


class MainMenu(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        label = ctk.CTkLabel(
            self, text="Main Menu", font=ctk.CTkFont(size=20, weight="bold")
        )
        label.pack(pady=20)

        load_button = ctk.CTkButton(self, text="Load Save File", command=self.load_save)
        load_button.pack(pady=10)

        self.soldiers_button = ctk.CTkButton(
            self, text="View Soldiers", state="disabled", command=self.show_soldiers
        )
        self.soldiers_button.pack(pady=10)

        self.bases_button = ctk.CTkButton(
            self, text="View Bases", state="disabled", command=self.show_bases
        )
        self.bases_button.pack(pady=10)

        quit_button = ctk.CTkButton(self, text="Quit", command=controller.quit)
        quit_button.pack(pady=10)

    def load_save(self):
        self.controller.load_save_file()

    def show_soldiers(self):
        from views.soldier_list import SoldierListView

        self.controller.show_frame(SoldierListView)

    def show_bases(self):
        from views.base_view import BaseView

        self.controller.show_frame(BaseView)
