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

    def item(self, item, option=None, **kwargs):
        if option == "values":
            return ["STR_RANK", "Soldier A", 1, 0, "Active"]
        if option == "tags":
            return ["even"]
        return None

    def move(self, item, parent, index):
        pass

    def selection(self):
        return [1]


class DummyScrollbar:
    def __init__(self, master=None, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def set(self, *args):
        pass


# Global BaseView that will be populated in setUpClass
BaseView = None


class TestBaseView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Setup mocks for the entire class."""
        cls._original_modules = {
            "customtkinter": sys.modules.get("customtkinter"),
            "tkinter": sys.modules.get("tkinter"),
            "tkinter.ttk": sys.modules.get("tkinter.ttk"),
            "PIL": sys.modules.get("PIL"),
            "PIL.Image": sys.modules.get("PIL.Image"),
        }

        mock_ctk = MagicMock()
        mock_ctk.CTkFrame = DummyCTkFrame
        mock_ctk.CTkLabel = DummyCTkLabel
        mock_ctk.CTkButton = DummyCTkButton
        mock_ctk.CTkOptionMenu = DummyCTkOptionMenu
        mock_ctk.CTkTabview = DummyCTkTabview
        mock_ctk.CTkScrollableFrame = DummyCTkScrollableFrame
        mock_ctk.CTkFont = MagicMock()
        sys.modules["customtkinter"] = mock_ctk

        mock_ttk = MagicMock()
        mock_ttk.Treeview = DummyTreeview
        mock_ttk.Scrollbar = DummyScrollbar
        sys.modules["tkinter"] = MagicMock()
        sys.modules["tkinter"].ttk = mock_ttk
        sys.modules["tkinter.ttk"] = mock_ttk

        sys.modules["PIL"] = MagicMock()
        sys.modules["PIL.Image"] = MagicMock()

        # Ensure views.base_view is reloaded with these mocks
        if "views.base_view" in sys.modules:
            del sys.modules["views.base_view"]

        import views.base_view

        global BaseView
        BaseView = views.base_view.BaseView

    @classmethod
    def tearDownClass(cls):
        """Restore sys.modules to prevent test pollution."""
        for mod_name, original_mod in cls._original_modules.items():
            if original_mod is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original_mod

        # Remove the imported module so it can be cleanly re-imported by other tests
        sys.modules.pop("views.base_view", None)

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

            s2 = MagicMock()
            s2.id = 2
            s2.recovery = 10
            s2.training = True
            s2.psi_training = True
            s2.rank = 1
            s2.type = "S"
            s2.name = "Soldier 2"
            s2.missions = 2
            s2.kills = 1

            base.soldiers = [s1, s2]

            # Setup the mocked tree instance to return children for deletion testing
            tree_instance = MockTree.return_value
            tree_instance.get_children.return_value = ["item1", "item2"]

            # Mock format_recovery_time
            with patch("view_utils.format_recovery_time", return_value="10 days"):
                self.view.render_soldiers(base)

            # Verify Treeview created
            MockTree.assert_called()

            # Verify delete called for existing children
            tree_instance.delete.assert_any_call("item1")
            tree_instance.delete.assert_any_call("item2")

            # Verify insert called
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

    def test_update_view_with_bases_already_selected(self):
        """Test behavior with bases when current base is already selected"""
        base1 = MagicMock()
        base1.name = "Base Alpha"
        base2 = MagicMock()
        base2.name = "Base Beta"
        self.mock_controller.bases = [base1, base2]

        self.view.current_base = base1

        self.view.base_selector.set = MagicMock()
        self.view.base_selector.configure = MagicMock()
        self.view.render_base_details = MagicMock()

        self.view.update_view()

        self.view.base_selector.configure.assert_called()
        self.view.render_base_details.assert_called_with(base1)

    def test_clear_frame(self):
        """Test clear_frame method"""
        frame = MagicMock()
        child1 = MagicMock()
        child2 = MagicMock()
        frame.winfo_children.return_value = [child1, child2]

        self.view.clear_frame(frame)

        child1.destroy.assert_called_once()
        child2.destroy.assert_called_once()

    def test_render_storage(self):
        """Test storage rendering logic"""
        base = MagicMock()
        base.items = {"STR_RIFLE": 10, "STR_PISTOL": 5}

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_storage(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("TR[STR_RIFLE]", texts)
            self.assertIn("10", texts)
            self.assertIn("TR[STR_PISTOL]", texts)
            self.assertIn("5", texts)

    def test_render_storage_empty(self):
        """Test storage rendering when empty"""
        base = MagicMock()
        base.items = {}

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_storage(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("No items in storage.", texts)

    def test_render_research(self):
        """Test research rendering logic"""
        base = MagicMock()
        r1 = MagicMock()
        r1.project = "STR_LASER_WEAPONS"
        r1.assigned = 10
        r1.cost = 500
        r1.spent = 250

        r2 = MagicMock()
        r2.project = "STR_PLASMA_WEAPONS"
        r2.assigned = 5
        r2.cost = 0
        r2.spent = 100

        base.research = [r1, r2]

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_research(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("TR[STR_LASER_WEAPONS]", texts)
            self.assertIn("10", texts)
            self.assertIn("250/500 (50%)", texts)
            self.assertIn("TR[STR_PLASMA_WEAPONS]", texts)
            self.assertIn("100/?", texts)

    def test_render_research_empty(self):
        """Test research rendering when empty"""
        base = MagicMock()
        base.research = []

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_research(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("No active research.", texts)

    def test_render_manufacturing(self):
        """Test manufacturing rendering logic"""
        base = MagicMock()
        m1 = MagicMock()
        m1.item = "STR_LASER_RIFLE"
        m1.assigned = 20
        m1.spent = 50
        m1.amount = 5
        m1.infinite = False

        m2 = MagicMock()
        m2.item = "STR_LASER_PISTOL"
        m2.assigned = 10
        m2.spent = 20
        m2.amount = 0
        m2.infinite = True

        base.manufacturing = [m1, m2]

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_manufacturing(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("TR[STR_LASER_RIFLE]", texts)
            self.assertIn("20", texts)
            self.assertIn("5", texts)
            self.assertIn("TR[STR_LASER_PISTOL]", texts)
            self.assertIn("∞", texts)

    def test_render_manufacturing_empty(self):
        """Test manufacturing rendering when empty"""
        base = MagicMock()
        base.manufacturing = []

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_manufacturing(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("No active production.", texts)

    def test_render_transfers_empty(self):
        """Test transfers rendering when empty"""
        base = MagicMock()
        base.transfers = []

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_transfers(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("No incoming transfers.", texts)

    def test_sort_data_list(self):
        """Test data list sorting logic"""
        data = [
            {"raw_sort": {"Rank": 1, "Name": "B"}},
            {"raw_sort": {"Rank": 2, "Name": "A"}},
            {"raw_sort": {"Rank": 0, "Name": "C"}},
        ]

        self.view.soldier_sort_col = "Rank"
        self.view.soldier_sort_reverse = False
        self.view.sort_data_list(data)
        self.assertEqual(data[0]["raw_sort"]["Rank"], 0)
        self.assertEqual(data[1]["raw_sort"]["Rank"], 1)
        self.assertEqual(data[2]["raw_sort"]["Rank"], 2)

        self.view.soldier_sort_col = "Name"
        self.view.soldier_sort_reverse = True
        self.view.sort_data_list(data)
        self.assertEqual(data[0]["raw_sort"]["Name"], "C")
        self.assertEqual(data[1]["raw_sort"]["Name"], "B")
        self.assertEqual(data[2]["raw_sort"]["Name"], "A")

    def test_sort_soldier_tree(self):
        """Test treeview sorting mechanism"""
        self.view.soldier_tree = MagicMock()
        self.view.soldier_tree.get_children.return_value = ["item1", "item2"]

        # We need realistic item values
        def mock_item(child, option=None, **kwargs):
            if option == "values":
                if child == "item1":
                    return ["Rank 2", "Alice", 5, 10, "Active"]
                else:
                    return ["Rank 1", "Bob", 10, 5, "Wounded"]
            if option == "tags":
                if child == "item1":
                    return ["even"]
                else:
                    return ["odd"]
            return None

        self.view.soldier_tree.item = MagicMock(side_effect=mock_item)

        # Toggle reverse flag if same column
        self.view.soldier_sort_col = "Rank"
        self.view.soldier_sort_reverse = False
        self.view.sort_soldier_tree("Rank")
        self.assertTrue(self.view.soldier_sort_reverse)

        # Change column
        self.view.sort_soldier_tree("Name")
        self.assertEqual(self.view.soldier_sort_col, "Name")
        self.assertFalse(self.view.soldier_sort_reverse)

    def test_on_soldier_select(self):
        """Test soldier selection handler"""
        self.view.soldier_tree = MagicMock()
        self.view.soldier_tree.selection.return_value = [1]

        self.view.on_soldier_select(None)

        self.mock_controller.show_soldier_view.assert_called_once_with(
            1, previous_view=BaseView
        )

    def test_back_to_menu(self):
        """Test back to menu button"""
        from views.main_menu import MainMenu

        self.view.back_to_menu()
        self.mock_controller.show_frame.assert_called_once_with(MainMenu)

    def test_render_transfers_unknown_shipment(self):
        """Test transfer rendering with unknown shipment"""
        base = MagicMock()
        t1 = MagicMock()
        t1.soldier = None
        t1.item_id = None
        t1.hours = 48

        base.transfers = [t1]

        with patch("customtkinter.CTkLabel") as MockLabel:
            self.view.render_transfers(base)

            texts = [c.kwargs.get("text") for c in MockLabel.call_args_list]
            self.assertIn("Unknown Shipment", texts)
            self.assertIn("?", texts)


if __name__ == "__main__":
    unittest.main()
