import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


class _DummyFrame:
    def __init__(self, master=None, **kwargs):
        self.master = master

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def grid_rowconfigure(self, index, weight=1):
        pass

    def grid_columnconfigure(self, index, weight=1):
        pass


class _DummyWidget:
    def __init__(self, master=None, **kwargs):
        self.kwargs = kwargs

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass


class _DummyBooleanVar:
    def __init__(self, value=False):
        self.value = value

    def get(self):
        return self.value


class _DummyTreeview:
    def __init__(self, master=None, **kwargs):
        self.kwargs = kwargs
        self.inserted = []

    def grid(self, **kwargs):
        pass

    def __setitem__(self, key, val):
        pass

    def heading(self, col, **kwargs):
        pass

    def column(self, col, **kwargs):
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
        self.inserted.append(kwargs)


class TestSoldierListView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_modules = {
            "customtkinter": sys.modules.get("customtkinter"),
            "tkinter": sys.modules.get("tkinter"),
            "tkinter.ttk": sys.modules.get("tkinter.ttk"),
        }

        mock_ctk = MagicMock()
        mock_ctk.CTkFrame = _DummyFrame
        mock_ctk.CTkButton = _DummyWidget
        mock_ctk.CTkLabel = _DummyWidget
        mock_ctk.CTkSwitch = _DummyWidget
        mock_ctk.BooleanVar = _DummyBooleanVar
        mock_ctk.CTkFont = MagicMock()
        sys.modules["customtkinter"] = mock_ctk

        mock_ttk = MagicMock()
        mock_ttk.Treeview = _DummyTreeview
        sys.modules["tkinter"] = MagicMock()
        sys.modules["tkinter"].ttk = mock_ttk
        sys.modules["tkinter.ttk"] = mock_ttk

        sys.modules.pop("views.soldier_list", None)
        import views.soldier_list

        cls.SoldierListView = views.soldier_list.SoldierListView

    @classmethod
    def tearDownClass(cls):
        for mod_name, original_mod in cls._original_modules.items():
            if original_mod is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original_mod
        sys.modules.pop("views.soldier_list", None)

    def test_update_view_attaches_soldier_sprites(self):
        controller = MagicMock()
        soldier = MagicMock(
            id=1,
            name="Jane Doe",
            rank=2,
            type="STR_SOLDIER",
            missions=4,
            kills=3,
            base="HQ",
        )
        controller.soldiers = [soldier]
        controller.translation_manager.get_rank_string.return_value = "STR_SERGEANT"
        controller.translation_manager.get.side_effect = lambda k: f"TR[{k}]"
        controller.resource_manager.get_soldier_sprite.return_value = MagicMock()

        view = self.SoldierListView(MagicMock(), controller)

        with patch("views.soldier_list.ImageTk") as mock_imagetk:
            mock_photo = MagicMock()
            mock_imagetk.PhotoImage.return_value = mock_photo
            view.update_view()

        controller.translation_manager.get_rank_string.assert_called_once_with(
            2, "STR_SOLDIER"
        )
        controller.resource_manager.get_soldier_sprite.assert_called_once_with(
            soldier, ctk_image=False, size=(32, 40)
        )
        assert len(view.tree.inserted) == 1
        row = view.tree.inserted[0]
        assert row["image"] is mock_photo
        assert row["values"][2] == "TR[STR_SERGEANT]"
        assert view._row_images == [mock_photo]


if __name__ == "__main__":
    unittest.main()
