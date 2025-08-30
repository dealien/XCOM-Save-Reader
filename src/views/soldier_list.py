import customtkinter as ctk
from tkinter import ttk
from tkinter import font as tkFont

class SoldierListView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Title
        label = ctk.CTkLabel(self, text="Soldier List", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        # Treeview for soldier data
        self.tree = self.create_treeview()
        self.tree.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)

        # Back Button
        back_button = ctk.CTkButton(self, text="Back to Main Menu", command=self.back_to_menu)
        back_button.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

    def create_treeview(self):
        # Using ttk.Treeview, need to style it for dark theme
        style = ttk.Style()
        style.theme_use("default")

        # Style for Treeview
        style.configure("Treeview",
                        background="#2a2d2e",
                        foreground="white",
                        rowheight=25,
                        fieldbackground="#343638",
                        bordercolor="#343638",
                        borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559b')])

        # Style for Treeview Heading
        style.configure("Treeview.Heading",
                        background="#565b5e",
                        foreground="white",
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[('active', '#3484F0')])

        tree = ttk.Treeview(self)
        return tree

    def back_to_menu(self):
        from views.main_menu import MainMenu
        self.controller.show_frame(MainMenu)

    def update_view(self):
        # Clear existing data
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Get data from controller
        soldiers = self.controller.soldiers
        if not soldiers:
            return

        # Define columns
        columns = ['ID', 'Name', 'Rank', 'Missions', 'Kills', 'Base']
        self.tree["columns"] = columns

        # Configure columns
        for col in columns:
            self.tree.heading(col, text=col, anchor="w")
            # Set stretch=False for all columns except 'Name'
            if col == 'Name':
                self.tree.column(col, anchor="w", stretch=True, minwidth=150)
            else:
                self.tree.column(col, anchor="center", stretch=False, width=80, minwidth=60)

        # Insert data
        for soldier in soldiers:
            values = [soldier.id, soldier.name, soldier.rank, soldier.missions, soldier.kills, soldier.base]
            self.tree.insert("", "end", values=values, iid=soldier.id)

        # Add event handler for row selection
        self.tree.bind('<<TreeviewSelect>>', self.on_soldier_select)

    def on_soldier_select(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            soldier_id = selected_item[0]
            self.controller.show_soldier_view(soldier_id)
