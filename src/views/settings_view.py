import os
import shutil
import subprocess
import sys
from tkinter import filedialog, messagebox

import customtkinter as ctk


class SettingsView(ctk.CTkToplevel):
    def __init__(self, parent, app_controller):
        super().__init__(parent)
        self.controller = app_controller
        self.title("Settings")
        self.geometry("500x250")

        # Make the window modal
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)

        # Game Directory Label
        self.dir_label = ctk.CTkLabel(self, text="OpenXcom Directory:")
        self.dir_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Game Directory Entry
        self.dir_entry = ctk.CTkEntry(self, width=300)
        self.dir_entry.grid(row=0, column=1, padx=(0, 10), pady=(20, 10), sticky="ew")

        # Pre-fill current config
        current_dir = self.controller.config.game_dir
        if current_dir:
            self.dir_entry.insert(0, current_dir)

        # Browse Button
        self.browse_button = ctk.CTkButton(
            self, text="Browse", width=80, command=self.browse_dir
        )
        self.browse_button.grid(row=0, column=2, padx=(0, 20), pady=(20, 10))

        # Save Button
        self.save_button = ctk.CTkButton(self, text="Save", command=self.save_settings)
        self.save_button.grid(row=1, column=1, padx=20, pady=20, sticky="e")

        self.cancel_button = ctk.CTkButton(self, text="Cancel", command=self.destroy)
        self.cancel_button.grid(row=1, column=2, padx=(0, 20), pady=20)

        # Open Cache Directory Button
        self.cache_button = ctk.CTkButton(
            self,
            text="Open Cache Directory",
            command=self.open_cache_dir,
        )
        self.cache_button.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=20,
            pady=(0, 15),
            sticky="e",
        )

        # Clear Cache Button
        self.clear_cache_button = ctk.CTkButton(
            self,
            text="Clear Cache",
            command=self.clear_cache,
        )
        self.clear_cache_button.grid(
            row=2,
            column=2,
            padx=(0, 20),
            pady=(0, 15),
        )

    def browse_dir(self):
        directory = filedialog.askdirectory(title="Select OpenXcom Directory")
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

    def save_settings(self):
        new_dir = self.dir_entry.get().strip()
        self.controller.config.game_dir = new_dir
        self.controller.config.save()

        # Force a re-initialization of translation manager if needed,
        # but for now, just let the user know they might need to reload.
        messagebox.showinfo(
            "Settings Saved",
            "Settings have been saved. You may need to restart "
            "or reload to apply changes.",
        )

        self.destroy()

    def open_cache_dir(self):
        cache_dir = self.controller.data_manager._cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(cache_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", cache_dir])
        else:
            subprocess.Popen(["xdg-open", cache_dir])

    def clear_cache(self):
        cache_dir = self.controller.data_manager._cache_dir
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir)
        messagebox.showinfo(
            "Cache Cleared",
            "Ruleset cache has been cleared.",
        )
