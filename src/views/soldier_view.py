import customtkinter as ctk

class SoldierView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_columnconfigure(1, weight=1) # Make the right column expandable

        # Name Banner (Top Left)
        self.name_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=24, weight="bold"))
        self.name_label.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")

        # Stats Frame (Left)
        stats_frame = ctk.CTkFrame(self)
        stats_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.stats_labels = {}

        stat_names = [
            "TUs", "Stamina", "Health", "Bravery", "Reactions", "Firing",
            "Throwing", "Strength", "Psi Strength", "Psi Skill"
        ]

        for i, stat in enumerate(stat_names):
            label = ctk.CTkLabel(stats_frame, text=f"{stat}:")
            label.grid(row=i, column=0, padx=10, pady=5, sticky="w")
            value = ctk.CTkLabel(stats_frame, text="")
            value.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            self.stats_labels[stat] = value

        # Inventory Frame (Right)
        inventory_frame = ctk.CTkFrame(self)
        inventory_frame.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")

        inventory_label = ctk.CTkLabel(inventory_frame, text="Inventory (Not Implemented)", font=ctk.CTkFont(size=16))
        inventory_label.pack(expand=True)

        # Back Button
        back_button = ctk.CTkButton(self, text="Back to Soldier List", command=self.back_to_list)
        back_button.grid(row=2, column=0, columnspan=2, padx=20, pady=20)

    def back_to_list(self):
        from views.soldier_list import SoldierListView
        self.controller.show_frame(SoldierListView)

    def update_view(self, soldier_id):
        soldier = self.controller.get_soldier_by_id(soldier_id)
        if not soldier:
            print(f"Error: Soldier with ID {soldier_id} not found.")
            self.back_to_list()
            return

        self.name_label.configure(text=f"{soldier.name} ({soldier.rank})")

        # Current Stats
        current_stats = soldier.currentstats
        self.stats_labels["TUs"].configure(text=current_stats.tu)
        self.stats_labels["Stamina"].configure(text=current_stats.stamina)
        self.stats_labels["Health"].configure(text=current_stats.health)
        self.stats_labels["Bravery"].configure(text=current_stats.bravery)
        self.stats_labels["Reactions"].configure(text=current_stats.reactions)
        self.stats_labels["Firing"].configure(text=current_stats.firing)
        self.stats_labels["Throwing"].configure(text=current_stats.throwing)
        self.stats_labels["Strength"].configure(text=current_stats.strength)
        self.stats_labels["Psi Strength"].configure(text=current_stats.psistrength)
        self.stats_labels["Psi Skill"].configure(text=current_stats.psiskill)
