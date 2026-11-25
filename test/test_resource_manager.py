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


def _make_synthetic_basebits_ufo(
    base_dir: Path, frame_colors: dict[int, int] | None = None
) -> Path:
    """Create minimal UFO assets with multi-frame BASEBITS.PCK for layout tests."""
    ufo_dir = base_dir / "UFO"
    (ufo_dir / "GEODATA").mkdir(parents=True, exist_ok=True)
    pal = bytearray(pd.PALETTE_RECORD_SIZE * 5)
    # Index 1=red, 2=green, 3=blue, 4=yellow, 5=magenta, 6=cyan, 7=gray
    vga_colors = {
        1: (63, 0, 0),
        2: (0, 63, 0),
        3: (0, 0, 63),
        4: (63, 63, 0),
        5: (63, 0, 63),
        6: (0, 63, 63),
        7: (10, 10, 10),
    }
    for pal_idx in range(5):
        pal_off = pal_idx * pd.PALETTE_RECORD_SIZE
        for color_idx, rgb in vga_colors.items():
            pal[pal_off + color_idx * 3 : pal_off + color_idx * 3 + 3] = bytes(rgb)
    (ufo_dir / "GEODATA" / "PALETTES.DAT").write_bytes(bytes(pal))

    colors = frame_colors or {}
    total_frames = max([2, *colors.keys()]) + 1
    pck_buf = bytearray()
    offsets: list[int] = []
    for idx in range(total_frames):
        offsets.append(len(pck_buf))
        color = colors.get(idx, 1)
        # Skip 0 rows, draw pixel 0 with `color`, end of frame
        pck_buf.extend(bytes([0, color, 0xFF]))

    (ufo_dir / "GEOGRAPH").mkdir(parents=True, exist_ok=True)
    (ufo_dir / "GEOGRAPH" / "BASEBITS.PCK").write_bytes(bytes(pck_buf))
    (ufo_dir / "GEOGRAPH" / "BASEBITS.TAB").write_bytes(
        struct.pack(f"<{len(offsets)}H", *offsets)
    )
    return ufo_dir


def _make_synthetic_vanilla_ufo(base_dir: Path) -> Path:
    """Create minimal UFO/GEODATA and GEOGRAPH/BASEBITS files for offline tests."""
    return _make_synthetic_basebits_ufo(base_dir, frame_colors={0: 1, 1: 1})


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


def test_get_craft_and_rank_sprites(tmp_path):
    """Craft and rank helpers resolve expected BASEBITS sprite offsets."""
    _make_synthetic_basebits_ufo(tmp_path, frame_colors={33: 2, 44: 3})

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.master = "xcom1"
    dm.extraSprites = {}
    dm.crafts = {"STR_SKYRANGER": {"sprite": 0}}
    dm.soldiers = {"STR_SOLDIER": {}}

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")

    craft_img = rm.get_craft_sprite("STR_SKYRANGER", ctk_image=False)
    assert craft_img is not None
    assert craft_img.getpixel((0, 0)) == (0, 252, 0, 255)

    rank_img = rm.get_rank_sprite(2, "STR_SOLDIER", ctk_image=False)
    assert rank_img is not None
    assert rank_img.getpixel((0, 0)) == (0, 0, 252, 255)

    assert rm.get_rank_sprite(-1) is None
    assert rm.get_rank_sprite(True) is None


