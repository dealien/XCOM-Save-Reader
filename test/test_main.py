import sys
import os
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

class DummyCTk:
    def __init__(self, *args, **kwargs):
        pass
    def title(self, *args, **kwargs):
        pass
    def geometry(self, *args, **kwargs):
        pass
    def mainloop(self, *args, **kwargs):
        pass

import customtkinter as ctk
ctk.CTk = DummyCTk

from main import App
from views.soldier_view import SoldierView
from views.mission_view import MissionView

class TestMain(unittest.TestCase):
    def setUp(self):
        class DummyAppForTest:
            show_soldier_view = App.show_soldier_view
            show_mission_view = App.show_mission_view
            get_soldier_by_id = App.get_soldier_by_id
            get_mission_by_id = App.get_mission_by_id
            get_mission_participants = App.get_mission_participants
            show_frame = App.show_frame

        self.app = DummyAppForTest()
        self.app.soldiers = []
        self.app.missions = {}
        self.app.mission_participants = {}
        self.app.frames = {}

        self.app.show_frame = MagicMock()

    def test_show_soldier_view(self):
        self.app.show_soldier_view(123)
        self.app.show_frame.assert_called_once_with(SoldierView, 123)

    def test_show_mission_view(self):
        self.app.show_mission_view(456, 123)
        self.app.show_frame.assert_called_once_with(MissionView, 456, 123)

    def test_get_soldier_by_id_found(self):
        class DummySoldier:
            def __init__(self, sid):
                self.id = sid
        self.app.soldiers = [DummySoldier(1), DummySoldier(2)]

        soldier = self.app.get_soldier_by_id(2)
        self.assertIsNotNone(soldier)
        self.assertEqual(soldier.id, 2)

    def test_get_soldier_by_id_not_found(self):
        self.assertIsNone(self.app.get_soldier_by_id(999))

    def test_get_soldier_by_id_invalid(self):
        self.assertIsNone(self.app.get_soldier_by_id("invalid"))

    def test_get_mission_by_id(self):
        self.app.missions = {1: "mission1", 2: "mission2"}

        self.assertEqual(self.app.get_mission_by_id(1), "mission1")
        self.assertIsNone(self.app.get_mission_by_id(3))

    def test_get_mission_participants(self):
        self.app.mission_participants = {1: [1, 2], 2: [3]}

        self.assertEqual(self.app.get_mission_participants(1), [1, 2])
        self.assertEqual(self.app.get_mission_participants(3), [])

    def test_show_frame(self):
        # Restore actual show_frame method to test it
        self.app.show_frame = App.show_frame.__get__(self.app)

        mock_frame = MagicMock()
        mock_cont = MagicMock()
        self.app.frames = {mock_cont: mock_frame}

        self.app.show_frame(mock_cont, "arg1", "arg2")

        mock_frame.update_view.assert_called_once_with("arg1", "arg2")
        mock_frame.tkraise.assert_called_once()

    def test_show_frame_no_update_view(self):
        # Restore actual show_frame method to test it
        self.app.show_frame = App.show_frame.__get__(self.app)

        class MockFrameWithoutUpdateView:
            def __init__(self):
                self.tkraise = MagicMock()

        mock_frame = MockFrameWithoutUpdateView()
        mock_cont = MagicMock()
        self.app.frames = {mock_cont: mock_frame}

        self.app.show_frame(mock_cont, "arg1")

        mock_frame.tkraise.assert_called_once()

if __name__ == "__main__":
    unittest.main()
