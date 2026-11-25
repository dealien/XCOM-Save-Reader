import logging
from tkinter import ttk
from typing import Any

import customtkinter as ctk

import view_utils

try:
    from PIL import ImageTk
except Exception:  # pragma: no cover - fallback when PIL is mocked in tests
    ImageTk = None

logger = logging.getLogger(__name__)


class BaseView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        logger.debug("Entering BaseView.__init__")
        super().__init__(parent)
        logger.debug("Called super().__init__")
        self.controller = controller

        # Sort state for soldier list and storage grid
        self.soldier_sort_col = "Rank"
        self.soldier_sort_reverse = False
        self.storage_sort_mode = "Name"
        self._soldier_row_images: list[Any] = []

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
        # current_selection = self.base_selector.get()
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

        rm = getattr(self.controller, "resource_manager", None)
        layout_img = rm.render_base_layout(base, scale=2) if rm is not None else None

        content = ctk.CTkFrame(scroll, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=5)

        if layout_img is not None:
            layout_frame = ctk.CTkFrame(content, fg_color="transparent")
            layout_frame.pack(side="left", anchor="nw", padx=(0, 20), pady=5)
            ctk.CTkLabel(
                layout_frame,
                text="Base Layout",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(anchor="w", pady=(0, 5))
            ctk.CTkLabel(layout_frame, text="", image=layout_img).pack(anchor="w")

        details_frame = ctk.CTkFrame(content, fg_color="transparent")
        details_frame.pack(side="left", fill="both", expand=True, anchor="nw")

        ctk.CTkLabel(
            details_frame, text="Facilities", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=5)

        # Group facilities by type and render with sprite if available
        counts: dict[str, int] = {}
        type_to_raw: dict[str, str] = {}
        for f in base.facilities:
            if f.type:
                ftype = self.controller.translation_manager.get(f.type)
                counts[ftype] = counts.get(ftype, 0) + 1
                type_to_raw[ftype] = f.type

        for ftype, count in counts.items():
            row = ctk.CTkFrame(details_frame, fg_color="transparent")
            row.pack(anchor="w", padx=10, pady=2)

            raw_type = type_to_raw.get(ftype, "")
            sprite = rm.get_facility_sprite(raw_type) if rm is not None else None

            if sprite is not None:
                ctk.CTkLabel(row, text="", image=sprite).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(row, text=f"{ftype}: {count}").pack(side="left")

        crafts = getattr(base, "crafts", None)
        if isinstance(crafts, (list, tuple)) and crafts:
            ctk.CTkLabel(
                details_frame, text="Crafts", font=ctk.CTkFont(size=16, weight="bold")
            ).pack(anchor="w", pady=(15, 5))
            for c in crafts:
                row = ctk.CTkFrame(details_frame, fg_color="transparent")
                row.pack(anchor="w", padx=10, pady=2)

                craft_sprite = (
                    rm.get_craft_sprite(c.type) if rm is not None and c.type else None
                )
                if craft_sprite is not None:
                    ctk.CTkLabel(row, text="", image=craft_sprite).pack(
                        side="left", padx=(0, 8)
                    )

                craft_type_name = (
                    self.controller.translation_manager.get(c.type)
                    if c.type
                    else "Unknown Craft"
                )
                craft_label = getattr(c, "name", None) or (
                    f"{craft_type_name} #{c.id}"
                    if getattr(c, "id", None)
                    else craft_type_name
                )
                status = (
                    self.controller.translation_manager.get(c.status)
                    if getattr(c, "status", None)
                    else ""
                )
                text = f"{craft_label} ({status})" if status else craft_label
                ctk.CTkLabel(row, text=text).pack(side="left")

    def render_soldiers(self, base):
        frame = self.tab_soldiers
        self.clear_frame(frame)

        total = len(base.soldiers)
        wounded = sum(1 for s in base.soldiers if s.recovery > 0)
        training = sum(1 for s in base.soldiers if s.training)
        psi_training = sum(1 for s in base.soldiers if s.psi_training)
        active = total - wounded  # Approximate

        # Summary Frame
        stats_frame = ctk.CTkFrame(frame)
        stats_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            stats_frame, text=f"Total: {total}", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=10)
        ctk.CTkLabel(stats_frame, text=f"Active: {active}").pack(side="left", padx=10)
        ctk.CTkLabel(
            stats_frame,
            text=f"Wounded: {wounded}",
            text_color="orange" if wounded > 0 else "gray",
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            stats_frame,
            text=f"Training: {training}",
            text_color="cyan" if training > 0 else "gray",
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            stats_frame,
            text=f"Psi: {psi_training}",
            text_color="purple" if psi_training > 0 else "gray",
        ).pack(side="left", padx=10)

        # Treeview
        self.soldier_tree = self.create_soldier_tree(frame)
        self.soldier_tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.populate_soldier_tree(base.soldiers)

    def create_soldier_tree(self, parent):
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            rowheight=44,
            fieldbackground="#2b2b2b",
            bordercolor="#2b2b2b",
            borderwidth=0,
            font=("Roboto", 11),
        )
        style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "white")],
        )
        style.configure(
            "Treeview.Heading",
            background="#3a3d42",
            foreground="white",
            relief="flat",
            font=("Roboto", 11, "bold"),
            padding=(10, 5),
        )

        columns = ["Rank", "Name", "Missions", "Kills", "Status"]
        tree = ttk.Treeview(parent, columns=columns, show="tree headings")
        tree.heading("#0", text="")
        tree.column("#0", width=50, minwidth=44, stretch=False, anchor="center")

        # Configure headers
        for col in columns:
            tree.heading(col, text=col, command=lambda c=col: self.sort_soldier_tree(c))

            if col == "Name":
                tree.column(col, width=200, anchor="w")
            elif col == "Status":
                tree.column(col, width=200, anchor="w")
            else:
                tree.column(col, width=80, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 20), pady=(0, 20))

        tree.bind("<<TreeviewSelect>>", self.on_soldier_select)

        # Tags for styling
        tree.tag_configure("odd", background="#2b2b2b")
        tree.tag_configure("even", background="#323538")
        tree.tag_configure("wounded", foreground="orange")

        return tree

    def populate_soldier_tree(self, soldiers):
        # Clear existing data and retained PhotoImage references
        self._soldier_row_images.clear()
        for i in self.soldier_tree.get_children():
            self.soldier_tree.delete(i)

        data = []
        for s in soldiers:
            # Rank translation
            rank_key = self.controller.translation_manager.get_rank_string(
                s.rank, s.type
            )
            rank_str = self.controller.translation_manager.get(rank_key)

            # Status
            status_parts = []
            is_wounded = False
            if s.recovery > 0:
                rec_str = view_utils.format_recovery_time(s.recovery)
                status_parts.append(f"Wounded ({rec_str})")
                is_wounded = True
            if s.training:
                status_parts.append("Training")
            if s.psi_training:
                status_parts.append("Psi Training")

            status_str = ", ".join(status_parts) if status_parts else "Active"

            data.append(
                {
                    "id": s.id,
                    "soldier": s,
                    "values": [rank_str, s.name, s.missions, s.kills, status_str],
                    "wounded": is_wounded,
                    "raw_sort": {  # For smarter sorting
                        "Rank": s.rank,
                        "Name": s.name,
                        "Missions": s.missions,
                        "Kills": s.kills,
                        "Status": s.recovery,  # Sort status by recovery days roughly
                    },
                }
            )

        # Sort
        self.sort_data_list(data)

        rm = getattr(self.controller, "resource_manager", None)

        # Insert
        for i, item in enumerate(data):
            tags = ["even" if i % 2 == 0 else "odd"]
            if item["wounded"]:
                tags.append("wounded")

            insert_kwargs: dict[str, Any] = {
                "iid": item["id"],
                "values": item["values"],
                "tags": tuple(tags),
            }
            if rm is not None and ImageTk is not None:
                pil_img = rm.get_soldier_sprite(
                    item["soldier"], ctk_image=False, size=(32, 40)
                )
                if pil_img is not None:
                    try:
                        photo = ImageTk.PhotoImage(pil_img)
                        self._soldier_row_images.append(photo)
                        insert_kwargs["image"] = photo
                    except Exception:
                        pass

            self.soldier_tree.insert("", "end", **insert_kwargs)

    def sort_soldier_tree(self, col):
        if self.soldier_sort_col == col:
            self.soldier_sort_reverse = not self.soldier_sort_reverse
        else:
            self.soldier_sort_reverse = False
            self.soldier_sort_col = col

        # Repopulate (using current base soldiers, but we need access to them.
        # Easier to re-read from tree or just re-render.
        # But render_soldiers creates new tree.
        # Let's re-sort the existing items in the tree.

        items = []
        for child in self.soldier_tree.get_children(""):
            values = self.soldier_tree.item(child, "values")
            # We loose raw data if we just pull values.
            # But we can assume typical string/int sorting for now.
            items.append((values, child))

        # Helper to get sort key
        def get_key(item):
            # Map column name to index
            col_idx = ["Rank", "Name", "Missions", "Kills", "Status"].index(col)
            val = item[0][col_idx]
            # Try float
            try:
                return float(val)
            except ValueError:
                return val

        items.sort(key=get_key, reverse=self.soldier_sort_reverse)

        for index, (_, child) in enumerate(items):
            self.soldier_tree.move(child, "", index)
            # Re-stripe
            current_tags = list(self.soldier_tree.item(child, "tags"))
            # Remove old striping
            if "even" in current_tags:
                current_tags.remove("even")
            if "odd" in current_tags:
                current_tags.remove("odd")

            new_stripe = "even" if index % 2 == 0 else "odd"
            current_tags.append(new_stripe)
            self.soldier_tree.item(child, tags=tuple(current_tags))

    def sort_data_list(self, data):
        # Sort the raw data dictionary list based on self.soldier_sort_col
        key_name = self.soldier_sort_col

        def get_sort_val(item):
            return item["raw_sort"].get(key_name, "")

        data.sort(key=get_sort_val, reverse=self.soldier_sort_reverse)

    def on_soldier_select(self, event):
        selected = self.soldier_tree.selection()
        if selected:
            soldier_id = selected[0]
            self.controller.show_soldier_view(soldier_id, previous_view=BaseView)

    def render_storage(self, base):
        frame = self.tab_storage
        self.clear_frame(frame)

        if not base.items:
            ctk.CTkLabel(frame, text="No items in storage.").pack(pady=10)
            return

        items_list = []
        for item_key, qty in base.items.items():
            name = self.controller.translation_manager.get(item_key)
            items_list.append((item_key, name, qty))
        self._storage_items = items_list

        container = ctk.CTkFrame(frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=1)

        # Left pane: single contiguous in-game sprite grid with sort selector
        left_pane = ctk.CTkFrame(container)
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_pane.grid_rowconfigure(1, weight=1)
        left_pane.grid_columnconfigure(0, weight=1)

        grid_header = ctk.CTkFrame(left_pane, fg_color="transparent")
        grid_header.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        grid_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            grid_header,
            text="Storage Grid",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(grid_header, text="Sort:").grid(row=0, column=1, padx=(0, 6))
        self.storage_sort_menu = ctk.CTkOptionMenu(
            grid_header,
            values=["Name", "ID", "Type", "Quantity", "List Order"],
            command=self._on_storage_sort_change,
        )
        self.storage_sort_menu.set(self.storage_sort_mode)
        self.storage_sort_menu.grid(row=0, column=2, sticky="e")

        self.storage_grid_scroll = ctk.CTkScrollableFrame(left_pane)
        self.storage_grid_scroll.grid(
            row=1, column=0, sticky="nsew", padx=6, pady=(0, 6)
        )

        # Right pane: searchable text list
        right_pane = ctk.CTkFrame(container)
        right_pane.grid(row=0, column=1, sticky="nsew")
        right_pane.grid_rowconfigure(1, weight=1)
        right_pane.grid_columnconfigure(0, weight=1)

        self.storage_search_entry = ctk.CTkEntry(
            right_pane, placeholder_text="Search items..."
        )
        self.storage_search_entry.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.storage_search_entry.bind(
            "<KeyRelease>", lambda _event: self._filter_storage_items()
        )

        self.storage_list_scroll = ctk.CTkScrollableFrame(right_pane)
        self.storage_list_scroll.grid(
            row=1, column=0, sticky="nsew", padx=6, pady=(0, 6)
        )

        self._populate_storage_views(self._storage_items)

    @staticmethod
    def _item_type_sort_key(item_def):
        categories = item_def.get("categories")
        cat = (
            str(categories[0]).lower()
            if isinstance(categories, list) and categories
            else ""
        )
        battle_type = item_def.get("battleType")
        try:
            bt = int(battle_type) if battle_type is not None else 999
        except ValueError, TypeError:
            bt = 999
        return (cat, bt)

    def _sort_storage_items(self, items):
        dm = getattr(self.controller, "data_manager", None)
        items_db = getattr(dm, "items", None)
        if not isinstance(items_db, dict):
            items_db = {}

        mode = getattr(self, "storage_sort_mode", "Name")
        if mode == "ID":
            return sorted(items, key=lambda x: x[0].lower())
        if mode == "Quantity":
            return sorted(items, key=lambda x: (-x[2], x[1].lower()))
        if mode == "Type":
            return sorted(
                items,
                key=lambda x: (
                    self._item_type_sort_key(items_db.get(x[0], {})),
                    x[1].lower(),
                ),
            )
        if mode == "List Order":

            def _list_order(entry):
                raw = items_db.get(entry[0], {}).get("listOrder")
                try:
                    order = int(raw) if raw is not None else 999999
                except ValueError, TypeError:
                    order = 999999
                return (order, entry[1].lower())

            return sorted(items, key=_list_order)
        return sorted(items, key=lambda x: (x[1].lower(), x[0]))

    def _on_storage_sort_change(self, mode):
        self.storage_sort_mode = mode
        self._filter_storage_items()

    def _filter_storage_items(self):
        query = ""
        if getattr(self, "storage_search_entry", None) is not None:
            query = self.storage_search_entry.get().strip().lower()
        items = getattr(self, "_storage_items", [])
        if query:
            filtered = [
                (key, name, qty)
                for key, name, qty in items
                if query in name.lower() or query in key.lower()
            ]
        else:
            filtered = items
        self._populate_storage_views(filtered)

    def _populate_storage_views(self, items):
        self.clear_frame(self.storage_grid_scroll)
        self.clear_frame(self.storage_list_scroll)

        if not items:
            ctk.CTkLabel(self.storage_grid_scroll, text="No matching items.").pack(
                pady=10
            )
            ctk.CTkLabel(self.storage_list_scroll, text="No matching items.").pack(
                pady=10
            )
            return

        items = self._sort_storage_items(items)
        rm = getattr(self.controller, "resource_manager", None)

        grid_items = [(item_key, qty) for item_key, _name, qty in items]
        grid_img = (
            rm.render_storage_grid(grid_items, grid_cols=16, scale=2)
            if rm is not None
            else None
        )
        if grid_img is not None:
            ctk.CTkLabel(self.storage_grid_scroll, text="", image=grid_img).pack(
                anchor="n", padx=4, pady=4
            )

        for item_key, name, qty in items:
            row = ctk.CTkFrame(self.storage_list_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            sprite = (
                rm.get_item_sprite(item_key, size=(24, 36)) if rm is not None else None
            )
            if sprite is not None:
                ctk.CTkLabel(row, text="", image=sprite).pack(side="left", padx=(6, 4))
            ctk.CTkLabel(row, text=name).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=str(qty)).pack(side="right", padx=8)

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
