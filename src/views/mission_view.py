import customtkinter as ctk


class MissionView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.from_soldier_id = None

        self.grid_columnconfigure(0, weight=1)

        # Mission Name Banner
        self.mission_name_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.mission_name_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Mission Details Frame
        details_frame = ctk.CTkFrame(self)
        details_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.mission_date_label = ctk.CTkLabel(details_frame, text="")
        self.mission_date_label.pack(anchor="w", padx=10, pady=2)

        self.mission_type_label = ctk.CTkLabel(details_frame, text="")
        self.mission_type_label.pack(anchor="w", padx=10, pady=2)

        self.mission_region_label = ctk.CTkLabel(details_frame, text="")
        self.mission_region_label.pack(anchor="w", padx=10, pady=2)

        self.mission_result_label = ctk.CTkLabel(details_frame, text="")
        self.mission_result_label.pack(anchor="w", padx=10, pady=2)

        self.alien_race_label = ctk.CTkLabel(details_frame, text="")
        self.alien_race_label.pack(anchor="w", padx=10, pady=2)

        # Participants Frame
        participants_frame = ctk.CTkFrame(self)
        participants_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        participants_frame.grid_columnconfigure(0, weight=1)

        participants_label = ctk.CTkLabel(
            participants_frame,
            text="Mission Participants",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        participants_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.participants_textbox = ctk.CTkTextbox(participants_frame, height=150)
        self.participants_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.participants_textbox.configure(state="disabled")

        # Back Button
        back_button = ctk.CTkButton(
            self, text="Back to Soldier View", command=self.back_to_soldier
        )
        back_button.grid(row=3, column=0, padx=20, pady=20)

    def back_to_soldier(self):
        from views.soldier_view import SoldierView

        self.controller.show_frame(SoldierView, self.from_soldier_id)

    def update_view(self, mission_id, from_soldier_id):
        self.from_soldier_id = from_soldier_id

        mission = self.controller.get_mission_by_id(mission_id)
        participants = self.controller.get_mission_participants(mission_id)

        if not mission:
            print(f"Error: Mission with ID {mission_id} not found.")
            self.back_to_soldier()
            return

        self.mission_name_label.configure(text=mission.name)
        self.mission_date_label.configure(text=f"Date: {mission.time}")
        self.mission_type_label.configure(text=f"Type: {mission.type}")
        self.mission_region_label.configure(text=f"Region: {mission.region}")
        self.mission_result_label.configure(
            text=f"Result: {'Success' if mission.success else 'Failure'}"
        )
        self.alien_race_label.configure(text=f"Enemy: {mission.alien_race}")

        self.participants_textbox.configure(state="normal")
        self.participants_textbox.delete("1.0", "end")

        if participants:
            participant_info = []
            for p in participants:
                status = "Survived"
                # Check for injuries (key in injuries dict is soldier id)
                if mission.injuries and p.id in mission.injuries:
                    days = mission.injuries[p.id]
                    status = f"Wounded ({days} days)"

                # Check for death
                if (
                    p.death_info
                    and p.death_info.get("cause", {}).get("mission") == mission.id
                ):
                    cause = p.death_info.get("cause", {})
                    status = (
                        f"KIA ({cause.get('weapon', 'Unknown')} "
                        f"[{cause.get('race', 'Unknown')}])"
                    )

                participant_info.append(f"{p.name} - {status}")

            self.participants_textbox.insert("1.0", "\n".join(participant_info))
        else:
            self.participants_textbox.insert("1.0", "No participant data found.")

        self.participants_textbox.configure(state="disabled")
