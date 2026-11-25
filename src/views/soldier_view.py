import logging
from functools import partial

import customtkinter as ctk

import view_utils
from inventory_formatter import format_inventory_entries

# Configure logger for this module
logger = logging.getLogger(__name__)


class SoldierView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_columnconfigure(2, weight=1)  # Make the inventory column expandable

        # Back Button
        back_button = ctk.CTkButton(self, text="←", command=self.back_to_list, width=30)
        back_button.grid(row=0, column=0, padx=(20, 0), pady=20, sticky="w")

        # Name & Rank Banner (Top Left)
        name_banner = ctk.CTkFrame(self, fg_color="transparent")
        name_banner.grid(row=0, column=1, columnspan=2, padx=20, pady=20, sticky="w")
        self.rank_icon_label = ctk.CTkLabel(name_banner, text="")
        self.rank_icon_label.pack(side="left", padx=(0, 10))
        self.name_label = ctk.CTkLabel(
            name_banner, text="", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.name_label.pack(side="left")

        # Stats Frame (Left)
        stats_frame = ctk.CTkFrame(self)
        stats_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew")
        self.stats_labels = {}

        stat_names = [
            "TUs",
            "Stamina",
            "Health",
            "Bravery",
            "Reactions",
            "Firing",
            "Throwing",
            "Strength",
            "Psi Strength",
            "Psi Skill",
        ]

        for i, stat in enumerate(stat_names):
            label = ctk.CTkLabel(stats_frame, text=f"{stat}:")
            label.grid(row=i, column=0, padx=10, pady=5, sticky="w")
            value = ctk.CTkLabel(stats_frame, text="")
            value.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            self.stats_labels[stat] = value

        # Soldier Sprite Frame (Center, between Stats and Inventory)
        sprite_frame = ctk.CTkFrame(self)
        sprite_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.soldier_sprite_label = ctk.CTkLabel(sprite_frame, text="")
        self.soldier_sprite_label.pack(expand=True, padx=15, pady=15)

        # Inventory Frame (Right)
        self.inventory_frame = ctk.CTkScrollableFrame(self, label_text="Inventory")
        self.inventory_frame.grid(
            row=1, column=2, padx=(10, 20), pady=10, sticky="nsew"
        )
        self.inventory_frame.grid_columnconfigure(0, weight=1)

        # Service Record Frame (Bottom, spanning all columns)
        service_record_frame = ctk.CTkFrame(self)
        service_record_frame.grid(
            row=2, column=0, columnspan=3, padx=20, pady=10, sticky="nsew"
        )
        service_record_frame.grid_columnconfigure((0, 1), weight=1)

        service_record_label = ctk.CTkLabel(
            service_record_frame,
            text="Service Record",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        service_record_label.grid(
            row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        # Service Record Info (Left Column)
        service_record_info_frame = ctk.CTkFrame(service_record_frame)
        service_record_info_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Mission History (Right Column)
        self.mission_history_frame = ctk.CTkScrollableFrame(
            service_record_frame, height=200, label_text="Mission History"
        )
        self.mission_history_frame.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        self.service_record_summary_label = ctk.CTkLabel(
            service_record_info_frame, text="", justify="left"
        )
        self.service_record_summary_label.pack(anchor="w", padx=10, pady=5)

        self.commendations_label = ctk.CTkLabel(
            service_record_info_frame, text="", justify="left"
        )
        self.commendations_label.pack(anchor="w", padx=10, pady=5)

    def back_to_list(self):
        from views.soldier_list import SoldierListView

        target_view = getattr(self, "previous_view", SoldierListView)
        if target_view is None:
            target_view = SoldierListView

        self.controller.show_frame(target_view)

    def on_mission_card_click(self, mission_id, soldier_id, event):
        self.controller.show_mission_view(mission_id, soldier_id)

    def update_view(self, soldier_id, previous_view=None):
        self.previous_view = previous_view

        soldier = self.controller.get_soldier_by_id(soldier_id)
        if not soldier:
            logger.error(f"Error: Soldier with ID {soldier_id} not found.")
            self.back_to_list()
            return

        tr = self.controller.translation_manager.get
        rank_key = self.controller.translation_manager.get_rank_string(
            soldier.rank, getattr(soldier, "type", "STR_SOLDIER")
        )
        self.name_label.configure(text=f"{soldier.name} ({tr(rank_key)})")

        rm = getattr(self.controller, "resource_manager", None)
        rank_sprite = (
            rm.get_rank_sprite(soldier.rank, getattr(soldier, "type", None))
            if rm is not None
            else None
        )
        self.rank_icon_label.configure(image=rank_sprite)

        soldier_sprite = (
            rm.get_soldier_sprite(soldier, ctk_image=True, size=(160, 200))
            if rm is not None
            else None
        )
        self.soldier_sprite_label.configure(image=soldier_sprite)

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
        summary = view_utils.format_service_record_summary(sr)
        self.service_record_summary_label.configure(text=summary)

        # Cause of death
        death_text = view_utils.format_death_info(soldier.death_info, tr)
        if death_text:
            current_text = self.service_record_summary_label.cget("text")
            self.service_record_summary_label.configure(text=current_text + death_text)

        commendations_text = (
            "Commendations:\n"
            + "\n".join(
                [
                    f"{tr(c['commendationName'])} (Level: {c['decorationLevel']})"
                    for c in sr.commendations
                ]
            )
            if sr.commendations
            else "No commendations."
        )
        self.commendations_label.configure(text=commendations_text)

        # Update inventory
        # Clear old inventory items
        for widget in self.inventory_frame.winfo_children():
            widget.destroy()

        inventory_data = format_inventory_entries(
            getattr(soldier, "equipmentLayout", None), translator=tr
        )

        if inventory_data:
            row = 0
            for slot, entries in sorted(inventory_data.items()):
                slot_label = ctk.CTkLabel(
                    self.inventory_frame,
                    text=slot,
                    font=ctk.CTkFont(size=14, weight="bold"),
                )
                slot_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
                row += 1
                for entry in entries:
                    item_row = ctk.CTkFrame(
                        self.inventory_frame, fg_color="transparent"
                    )
                    item_row.grid(row=row, column=0, padx=20, pady=2, sticky="w")
                    item_sprite = (
                        rm.get_item_sprite(entry["item_type"], size=(24, 36))
                        if rm is not None
                        else None
                    )
                    if item_sprite is not None:
                        ctk.CTkLabel(item_row, text="", image=item_sprite).pack(
                            side="left", padx=(0, 6)
                        )
                    item_label = ctk.CTkLabel(item_row, text=entry["text"])
                    item_label.pack(side="left")
                    row += 1
        else:
            no_inventory_label = ctk.CTkLabel(
                self.inventory_frame, text="No inventory."
            )
            no_inventory_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Clear old mission cards
        for widget in self.mission_history_frame.winfo_children():
            widget.destroy()

        if sr.missions:
            # Pre-calculate kill counts per mission ID for better performance
            kills_per_mission = {}
            for kill in sr.kill_list:
                m_id = kill.get("mission")
                kills_per_mission[m_id] = kills_per_mission.get(m_id, 0) + 1

            for mission in sr.missions:
                card = ctk.CTkFrame(self.mission_history_frame, border_width=1)
                card.pack(fill="x", expand=True, padx=5, pady=5)

                kill_count = kills_per_mission.get(mission.id, 0)

                card_title = f"{tr(mission.name)} - {mission.time}"
                card_result = f"Result: {'Success' if mission.success else 'Failure'}"
                card_kills = f"Kills: {kill_count}"

                title_label = ctk.CTkLabel(
                    card, text=card_title, font=ctk.CTkFont(weight="bold")
                )
                title_label.pack(anchor="w", padx=10, pady=(5, 0))

                result_label = ctk.CTkLabel(card, text=card_result)
                result_label.pack(anchor="w", padx=10)

                kills_label = ctk.CTkLabel(card, text=card_kills)
                kills_label.pack(anchor="w", padx=10, pady=(0, 5))

                # Check for death in this mission
                death_label = None
                if (
                    soldier.death_info
                    and soldier.death_info.get("cause", {}).get("mission") == mission.id
                ):
                    death_detail = view_utils.format_mission_death_detail(
                        soldier.death_info, tr
                    )
                    death_label = ctk.CTkLabel(
                        card, text=death_detail, text_color="#ff5555"
                    )
                    death_label.pack(anchor="w", padx=10, pady=(0, 5))

                # Bind click event to the card and its labels
                click_handler = partial(
                    self.on_mission_card_click, mission.id, soldier.id
                )
                card.bind("<Button-1>", click_handler)
                title_label.bind("<Button-1>", click_handler)
                result_label.bind("<Button-1>", click_handler)
                kills_label.bind("<Button-1>", click_handler)
                if death_label:
                    death_label.bind("<Button-1>", click_handler)
        else:
            no_missions_label = ctk.CTkLabel(
                self.mission_history_frame, text="No mission history."
            )
            no_missions_label.pack(padx=10, pady=10)
