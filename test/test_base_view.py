import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


# Create a dummy module for customtkinter to avoid inheriting from MagicMock
class DummyCTkFrame:
    def __init__(self, master=None, **kwargs):
        self.master = master
        self.winfo_children = MagicMock(return_value=[])

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def grid_rowconfigure(self, index, weight=1):
        pass

    def grid_columnconfigure(self, index, weight=1):
        pass

    def destroy(self):
        pass


class DummyCTkLabel:
    def __init__(self, master=None, **kwargs):
        self.kwargs = kwargs

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass


class DummyCTkButton:
    def __init__(self, master=None, **kwargs):
        pass

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass


class DummyCTkOptionMenu:
    def __init__(self, master=None, **kwargs):
        self.values = kwargs.get("values", [])
        self.command = kwargs.get("command")

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def set(self, value):
        pass

    def get(self):
        return "Base Alpha"

    def configure(self, **kwargs):
        pass


class DummyCTkTabview:
    def __init__(self, master=None, **kwargs):
        self.tabs = {}

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def add(self, name):
        self.tabs[name] = MagicMock()
        # Mock winfo_children for the tab frame
        self.tabs[name].winfo_children = MagicMock(return_value=[])
        return self.tabs[name]


class DummyCTkScrollableFrame:
    def __init__(self, master=None, **kwargs):
        pass

    def pack(self, **kwargs):
        pass


class DummyTreeview:
    def __init__(self, master=None, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def grid(self, **kwargs):
        pass

    def heading(self, col, **kwargs):
        pass

    def column(self, col, **kwargs):
        pass

    def configure(self, **kwargs):
        pass

    def bind(self, event, command):
        pass

    def tag_configure(self, tag, **kwargs):
        pass

    def get_children(self):
        return []

    def delete(self, item):
        pass

    def insert(self, parent, index, **kwargs):
        pass

    def yview(self, *args):
        pass


class DummyScrollbar:
    def __init__(self, master=None, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def set(self, *args):
        pass


mock_ctk = MagicMock()
mock_ctk.CTkFrame = DummyCTkFrame
mock_ctk.CTkLabel = DummyCTkLabel
mock_ctk.CTkButton = DummyCTkButton
mock_ctk.CTkOptionMenu = DummyCTkOptionMenu
mock_ctk.CTkTabview = DummyCTkTabview
mock_ctk.CTkScrollableFrame = DummyCTkScrollableFrame
mock_ctk.CTkFont = MagicMock()

_original_modules = {
    "customtkinter": sys.modules.get("customtkinter"),
    "tkinter": sys.modules.get("tkinter"),
    "tkinter.ttk": sys.modules.get("tkinter.ttk"),
}

sys.modules["customtkinter"] = mock_ctk

# Mock ttk
mock_ttk = MagicMock()
mock_ttk.Treeview = DummyTreeview
mock_ttk.Scrollbar = DummyScrollbar
sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter"].ttk = mock_ttk
sys.modules["tkinter.ttk"] = mock_ttk

# Now import the class under test
from views.base_view import BaseView  # noqa: E402


def tearDownModule():
    """Restore sys.modules to prevent test pollution."""
    for mod_name, original_mod in _original_modules.items():
        if original_mod is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = original_mod

    # Remove the imported module so it can be cleanly re-imported by other tests
    sys.modules.pop("views.base_view", None)


class TestBaseView(unittest.TestCase):
    def setUp(self):
        self.mock_parent = MagicMock()
        self.mock_controller = MagicMock()
        self.mock_controller.bases = []
        self.mock_controller.translation_manager = MagicMock()
        self.mock_controller.translation_manager.get.side_effect = lambda x: f"TR[{x}]"
        self.mock_controller.translation_manager.get_rank_string.return_value = (
            "STR_RANK"
        )

        self.view = BaseView(self.mock_parent, self.mock_controller)

    def test_init(self):
        """Verify components are initialized"""
        # Verify tabs created
        self.assertIn("Overview", self.view.tab_view.tabs)
        self.assertIn("Soldiers", self.view.tab_view.tabs)
        self.assertIn("Transfers", self.view.tab_view.tabs)

    def test_update_view_no_bases(self):
        """Test behavior when no bases exist"""
        self.mock_controller.bases = []

        # We need to spy on base_selector methods.
        # Since DummyCTkOptionMenu is a real class here,
        # we can mock its methods on the instance
        self.view.base_selector.set = MagicMock()
        self.view.base_selector.configure = MagicMock()

        self.view.update_view()
        self.view.base_selector.set.assert_called_with("No Bases Found")
        self.view.base_selector.configure.assert_called_with(state="disabled")

    def test_update_view_with_bases(self):
        """Test behavior with bases"""
        base1 = MagicMock()
        base1.name = "Base Alpha"
        base2 = MagicMock()
        base2.name = "Base Beta"
        self.mock_controller.bases = [base1, base2]

        self.view.base_selector.set = MagicMock()
        self.view.base_selector.configure = MagicMock()
        self.view.base_selector.get = MagicMock(return_value="Base Alpha")

        # Test default selection
        self.view.update_view()

        self.view.base_selector.configure.assert_called()
        self.view.base_selector.set.assert_called_with("Base Alpha")
        self.assertEqual(self.view.current_base, base1)

    def test_render_overview(self):
        """Test facility counting Logic"""
        base = MagicMock()
        f1 = MagicMock()
        f1.type = "STR_HANGAR"
        f2 = MagicMock()
        f2.type = "STR_HANGAR"
        f3 = MagicMock()
        f3.type = "STR_LIVING"
        base.facilities = [f1, f2, f3]

        # Capture Labels
        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_overview(base)

            # Verify calls
            self.mock_controller.translation_manager.get.assert_any_call("STR_HANGAR")

            # Check arguments to Label init
            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("TR[STR_HANGAR]: 2", texts)
            self.assertIn("TR[STR_LIVING]: 1", texts)

    def test_render_soldiers(self):
        """Test soldier statistics logic"""
        base = MagicMock()
        base.soldiers = []

        # We need to mock the creation of the treeview and its methods for verification
        with patch("tkinter.ttk.Treeview") as MockTree:
            # Setup specific soldier data to test population
            s1 = MagicMock()
            s1.id = 1
            s1.recovery = 0
            s1.training = False
            s1.psi_training = False
            s1.rank = 0
            s1.type = "S"
            s1.name = "Soldier 1"
            s1.missions = 10
            s1.kills = 5
            base.soldiers = [s1]

            self.view.render_soldiers(base)

            # Verify Treeview created
            MockTree.assert_called()

            # Verify insert called
            # Get the instance returned by MockTree()
            tree_instance = MockTree.return_value
            tree_instance.insert.assert_called()

    def test_render_transfers(self):
        """Test transfer rendering"""
        base = MagicMock()
        t1 = MagicMock()
        t1.soldier = MagicMock()
        t1.soldier.name = "Jane Doe"
        t1.soldier.rank = 0
        t1.soldier.type = "STR_SOLDIER"
        t1.item_id = None
        t1.hours = 24

        t2 = MagicMock()
        t2.soldier = None
        t2.item_id = "STR_RIFLE"
        t2.item_qty = 5
        t2.hours = 12

        base.transfers = [t1, t2]

        # Mock translation for rank (Set BEFORE render_transfers)
        self.mock_controller.translation_manager.get_rank_string.return_value = (
            "STR_ROOKIE_KEY"
        )

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_transfers(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]

            self.assertIn("TR[STR_ROOKIE_KEY] Jane Doe", texts)
            self.assertIn("TR[STR_RIFLE]", texts)


if __name__ == "__main__":
    unittest.main()
