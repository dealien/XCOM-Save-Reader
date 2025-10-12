import customtkinter as ctk

class BaseView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_columnconfigure(1, weight=1)

        # Back button
        back_button = ctk.CTkButton(self, text="←", command=self.back_to_menu, width=30)
        back_button.grid(row=0, column=0, padx=(20, 0), pady=20, sticky="w")

        label = ctk.CTkLabel(self, text="Base View (Not Implemented)", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=1, padx=20, pady=20, sticky="w")

    def back_to_menu(self):
        from views.main_menu import MainMenu
        self.controller.show_frame(MainMenu)