def test_render_base_layout_hangars_and_parked_craft(tmp_path):
    """Base layout composites 1x1 facilities, 2x2 hangars, construction, and craft."""
    frame_colors = {
        0: 7,  # dirt (dark gray)
        1: 6,  # lift shape (cyan)
        2: 1,  # lift facility (red)
        9: 2,  # hangar UL (green)
        10: 2,  # hangar UR
        11: 2,  # hangar LL
        12: 2,  # hangar LR
        13: 4,  # construction UL (yellow)
        14: 4,  # construction UR
        15: 4,  # construction LL
        16: 4,  # construction LR
        33: 5,  # Skyranger (magenta)
    }
    _make_synthetic_basebits_ufo(tmp_path, frame_colors=frame_colors)

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.master = "xcom1"
    dm.extraSprites = {}
    dm.facilities = {
        "STR_ACCESS_LIFT": {"spriteShape": 1, "spriteFacility": 2},
        "STR_HANGAR": {"spriteShape": 9, "spriteFacility": 9, "size": 2, "crafts": 1},
    }
    dm.crafts = {"STR_SKYRANGER": {"sprite": 0}}

    fac_lift = MagicMock(type="STR_ACCESS_LIFT", x=2, y=2, build_time=0)
    fac_hangar_done = MagicMock(type="STR_HANGAR", x=0, y=0, build_time=0)
    fac_hangar_wip = MagicMock(type="STR_HANGAR", x=4, y=0, build_time=5)
    craft_parked = MagicMock(type="STR_SKYRANGER", status="STR_READY")
    craft_extra = MagicMock(type="STR_SKYRANGER", status="STR_READY")
    base = MagicMock(
        facilities=[fac_lift, fac_hangar_done, fac_hangar_wip],
        crafts=[craft_parked, craft_extra],
    )

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    img = rm.render_base_layout(base, scale=2, ctk_image=False)

    assert img is not None
    assert img.size == (384, 384)
    # Completed 2x2 hangar corners at (0,0), (1,0), (0,1), (1,1) -> green
    for gx, gy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        assert img.getpixel((gx * 64, gy * 64)) == (0, 252, 0, 255)
    # Parked Skyranger centered inside 2x2 hangar at (0, 0) -> (32, 24)
    assert img.getpixel((32, 24)) == (252, 0, 252, 255)
    # Under-construction 2x2 hangar at (4, 0) -> yellow, and no craft parked inside
    for gx, gy in ((4, 0), (5, 0), (4, 1), (5, 1)):
        assert img.getpixel((gx * 64, gy * 64)) == (252, 252, 0, 255)
    assert img.getpixel((4 * 64 + 32, 24)) != (252, 0, 252, 255)
    # Lift at (2, 2) -> facility red overrides shape cyan at (0, 0)
    assert img.getpixel((2 * 64, 2 * 64)) == (252, 0, 0, 255)
    # Empty dirt cell at (5, 5)
    assert img.getpixel((5 * 64, 5 * 64)) == (40, 40, 40, 255)


def test_render_base_layout_real_ufo(tmp_path):
    """Verify render_base_layout works end-to-end with real UFO BASEBITS.PCK."""
    if not (UFO_DIR / "GEODATA" / "PALETTES.DAT").is_file():
        return

    dm = MagicMock()
    dm.base_path = str(REFERENCE)
    dm.master = "xcom1"
    dm.extraSprites = {}
    dm.facilities = {
        "STR_ACCESS_LIFT": {"spriteShape": 2, "spriteFacility": 17},
        "STR_HANGAR": {"spriteShape": 9, "spriteFacility": 9, "size": 2, "crafts": 1},
    }
    dm.crafts = {"STR_SKYRANGER": {"sprite": 0}}

    base = MagicMock(
        facilities=[
            MagicMock(type="STR_ACCESS_LIFT", x=2, y=2, build_time=0),
            MagicMock(type="STR_HANGAR", x=0, y=0, build_time=0),
        ],
        crafts=[MagicMock(type="STR_SKYRANGER", status="STR_READY")],
    )

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    img = rm.render_base_layout(base, scale=2, ctk_image=False)
    assert img is not None
    assert img.size == (384, 384)
    assert img.getbbox() == (0, 0, 384, 384)


