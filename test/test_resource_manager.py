"""Tests for src/resource_manager.py."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from resource_manager import ResourceManager

REFERENCE = Path(__file__).resolve().parent.parent / "reference"
UFO_DIR = REFERENCE / "UFO"


def test_resource_manager_mod_sprite(tmp_path):
    # Create a test sprite image
    mod_dir = tmp_path / "mod"
    res_dir = mod_dir / "Resources"
    res_dir.mkdir(parents=True)
    img_path = res_dir / "test_icon.png"
    Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(img_path)

    dm = MagicMock()
    dm.extraSprites = {
        "TEST_SPRITE": {
            "_source_dir": str(mod_dir),
            "files": {0: "Resources/test_icon.png"},
        }
    }
    dm.base_path = str(tmp_path)

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    # Test CTkImage
    ctk_img = rm.get_sprite("TEST_SPRITE", index=0, ctk_image=True)
    assert ctk_img is not None

    # Test PIL image
    pil_img = rm.get_sprite("TEST_SPRITE", index=0, ctk_image=False)
    assert isinstance(pil_img, Image.Image)
    assert pil_img.size == (16, 16)

    # Test caching
    cached = rm.get_sprite("TEST_SPRITE", index=0, ctk_image=False)
    assert cached is pil_img


def test_resource_manager_path_traversal_blocked(tmp_path):
    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()

    dm = MagicMock()
    dm.extraSprites = {
        "EVIL_SPRITE": {
            "_source_dir": str(mod_dir),
            "files": {0: "../../secret.png"},
        }
    }
    dm.base_path = str(tmp_path)

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    assert rm.get_sprite("EVIL_SPRITE") is None


def test_resource_manager_vanilla_resolution_and_getters(tmp_path):
    # Mock data manager pointing to real reference folder if available
    dm = MagicMock()
    dm.base_path = str(REFERENCE)
    dm.master = "xcom1"
    dm.extraSprites = {}
    dm.facilities = {
        "STR_ACCESS_LIFT": {"spriteFacility": 17},
        "STR_LIVING_QUARTERS": {"spriteFacility": 18},
    }
    dm.items = {
        "STR_LASER_RIFLE": {"bigSprite": 0},
        "STR_PISTOL": {"bigSprite": 1},
    }

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")

    if (UFO_DIR / "GEODATA" / "PALETTES.DAT").is_file():
        # Facility sprite
        fac_img = rm.get_facility_sprite("STR_ACCESS_LIFT", ctk_image=False)
        assert isinstance(fac_img, Image.Image)
        assert fac_img.size == (32, 40)

        # Item sprite
        item_img = rm.get_item_sprite("STR_LASER_RIFLE", ctk_image=False)
        assert isinstance(item_img, Image.Image)
        assert item_img.size == (32, 48)

        # Smoke sprite
        smoke_img = rm.get_smoke_sprite(0, ctk_image=False)
        assert isinstance(smoke_img, Image.Image)
        assert smoke_img.size == (32, 40)

        # get_sprite archive fallback
        archive_sprite = rm.get_sprite("BASEBITS.PCK", index=17, ctk_image=False)
        assert isinstance(archive_sprite, Image.Image)
        assert archive_sprite.size == (32, 40)

        # Dict argument support
        dict_fac = rm.get_facility_sprite({"spriteFacility": 18}, ctk_image=False)
        assert isinstance(dict_fac, Image.Image)
        assert dict_fac.size == (32, 40)


def test_resource_manager_mod_override_over_vanilla(tmp_path):
    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()
    custom_icon = mod_dir / "custom_lift.png"
    Image.new("RGBA", (32, 40), (0, 255, 0, 255)).save(custom_icon)

    dm = MagicMock()
    dm.base_path = str(REFERENCE)
    dm.master = "xcom1"
    dm.extraSprites = {
        "BASEBITS.PCK": {
            "_source_dir": str(mod_dir),
            "files": {17: "custom_lift.png"},
        }
    }
    dm.facilities = {"STR_ACCESS_LIFT": {"spriteFacility": 17}}

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    # Even if vanilla exists, the mod extraSprites definition should take precedence
    fac_img = rm.get_facility_sprite("STR_ACCESS_LIFT", ctk_image=False)
    assert isinstance(fac_img, Image.Image)
    assert fac_img.getpixel((0, 0)) == (0, 255, 0, 255)
