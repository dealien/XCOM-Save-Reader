import customtkinter as ctk
from tkinter import ttk
from tkinter import font as tkFont


class SoldierListView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.sort_column = "Name"  # Default sort column
        self.sort_reverse = False
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Back button
        back_button = ctk.CTkButton(self, text="←", command=self.back_to_menu, width=30)
        back_button.grid(row=0, column=0, padx=(20, 0), pady=20, sticky="w")

        # Title
        label = ctk.CTkLabel(self, text="Soldier List", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=1, padx=20, pady=20, sticky="w")

        # Treeview for soldier data
        self.tree = self.create_treeview()
        self.tree.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)

    def create_treeview(self):
        # Using ttk.Treeview, need to style it for dark theme
        style = ttk.Style()
        style.theme_use("default")

        # Colors
        bg_color = "#2b2b2b"
        fg_color = "white"
        selected_color = "#1f538d"
        header_bg = "#3a3d42"
        header_fg = "white"
        
        # Style for Treeview
        # Increase row height and use a larger font
        style.configure("Treeview",
                        background=bg_color,
                        foreground=fg_color,
                        rowheight=35,
                        fieldbackground=bg_color,
                        bordercolor=bg_color,
                        borderwidth=0,
                        font=("Roboto", 11))
        
        style.map('Treeview', 
                  background=[('selected', selected_color)],
                  foreground=[('selected', 'white')])

        # Style for Treeview Heading
        style.configure("Treeview.Heading",
                        background=header_bg,
                        foreground=header_fg,
                        relief="flat",
                        font=("Roboto", 11, "bold"),
                        padding=(10, 5))
                        
        style.map("Treeview.Heading",
                  background=[('active', '#4a4e54')])

        tree = ttk.Treeview(self, show='headings')
        
        # Configure alternating row colors
        tree.tag_configure('odd', background='#2b2b2b')
        tree.tag_configure('even', background='#323538')
        
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
            self.tree.heading(col, text=col, anchor="w", command=lambda c=col: self.sort_by_column(c))
            if col == 'Name':
                self.tree.column(col, anchor="w", stretch=True, minwidth=150)
            elif col == 'Base':
                self.tree.column(col, anchor="w", stretch=True, minwidth=100)
            else:
                self.tree.column(col, anchor="w", stretch=False, width=80, minwidth=60)

        # Insert data with striped rows
        for i, soldier in enumerate(soldiers):
            values = [soldier.id, soldier.name, soldier.rank, soldier.missions, soldier.kills, soldier.base]
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert("", "end", values=values, iid=soldier.id, tags=(tag,))

        # Add event handler for row selection
        self.tree.bind('<<TreeviewSelect>>', self.on_soldier_select)

    def sort_by_column(self, col):
        # Determine sort order
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
        self.sort_column = col

        # Get data from treeview
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]

        # Sort data
        # Attempt to convert to a number for sorting, otherwise use string
        try:
            data.sort(key=lambda t: float(t[0]), reverse=self.sort_reverse)
        except ValueError:
            data.sort(key=lambda t: t[0], reverse=self.sort_reverse)

        # Repopulate treeview
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)

    def on_soldier_select(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            soldier_id = selected_item[0]
            self.controller.show_soldier_view(soldier_id)
