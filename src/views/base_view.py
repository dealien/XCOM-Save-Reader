import logging

import customtkinter as ctk

logger = logging.getLogger(__name__)


class BaseView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Configure grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header Frame
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(2, weight=1)

        # Back Button
        back_btn = ctk.CTkButton(header, text="←", width=30, command=self.back_to_menu)
        back_btn.grid(row=0, column=0, padx=(0, 20))

        # Title
        self.title_label = ctk.CTkLabel(
            header, text="Base Overview", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=1)

        # Base Selector
        self.base_selector = ctk.CTkOptionMenu(header, command=self.on_base_select)
        self.base_selector.grid(row=0, column=3, padx=10)

        # Content Area (Tab View)
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Tabs
        self.tab_overview = self.tab_view.add("Overview")
        self.tab_soldiers = self.tab_view.add("Soldiers")
        self.tab_storage = self.tab_view.add("Storage")
        self.tab_research = self.tab_view.add("Research")
        self.tab_manufacturing = self.tab_view.add("Manufacturing")
        self.tab_transfers = self.tab_view.add("Transfers")

        # Current Base Data matches
        self.current_base = None

    def update_view(self):
        # Populate base selector
        bases = self.controller.bases
        if not bases:
            self.base_selector.set("No Bases Found")
            self.base_selector.configure(state="disabled")
            return

        base_names = [b.name for b in bases]
        self.base_selector.configure(values=base_names, state="normal")

        # Select first base if none selected or not in list
        current_selection = self.base_selector.get()
        if not self.current_base or self.current_base.name not in base_names:
            self.base_selector.set(base_names[0])
            self.on_base_select(base_names[0])
        else:
            # Refresh current view
            self.render_base_details(self.current_base)

    def on_base_select(self, base_name):
        for b in self.controller.bases:
            if b.name == base_name:
                self.current_base = b
                self.render_base_details(b)
                break

    def render_base_details(self, base):
        self.render_overview(base)
        self.render_soldiers(base)
        self.render_storage(base)
        self.render_research(base)
        self.render_manufacturing(base)
        self.render_transfers(base)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def render_overview(self, base):
        frame = self.tab_overview
        self.clear_frame(frame)

        # Facilities List (Scrollable)
        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            scroll, text="Facilities", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=5)

        # Simple list of facilities for now
        # Could grouping by type count? e.g. "Living Quarters x3"
        counts = {}
        for f in base.facilities:
            if f.type:
                ftype = self.controller.translation_manager.get(f.type)
                counts[ftype] = counts.get(ftype, 0) + 1

        for ftype, count in counts.items():
            ctk.CTkLabel(scroll, text=f"{ftype}: {count}").pack(anchor="w", padx=10)

    def render_soldiers(self, base):
        frame = self.tab_soldiers
        self.clear_frame(frame)

        total = len(base.soldiers)
        wounded = sum(1 for s in base.soldiers if s.recovery > 0)
        training = sum(1 for s in base.soldiers if s.training)
        psi_training = sum(1 for s in base.soldiers if s.psi_training)
        active = total - wounded  # Approximate, overlapping statuses possible?

        ctk.CTkLabel(
            frame,
            text=f"Total Soldiers: {total}",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=10)

        stats_frame = ctk.CTkFrame(frame)
        stats_frame.pack(fill="x", padx=20)

        ctk.CTkLabel(stats_frame, text=f"Active: {active} (Approx)").pack(
            side="left", expand=True, padx=5
        )
        ctk.CTkLabel(
            stats_frame,
            text=f"Wounded: {wounded}",
            text_color="orange" if wounded > 0 else "gray",
        ).pack(side="left", expand=True, padx=5)
        ctk.CTkLabel(
            stats_frame,
            text=f"Training: {training}",
            text_color="cyan" if training > 0 else "gray",
        ).pack(side="left", expand=True, padx=5)
        ctk.CTkLabel(
            stats_frame,
            text=f"Psi Training: {psi_training}",
            text_color="purple" if psi_training > 0 else "gray",
        ).pack(side="left", expand=True, padx=5)

        # TODO: Link to filtered soldier list view
        # For now, simplistic message
        ctk.CTkLabel(
            frame,
            text="(Feature to filter soldier list by base coming soon)",
            text_color="gray",
        ).pack(pady=20)

    def render_storage(self, base):
        frame = self.tab_storage
        self.clear_frame(frame)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(fill="both", expand=True)

        if not base.items:
            ctk.CTkLabel(scroll, text="No items in storage.").pack(pady=10)
            return

        # Sort items by name (translated)
        items_list = []
        for item_key, qty in base.items.items():
            name = self.controller.translation_manager.get(item_key)
            items_list.append((name, qty))

        items_list.sort(key=lambda x: x[0])

        for name, qty in items_list:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=name).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(qty)).pack(side="right", padx=10)

    def render_research(self, base):
        frame = self.tab_research
        self.clear_frame(frame)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(fill="both", expand=True)

        if not base.research:
            ctk.CTkLabel(scroll, text="No active research.").pack(pady=10)
            return

        # Headers
        h = ctk.CTkFrame(scroll)
        h.pack(fill="x")
        ctk.CTkLabel(h, text="Project", width=300, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(h, text="Assigned", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(h, text="Progress", width=150).pack(side="left", padx=5)

        for r in base.research:
            name = self.controller.translation_manager.get(r.project)
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=name, width=300, anchor="w").pack(
                side="left", padx=5
            )
            ctk.CTkLabel(row, text=str(r.assigned), width=80).pack(side="left", padx=5)

            # Progress bar logic if cost > 0
            if r.cost > 0:
                pct = min(1.0, r.spent / r.cost)
                prog_text = f"{r.spent}/{r.cost} ({int(pct * 100)}%)"
            else:
                prog_text = f"{r.spent}/?"
            ctk.CTkLabel(row, text=prog_text, width=150).pack(side="left", padx=5)

    def render_manufacturing(self, base):
        frame = self.tab_manufacturing
        self.clear_frame(frame)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(fill="both", expand=True)

        if not base.manufacturing:
            ctk.CTkLabel(scroll, text="No active production.").pack(pady=10)
            return

        h = ctk.CTkFrame(scroll)
        h.pack(fill="x")
        ctk.CTkLabel(h, text="Item", width=300, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(h, text="Assigned", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(h, text="Spent", width=100).pack(side="left", padx=5)
        ctk.CTkLabel(h, text="Ordered", width=80).pack(side="left", padx=5)

        for m in base.manufacturing:
            name = self.controller.translation_manager.get(m.item)
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=name, width=300, anchor="w").pack(
                side="left", padx=5
            )
            ctk.CTkLabel(row, text=str(m.assigned), width=80).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(m.spent), width=100).pack(side="left", padx=5)
            ctk.CTkLabel(
                row,
                text=str(m.amount) if not getattr(m, "infinite", False) else "∞",
                width=80,
            ).pack(side="left", padx=5)

    def render_transfers(self, base):
        frame = self.tab_transfers
        self.clear_frame(frame)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(fill="both", expand=True)

        if not base.transfers:
            ctk.CTkLabel(scroll, text="No incoming transfers.").pack(pady=10)
            return

        h = ctk.CTkFrame(scroll)
        h.pack(fill="x")
        ctk.CTkLabel(h, text="Item / Soldier", width=300, anchor="w").pack(
            side="left", padx=5
        )
        ctk.CTkLabel(h, text="Qty", width=50).pack(side="left", padx=5)
        ctk.CTkLabel(h, text="Arrival (Hours)", width=100).pack(side="left", padx=5)

        for t in base.transfers:
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=2)

            if t.soldier:
                name = t.soldier.name
                qty = 1
                # Maybe show rank?
                rank = self.controller.translation_manager.get(
                    self.controller.translation_manager.get_rank_string(
                        t.soldier.rank, t.soldier.type
                    )
                )
                display_text = f"{rank} {name}"
            elif t.item_id:
                display_text = self.controller.translation_manager.get(t.item_id)
                qty = t.item_qty
            else:
                display_text = "Unknown Shipment"
                qty = "?"

            ctk.CTkLabel(row, text=display_text, width=300, anchor="w").pack(
                side="left", padx=5
            )
            ctk.CTkLabel(row, text=str(qty), width=50).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(t.hours), width=100).pack(side="left", padx=5)

    def back_to_menu(self):
        from views.main_menu import MainMenu

        self.controller.show_frame(MainMenu)