def test_get_soldier_sprite_vanilla_and_recolor(tmp_path):
    """Soldier sprites compose armor torso by gender and recolor face/hair by look."""
    ufo_dir = _make_synthetic_basebits_ufo(tmp_path)
    (ufo_dir / "UNITS").mkdir(parents=True, exist_ok=True)

    # Extend palette so face group 6 (96) -> red, face target 160 -> blue,
    # hair group 9 (144) -> green, hair target 245 -> yellow.
    pal_path = ufo_dir / "GEODATA" / "PALETTES.DAT"
    pal_bytes = bytearray(pal_path.read_bytes())
    bat_off = pd.PALETTE_BATTLESCAPE * pd.PALETTE_RECORD_SIZE
    pal_bytes[bat_off + 96 * 3 : bat_off + 96 * 3 + 3] = bytes([63, 0, 0])
    pal_bytes[bat_off + 160 * 3 : bat_off + 160 * 3 + 3] = bytes([0, 0, 63])
    pal_bytes[bat_off + 144 * 3 : bat_off + 144 * 3 + 3] = bytes([0, 63, 0])
    pal_bytes[bat_off + 245 * 3 : bat_off + 245 * 3 + 3] = bytes([63, 63, 0])
    pal_path.write_bytes(bytes(pal_bytes))

    # Build XCOM_0.PCK with 275 frames:
    # frame 3 (r-arm): face idx 96 at (0,0) and hair idx 144 at (1,0)
    # frame 11 (l-arm): transparent
    # frame 19 (legs): color 7 at (2,0)
    # frame 35 (male torso): green color 2 at (3,0)
    # frame 270 (female torso): cyan color 6 at (3,0)
    pck_buf = bytearray()
    offsets: list[int] = []
    for idx in range(275):
        offsets.append(len(pck_buf))
        if idx == 3:
            pck_buf.extend(bytes([0, 96, 144, 0xFF]))
        elif idx == 19:
            pck_buf.extend(bytes([0, 0xFE, 2, 7, 0xFF]))
        elif idx == 35:
            pck_buf.extend(bytes([0, 0xFE, 3, 2, 0xFF]))
        elif idx == 270:
            pck_buf.extend(bytes([0, 0xFE, 3, 6, 0xFF]))
        else:
            pck_buf.extend(bytes([0, 0xFF]))

    (ufo_dir / "UNITS" / "XCOM_0.PCK").write_bytes(bytes(pck_buf))
    (ufo_dir / "UNITS" / "XCOM_0.TAB").write_bytes(
        struct.pack(f"<{len(offsets)}H", *offsets)
    )

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.master = "xcom1"
    dm.extraSprites = {}
    dm.armors = {
        "STR_NONE_UC": {
            "spriteSheet": "XCOM_0.PCK",
            "spriteFaceGroup": 6,
            "spriteFaceColor": [96, 96, 96, 96, 160, 160],
            "spriteHairGroup": 9,
            "spriteHairColor": [144, 144, 144, 144, 245, 245],
        }
    }

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    male_look0 = MagicMock(armor="STR_NONE_UC", gender=0, look=0)
    female_look0 = MagicMock(armor="STR_NONE_UC", gender=1, look=0)
    male_look2 = MagicMock(armor="STR_NONE_UC", gender=0, look=2)

    img_m0 = rm.get_soldier_sprite(male_look0, ctk_image=False)
    img_f0 = rm.get_soldier_sprite(female_look0, ctk_image=False)
    img_m2 = rm.get_soldier_sprite(male_look2, ctk_image=False)

    assert img_m0 is not None and img_m0.size == (32, 40)
    # Torso differs by gender: male green vs female cyan at (3, 0)
    assert img_m0.getpixel((3, 0)) == (0, 252, 0, 255)
    assert img_f0.getpixel((3, 0)) == (0, 252, 252, 255)
    # Face/hair differ by look: look=0 (96/144) vs look=2 (160/245)
    assert img_m0.getpixel((0, 0)) == (252, 0, 0, 255)
    assert img_m2.getpixel((0, 0)) == (0, 0, 252, 255)
    assert img_m0.getpixel((1, 0)) == (0, 252, 0, 255)
    assert img_m2.getpixel((1, 0)) == (252, 252, 0, 255)


