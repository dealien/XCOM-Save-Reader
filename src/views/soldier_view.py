import customtkinter as ctk
from functools import partial

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
        self.inventory_frame = ctk.CTkFrame(self)
        self.inventory_frame.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        self.inventory_frame.grid_columnconfigure(0, weight=1)

        # Service Record Frame (Bottom, spanning both columns)
        service_record_frame = ctk.CTkFrame(self)
        service_record_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        service_record_frame.grid_columnconfigure((0, 1), weight=1)

        service_record_label = ctk.CTkLabel(service_record_frame, text="Service Record", font=ctk.CTkFont(size=16, weight="bold"))
        service_record_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Service Record Info (Left Column)
        service_record_info_frame = ctk.CTkFrame(service_record_frame)
        service_record_info_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Mission History (Right Column)
        self.mission_history_frame = ctk.CTkScrollableFrame(service_record_frame, height=200, label_text="Mission History")
        self.mission_history_frame.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        self.service_record_summary_label = ctk.CTkLabel(service_record_info_frame, text="", justify="left")
        self.service_record_summary_label.pack(anchor="w", padx=10, pady=5)

        self.commendations_label = ctk.CTkLabel(service_record_info_frame, text="", justify="left")
        self.commendations_label.pack(anchor="w", padx=10, pady=5)

        # Back Button
        back_button = ctk.CTkButton(self, text="Back to Soldier List", command=self.back_to_list)
        back_button.grid(row=3, column=0, columnspan=2, padx=20, pady=20)

    def back_to_list(self):
        from views.soldier_list import SoldierListView
        self.controller.show_frame(SoldierListView)

    def on_mission_card_click(self, mission_id, soldier_id, event):
        self.controller.show_mission_view(mission_id, soldier_id)

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

        # Service Record
        sr = soldier.service_record
        summary = (
            f"Months of Service: {sr.months_service}\n"
            f"Days Wounded: {sr.days_wounded_total} (Wounded {sr.times_wounded_total} times)\n"
            f"Times Unconscious: {sr.unconscious_total}\n"
            f"Shots Fired: {sr.shots_fired_counter_total} | Shots Landed: {sr.shots_landed_counter_total}\n"
            f"Times Shot At: {sr.shot_at_counter_total} | Times Hit: {sr.hit_counter_total}"
        )
        self.service_record_summary_label.configure(text=summary)

        commendations_text = "Commendations:\n" + "\n".join([f"{c['commendationName']} (Level: {c['decorationLevel']})" for c in sr.commendations]) if sr.commendations else "No commendations."
        self.commendations_label.configure(text=commendations_text)

        # Update inventory
        for widget in self.inventory_frame.winfo_children():
            widget.destroy()

        inventory_label = ctk.CTkLabel(self.inventory_frame, text="Inventory", font=ctk.CTkFont(size=16, weight="bold"))
        inventory_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        if soldier.equipmentLayout:
            inventory_by_slot = {}
            for item in soldier.equipmentLayout:
                slot = item.get("slot", "Unslotted")
                if slot not in inventory_by_slot:
                    inventory_by_slot[slot] = []
                inventory_by_slot[slot].append(item)

            row = 1
            for slot, items in sorted(inventory_by_slot.items()):
                slot_label = ctk.CTkLabel(self.inventory_frame, text=slot, font=ctk.CTkFont(size=14, weight="bold"))
                slot_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
                row += 1
                for item in items:
                    item_text = f"  - {item['itemType']}"
                    if "ammoItemSlots" in item and isinstance(item["ammoItemSlots"], list):
                        ammo_text = ", ".join(item["ammoItemSlots"])
                        item_text += f" (Loaded with: {ammo_text})"
                    elif "ammoItem" in item:
                        item_text += f" (Loaded with: {item['ammoItem']})"

                    if "fuseTimer" in item and item['fuseTimer'] is not None:
                        item_text += f" Active ({item['fuseTimer']})"

                    item_label = ctk.CTkLabel(self.inventory_frame, text=item_text)
                    item_label.grid(row=row, column=0, padx=20, pady=2, sticky="w")
                    row += 1
        else:
            no_inventory_label = ctk.CTkLabel(self.inventory_frame, text="No inventory.")
            no_inventory_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")


        # Clear old mission cards
        for widget in self.mission_history_frame.winfo_children():
            widget.destroy()

        if sr.missions:
            for mission in sr.missions:
                card = ctk.CTkFrame(self.mission_history_frame, border_width=1)
                card.pack(fill="x", expand=True, padx=5, pady=5)

                kill_count = len([k for k in sr.kill_list if k['mission'] == mission.id])

                card_title = f"{mission.name} - {mission.time}"
                card_result = f"Result: {'Success' if mission.success else 'Failure'}"
                card_kills = f"Kills: {kill_count}"

                title_label = ctk.CTkLabel(card, text=card_title, font=ctk.CTkFont(weight="bold"))
                title_label.pack(anchor="w", padx=10, pady=(5, 0))

                result_label = ctk.CTkLabel(card, text=card_result)
                result_label.pack(anchor="w", padx=10)

                kills_label = ctk.CTkLabel(card, text=card_kills)
                kills_label.pack(anchor="w", padx=10, pady=(0, 5))

                # Bind click event to the card and its labels
                click_handler = partial(self.on_mission_card_click, mission.id, soldier.id)
                card.bind("<Button-1>", click_handler)
                title_label.bind("<Button-1>", click_handler)
                result_label.bind("<Button-1>", click_handler)
                kills_label.bind("<Button-1>", click_handler)
        else:
            no_missions_label = ctk.CTkLabel(self.mission_history_frame, text="No mission history.")
            no_missions_label.pack(padx=10, pady=10)
