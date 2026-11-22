"""Tests for src/resource_manager.py."""

import os
import struct
import sys
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import pck_decoder as pd
from resource_manager import ResourceManager

REFERENCE = Path(__file__).resolve().parent.parent / "reference"
UFO_DIR = REFERENCE / "UFO"


def _make_synthetic_vanilla_ufo(base_dir: Path) -> Path:
    """Create minimal UFO/GEODATA and GEOGRAPH/BASEBITS files for offline tests."""
    ufo_dir = base_dir / "UFO"
    (ufo_dir / "GEODATA").mkdir(parents=True)
    pal = bytearray(pd.PALETTE_RECORD_SIZE * 5)
    for i in range(5):
        pal[i * pd.PALETTE_RECORD_SIZE + 3 : i * pd.PALETTE_RECORD_SIZE + 6] = bytes(
            [63, 0, 0]
        )
    (ufo_dir / "GEODATA" / "PALETTES.DAT").write_bytes(bytes(pal))

    (ufo_dir / "GEOGRAPH").mkdir(parents=True)
    frame = bytes([0, 1, 0xFF])
    (ufo_dir / "GEOGRAPH" / "BASEBITS.PCK").write_bytes(frame + frame)
    (ufo_dir / "GEOGRAPH" / "BASEBITS.TAB").write_bytes(
        struct.pack("<HH", 0, len(frame))
    )
    return ufo_dir


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


def test_partial_mod_override_falls_back_to_vanilla(tmp_path):
    """Unoverridden indices in a modded archive must fall back to vanilla PCK."""
    _make_synthetic_vanilla_ufo(tmp_path)

    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()
    green_icon = mod_dir / "mod_76.png"
    Image.new("RGBA", (32, 40), (0, 255, 0, 255)).save(green_icon)

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.master = "xcom1"
    dm.extraSprites = {
        "BASEBITS.PCK": {
            "_source_dir": str(mod_dir),
            "_file_sources": {76: str(mod_dir)},
            "files": {76: "mod_76.png"},
        }
    }

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")

    mod_img = rm.get_basebit_sprite(76, ctk_image=False)
    assert mod_img is not None
    assert mod_img.getpixel((0, 0)) == (0, 255, 0, 255)

    # Index 0 is not in extraSprites: must decode red vanilla sprite, not mod index 76.
    vanilla_via_basebit = rm.get_basebit_sprite(0, ctk_image=False)
    vanilla_via_get_sprite = rm.get_sprite("BASEBITS.PCK", index=0, ctk_image=False)
    assert vanilla_via_basebit is not None
    assert vanilla_via_basebit.getpixel((0, 0)) == (252, 0, 0, 255)
    assert vanilla_via_get_sprite is not None
    assert vanilla_via_get_sprite.getpixel((0, 0)) == (252, 0, 0, 255)


def test_multi_mod_per_index_file_sources(tmp_path):
    """Each index in extraSprites resolves from its own originating mod directory."""
    mod_a = tmp_path / "mod_a"
    mod_b = tmp_path / "mod_b"
    mod_a.mkdir()
    mod_b.mkdir()
    Image.new("RGBA", (32, 40), (0, 0, 255, 255)).save(mod_a / "a.png")
    Image.new("RGBA", (32, 40), (255, 255, 0, 255)).save(mod_b / "b.png")

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.extraSprites = {
        "BASEBITS.PCK": {
            "_source_dir": str(mod_b),
            "_file_sources": {10: str(mod_a), 20: str(mod_b)},
            "files": {10: "a.png", 20: "b.png"},
        }
    }

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    assert rm.get_basebit_sprite(10, ctk_image=False).getpixel((0, 0)) == (
        0,
        0,
        255,
        255,
    )
    assert rm.get_basebit_sprite(20, ctk_image=False).getpixel((0, 0)) == (
        255,
        255,
        0,
        255,
    )


def test_json_stringified_keys_matched(tmp_path):
    """Stringified integer keys (e.g. from JSON) still match integer indices."""
    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()
    Image.new("RGBA", (32, 40), (12, 34, 56, 255)).save(mod_dir / "custom.png")

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.extraSprites = {
        "BASEBITS.PCK": {
            "_source_dir": str(mod_dir),
            "_file_sources": {"17": str(mod_dir)},
            "files": {"17": "custom.png"},
        }
    }

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    img = rm.get_basebit_sprite(17, ctk_image=False)
    assert img is not None
    assert img.getpixel((0, 0)) == (12, 34, 56, 255)


def test_reset_and_clear_cache(tmp_path):
    """reset() clears memory caches/extractor; clear_cache() also removes disk PNGs."""
    _make_synthetic_vanilla_ufo(tmp_path)
    cache_dir = tmp_path / "sprite_cache"

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.master = "xcom1"
    dm.extraSprites = {}

    rm = ResourceManager(dm, cache_dir=cache_dir)
    img = rm.get_basebit_sprite(0, ctk_image=False)
    assert img is not None
    assert rm.vanilla_extractor is not None
    assert len(rm.image_cache) > 0
    assert list(cache_dir.rglob("*.png"))

    rm.reset()
    assert rm.image_cache == {}
    assert rm.vanilla_extractor is None
    assert list(cache_dir.rglob("*.png"))

    assert rm.get_basebit_sprite(0, ctk_image=False) is not None
    rm.clear_cache()
    assert rm.image_cache == {}
    assert rm.vanilla_extractor is None
    assert not cache_dir.exists()