def test_get_soldier_sprite_mod_sheet_and_recolor(tmp_path):
    """Modded paletted extraSprites unit sheets slice subX/subY and recolor ramps."""
    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()

    # Create 128x40 paletted PNG (4 frames of 32x40); frame 3 draws palette idx 96
    sheet = Image.new("P", (128, 40), 0)
    pal = [0] * 768
    pal[96 * 3 : 96 * 3 + 3] = [200, 10, 10]
    pal[160 * 3 : 160 * 3 + 3] = [10, 200, 10]
    sheet.putpalette(pal)
    sheet.info["transparency"] = 0
    sheet.putpixel((3 * 32, 0), 96)
    sheet.save(mod_dir / "unit.png", transparency=0)

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.extraSprites = {
        "MOD_UNIT.PCK": {
            "subX": 32,
            "subY": 40,
            "_source_dir": str(mod_dir),
            "_file_sources": {0: str(mod_dir)},
            "files": {0: "unit.png"},
        }
    }
    dm.armors = {
        "STR_MOD_ARMOR": {
            "spriteSheet": "MOD_UNIT.PCK",
            "drawingRoutine": 4,
            "spriteFaceGroup": 6,
            "spriteFaceColor": [96, 96, 160, 160],
        }
    }

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    s0 = rm.get_soldier_sprite(
        MagicMock(armor="STR_MOD_ARMOR", gender=0, look=0), ctk_image=False
    )
    s1 = rm.get_soldier_sprite(
        MagicMock(armor="STR_MOD_ARMOR", gender=0, look=1), ctk_image=False
    )
    assert s0 is not None and s0.getpixel((0, 0)) == (200, 10, 10, 255)
    assert s1 is not None and s1.getpixel((0, 0)) == (10, 200, 10, 255)


def test_render_game_text_and_storage_tile(tmp_path):
    """Game font renders counts cleanly onto 64x96 storage grid tiles."""
    dm = MagicMock()
    dm.base_path = str(REFERENCE if (REFERENCE / "common").is_dir() else tmp_path)
    dm.master = "xcom1"
    dm.extraSprites = {}
    dm.items = {"STR_LASER_RIFLE": {"bigSprite": 0}}

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    txt = rm.render_game_text("42", scale=2)
    assert txt.mode == "RGBA"
    assert txt.getbbox() is not None

    tile = rm.render_storage_item_tile("STR_LASER_RIFLE", 42, scale=2, ctk_image=False)
    assert tile.size == (64, 96)
    assert tile.mode == "RGBA"
    # Bottom-right region should contain non-background text pixels
    br_region = tile.crop((32, 70, 64, 96))
    colors = br_region.getcolors(maxcolors=256)
    assert colors is not None and len(colors) > 1

    # Fallback path without FontSmall.png also produces valid RGBA image
    dm_empty = MagicMock()
    dm_empty.base_path = str(tmp_path)
    rm_fallback = ResourceManager(dm_empty, cache_dir=tmp_path / "cache2")
    fallback_txt = rm_fallback.render_game_text("99", scale=1)
    assert fallback_txt.mode == "RGBA" and fallback_txt.getbbox() is not None


def test_render_storage_grid_packs_items_without_text_labels(tmp_path):
    """Contiguous storage grid packs 1x1, 1x2, and 2x3 items with count overlays."""
    ufo_dir = _make_synthetic_basebits_ufo(tmp_path)
    (ufo_dir / "UNITS").mkdir(parents=True, exist_ok=True)

    # Create BIGOBS.PCK with frame 0 (red pixel at (0, 0)) and frame 1 (green pixel)
    frame0 = bytes([0, 1, 0xFF])
    frame1 = bytes([0, 2, 0xFF])
    (ufo_dir / "UNITS" / "BIGOBS.PCK").write_bytes(frame0 + frame1)
    (ufo_dir / "UNITS" / "BIGOBS.TAB").write_bytes(struct.pack("<HH", 0, len(frame0)))

    dm = MagicMock()
    dm.base_path = str(tmp_path)
    dm.master = "xcom1"
    dm.extraSprites = {}
    dm.items = {
        "STR_RIFLE": {"bigSprite": 0, "invWidth": 2, "invHeight": 3},
        "STR_PISTOL": {"bigSprite": 1, "invWidth": 1, "invHeight": 2},
        "STR_GRENADE": {"bigSprite": 0, "invWidth": 1, "invHeight": 1},
    }

    rm = ResourceManager(dm, cache_dir=tmp_path / "cache")
    grid_img = rm.render_storage_grid(
        [("STR_RIFLE", 5), ("STR_PISTOL", 12), ("STR_GRENADE", 120)],
        grid_cols=6,
        scale=2,
        ctk_image=False,
    )

    assert grid_img is not None
    assert grid_img.width == 6 * 32
    assert grid_img.height >= 6 * 32
    assert grid_img.height % 32 == 0
    assert rm.render_storage_grid([], grid_cols=6, scale=2, ctk_image=False) is None
