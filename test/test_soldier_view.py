import os
import sys
import unittest
from unittest.mock import MagicMock

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

    def winfo_children(self):
        return []


class _DummyLabel:
    def __init__(self, master=None, **kwargs):
        self.kwargs = dict(kwargs)

    def grid(self, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def cget(self, key):
        return self.kwargs.get(key, "")


class _DummyButton:
    def __init__(self, master=None, **kwargs):
        pass

    def grid(self, **kwargs):
        pass


class TestSoldierView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_modules = {
            "customtkinter": sys.modules.get("customtkinter"),
        }

        mock_ctk = MagicMock()
        mock_ctk.CTkFrame = _DummyFrame
        mock_ctk.CTkScrollableFrame = _DummyFrame
        mock_ctk.CTkLabel = _DummyLabel
        mock_ctk.CTkButton = _DummyButton
        mock_ctk.CTkFont = MagicMock()
        sys.modules["customtkinter"] = mock_ctk

        sys.modules.pop("views.soldier_view", None)
        import views.soldier_view

        cls.SoldierView = views.soldier_view.SoldierView

    @classmethod
    def tearDownClass(cls):
        for mod_name, original_mod in cls._original_modules.items():
            if original_mod is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original_mod
        sys.modules.pop("views.soldier_view", None)

    def test_update_view_sets_large_soldier_sprite(self):
        controller = MagicMock()
        soldier = MagicMock()
        soldier.id = 7
        soldier.name = "Mounir Khlifi"
        soldier.rank = 1
        soldier.type = "STR_SOLDIER"
        soldier.death_info = None
        soldier.equipmentLayout = None
        soldier.service_record = MagicMock(
            commendations=[],
            missions=[],
            kill_list=[],
            months_service=3,
            days_wounded_total=0,
            times_wounded_total=0,
            unconscious_total=0,
            shots_fired_counter_total=0,
            shots_landed_counter_total=0,
            shot_at_counter_total=0,
            hit_counter_total=0,
        )
        soldier.currentstats = MagicMock(
            tu=50,
            stamina=50,
            health=30,
            bravery=20,
            reactions=40,
            firing=55,
            throwing=35,
            strength=40,
            psistrength=30,
            psiskill=0,
        )
        controller.get_soldier_by_id.return_value = soldier
        controller.translation_manager.get_rank_string.return_value = "STR_AGENT"
        controller.translation_manager.get.side_effect = lambda k: f"TR[{k}]"
        large_sprite = MagicMock()
        controller.resource_manager.get_soldier_sprite.return_value = large_sprite

        view = self.SoldierView(MagicMock(), controller)
        view.update_view(7)

        controller.resource_manager.get_soldier_sprite.assert_called_once_with(
            soldier, ctk_image=True, size=(160, 200)
        )
        assert view.soldier_sprite_label.cget("image") is large_sprite


if __name__ == "__main__":
    unittest.main()
