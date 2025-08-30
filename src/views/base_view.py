import customtkinter as ctk

class BaseView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        label = ctk.CTkLabel(self, text="Base View (Not Implemented)", font=ctk.CTkFont(size=20, weight="bold"))
        label.pack(pady=20, padx=20, expand=True)

        back_button = ctk.CTkButton(self, text="Back to Main Menu", command=self.back_to_menu)
        back_button.pack(pady=20)

    def back_to_menu(self):
        from src.views.main_menu import MainMenu
        self.controller.show_frame(MainMenu)
