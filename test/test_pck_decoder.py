"""Tests for src/pck_decoder.py.

Unit tests use small synthetic byte buffers and always run.
Integration tests decode real vanilla files from reference/UFO and reference/TFTD
and are skipped automatically when those folders are absent.
"""

import os
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import pck_decoder as pd

REFERENCE = Path(__file__).resolve().parent.parent / "reference"
UFO_DIR = REFERENCE / "UFO"
TFTD_DIR = REFERENCE / "TFTD"

needs_ufo = pytest.mark.skipif(
    not (UFO_DIR / "GEODATA" / "PALETTES.DAT").is_file(),
    reason="reference/UFO vanilla files not present",
)
needs_tftd = pytest.mark.skipif(
    not (TFTD_DIR / "MISSDAT" / "BASE.DAT").is_file(),
    reason="reference/TFTD vanilla files not present",
)

RED = (252, 0, 0, 255)
CLEAR = (0, 0, 0, 0)


@pytest.fixture
def red_palette():
    """A palette where index 1 is pure red and everything else is black."""
    raw = bytearray(pd.PALETTE_RECORD_SIZE)
    raw[3:6] = bytes([63, 0, 0])
    return pd.parse_palettes_bytes(bytes(raw))[0]


# --- Palettes -----------------------------------------------------------------


def test_parse_palettes_converts_vga_and_index0_transparent(red_palette):
    assert len(red_palette) == 256
    assert red_palette[0] == CLEAR
    assert red_palette[1] == RED
    assert red_palette[2] == (0, 0, 0, 255)


def test_parse_palettes_multiple_records():
    data = bytes(pd.PALETTE_RECORD_SIZE * 3)
    assert len(pd.parse_palettes_bytes(data)) == 3


def test_parse_palettes_too_short():
    with pytest.raises(ValueError):
        pd.parse_palettes_bytes(b"\x00" * 10)


def test_apply_backpals(red_palette):
    backpals = bytearray(pd.BACKPALS_SUBPALETTE_BYTES * 2)
    backpals[48:51] = bytes([0, 63, 0])  # sub-palette 1, colour 0 = green
    merged = pd.apply_backpals(red_palette, bytes(backpals), subpalette_index=1)
    assert merged[224] == (0, 252, 0, 255)
    assert merged[1] == RED


def test_apply_backpals_out_of_range(red_palette):
    with pytest.raises(ValueError):
        pd.apply_backpals(red_palette, bytes(48), subpalette_index=1)


# --- TAB / PCK ----------------------------------------------------------------


def test_parse_tab_uint16_and_uint32():
    assert pd.parse_tab_bytes(struct.pack("<HH", 0, 5)) == [0, 5]
    assert pd.parse_tab_bytes(struct.pack("<II", 0, 70000), offset_size=4) == [
        0,
        70000,
    ]


@pytest.mark.parametrize("data,size", [(b"\x00\x00\x00", 2), (b"\x00\x00", 3)])
def test_parse_tab_invalid(data, size):
    with pytest.raises(ValueError):
        pd.parse_tab_bytes(data, offset_size=size)


def test_decode_pck_archive_rle(red_palette):
    # Frame 0: skip 1 row, skip 2 px, draw colour 1, end.
    # Frame 1: no skip, draw colour 1 twice, end.
    frame0 = bytes([1, 0xFE, 2, 1, 0xFF])
    frame1 = bytes([0, 1, 1, 0xFF])
    tab = struct.pack("<HH", 0, len(frame0))
    frames = pd.decode_pck_archive(frame0 + frame1, tab, red_palette, 4, 4)
    assert len(frames) == 2
    assert frames[0].getpixel((2, 1)) == RED
    assert frames[0].getpixel((0, 0)) == CLEAR
    assert frames[1].getpixel((0, 0)) == RED
    assert frames[1].getpixel((1, 0)) == RED
    assert frames[1].getpixel((2, 0)) == CLEAR


def test_decode_pck_without_tab_and_overflow_is_safe(red_palette):
    # More pixels than fit in 2x2: extras must be ignored, not crash.
    frames = pd.decode_pck_archive(
        bytes([0, 1, 1, 1, 1, 1, 1]), None, red_palette, 2, 2
    )
    assert len(frames) == 1
    assert frames[0].getpixel((1, 1)) == RED


def test_decode_pck_offset_past_end(red_palette):
    img = pd.decode_pck_frame(b"\x00", red_palette, start_offset=5, width=2, height=2)
    assert img.getpixel((0, 0)) == CLEAR


# --- Full-screen formats ------------------------------------------------------


def test_decode_spk(red_palette):
    # Skip 1 word (2 px), draw 1 word (2 px of colour 1), EOF.
    data = struct.pack("<HHHH", 0xFFFF, 1, 0xFFFE, 1) + bytes([1, 1])
    data += struct.pack("<H", 0xFFFD)
    img = pd.decode_spk_bytes(data, red_palette, width=4, height=1)
    assert [img.getpixel((x, 0)) for x in range(4)] == [CLEAR, CLEAR, RED, RED]


def test_decode_bdy(red_palette):
    # Row 0: run of 3 x colour 1 (code 254 -> 257-254 = 3), then 1 literal 0.
    # Row 1: literal of 4 bytes (code 3).
    data = bytes([254, 1, 0, 0, 3, 0, 1, 0, 1])
    img = pd.decode_bdy_bytes(data, red_palette, width=4, height=2)
    assert [img.getpixel((x, 0)) for x in range(4)] == [RED, RED, RED, CLEAR]
    assert [img.getpixel((x, 1)) for x in range(4)] == [CLEAR, RED, CLEAR, RED]


def test_decode_scr(red_palette):
    img = pd.decode_scr_bytes(bytes([0, 1, 1, 0]), red_palette, width=2, height=2)
    assert img.getpixel((1, 0)) == RED
    assert img.getpixel((0, 1)) == RED
    assert img.getpixel((0, 0)) == CLEAR


# --- SOLDIER.DAT / BASE.DAT ---------------------------------------------------


def _soldier_record(name: bytes, rank: int = 2) -> bytearray:
    rec = bytearray(pd.SOLDIER_DAT_RECORD_SIZE)
    struct.pack_into("<HHHHHHH", rec, 0, rank, 0, 1, 0, 5, 7, 3)
    rec[16 : 16 + len(name)] = name
    rec[42:52] = bytes([50, 30, 40, 45, 25, 60, 55, 20, 70, 0])
    rec[52] = 6  # initial bravery = 110 - 60 = 50
    rec[53:62] = bytes([1, 2, 3, 4, 5, 6, 7, 8, 1])  # +10 bravery
    rec[62], rec[66], rec[67] = 1, 1, 2
    return rec


def test_parse_soldier_dat():
    empty = bytearray(pd.SOLDIER_DAT_RECORD_SIZE)
    struct.pack_into("<H", empty, 0, 0xFFFF)
    data = bytes(_soldier_record(b"Jane Doe") + empty)
    soldiers = pd.parse_soldier_dat_bytes(data)
    assert len(soldiers) == 1
    s = soldiers[0]
    assert (s.name, s.rank, s.missions, s.kills) == ("Jane Doe", 2, 5, 7)
    assert s.initial_stats["tu"] == 50
    assert s.initial_stats["bravery"] == 50
    assert s.current_stats["tu"] == 51
    assert s.current_stats["bravery"] == 60
    assert (s.armor, s.gender, s.appearance) == (1, 1, 2)


def test_parse_soldier_dat_bad_size():
    with pytest.raises(ValueError):
        pd.parse_soldier_dat_bytes(bytes(70))


@pytest.mark.parametrize(
    "is_tftd,size,grid,disabled",
    [
        (False, 292, 0x16, 0x120),
        (True, 296, 0xDA, 0x124),
    ],
)
def test_parse_base_dat_offsets(is_tftd, size, grid, disabled):
    active = bytearray(size)
    active[0:4] = b"Base"
    active[grid : grid + 36] = bytes(range(36))
    active[grid + 72] = 9  # engineers
    active[grid + 73] = 4  # scientists
    inactive = bytearray(active)
    inactive[disabled] = 1
    bases = pd.parse_base_dat_bytes(bytes(active + inactive), is_tftd=is_tftd)
    assert len(bases) == 1
    b = bases[0]
    assert b.name == "Base"
    assert b.facilities_grid[0] == [0, 1, 2, 3, 4, 5]
    assert b.facilities_grid[5][5] == 35
    assert (b.engineers, b.scientists) == (9, 4)


def test_parse_base_dat_bad_size():
    with pytest.raises(ValueError):
        pd.parse_base_dat_bytes(bytes(100))


# --- VanillaAssetExtractor (synthetic game dir) -------------------------------


@pytest.fixture
def fake_game_dir(tmp_path):
    """Minimal game dir with lowercase names to exercise case-insensitive lookup."""
    pal = bytearray(pd.PALETTE_RECORD_SIZE * 5)
    for i in range(5):
        pal[i * pd.PALETTE_RECORD_SIZE + 3 : i * pd.PALETTE_RECORD_SIZE + 6] = bytes(
            [63, 0, 0]
        )
    (tmp_path / "geodata").mkdir()
    (tmp_path / "geodata" / "palettes.dat").write_bytes(bytes(pal))
    frame = bytes([0, 1, 0xFF])
    for folder, name in (
        ("geograph", "basebits"),
        ("units", "bigobs"),
        ("ufograph", "smoke"),
    ):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / f"{name}.pck").write_bytes(frame + frame)
        (tmp_path / folder / f"{name}.tab").write_bytes(
            struct.pack("<HH", 0, len(frame))
        )
    return tmp_path


def test_extractor_decodes_and_caches(fake_game_dir, tmp_path):
    cache = tmp_path / "cache"
    ex = pd.VanillaAssetExtractor(fake_game_dir, cache)
    img = ex.get_basebit_sprite(1)
    assert img.size == (32, 40)
    assert img.getpixel((0, 0)) == RED
    cached = ex.get_cached_sprite_path("GEOGRAPH/BASEBITS.PCK", 1, pd.PALETTE_BASESCAPE)
    assert cached.is_file()
    # Second call is served from the PNG cache.
    assert ex.get_basebit_sprite(1).getpixel((0, 0)) == RED

    assert ex.get_bigob_sprite(0).size == (32, 48)
    with pytest.raises(IndexError):
        ex.get_bigob_sprite(2)

    assert ex.get_smoke_sprite(0).size == (32, 40)
    with pytest.raises(IndexError):
        ex.get_smoke_sprite(2)


def test_extractor_invalidates_stale_cache_on_source_change(fake_game_dir, tmp_path):
    cache = tmp_path / "cache"
    ex = pd.VanillaAssetExtractor(fake_game_dir, cache)

    assert ex.get_basebit_sprite(0).getpixel((0, 0)) == RED
    cached_png = ex.get_cached_sprite_path(
        "GEOGRAPH/BASEBITS.PCK", 0, pd.PALETTE_BASESCAPE
    )
    cached_mtime = cached_png.stat().st_mtime

    # Update BASEBITS.PCK frame 0 to draw palette index 2 (opaque black) and bump mtime.
    pck_path = fake_game_dir / "geograph" / "basebits.pck"
    new_frame = bytes([0, 2, 0xFF])
    pck_path.write_bytes(new_frame + new_frame)
    os.utime(pck_path, (cached_mtime + 10, cached_mtime + 10))

    assert ex.get_basebit_sprite(0).getpixel((0, 0)) == (0, 0, 0, 255)

    # Update PALETTES.DAT so index 2 becomes blue and bump mtime beyond the new PNG.
    new_cached_mtime = cached_png.stat().st_mtime
    pal_path = fake_game_dir / "geodata" / "palettes.dat"
    pal_bytes = bytearray(pal_path.read_bytes())
    for i in range(5):
        offset = i * pd.PALETTE_RECORD_SIZE + 6
        pal_bytes[offset : offset + 3] = bytes([0, 0, 63])
    pal_path.write_bytes(bytes(pal_bytes))
    os.utime(pal_path, (new_cached_mtime + 10, new_cached_mtime + 10))

    assert ex.get_basebit_sprite(0).getpixel((0, 0)) == (0, 0, 252, 255)


def test_extractor_missing_files(tmp_path):
    ex = pd.VanillaAssetExtractor(tmp_path / "nothing", tmp_path / "cache")
    with pytest.raises(FileNotFoundError):
        ex.get_palette()


def test_extractor_bad_palette_index(fake_game_dir, tmp_path):
    ex = pd.VanillaAssetExtractor(fake_game_dir, tmp_path / "cache")
    with pytest.raises(IndexError):
        ex.get_palette(9)


def test_cli_extracts_all(fake_game_dir, tmp_path, capsys):
    cache = tmp_path / "out"
    assert pd.main(["--game-dir", str(fake_game_dir), "--cache-dir", str(cache)]) == 0
    assert len(list(cache.glob("*.png"))) == 6
    assert "Extracted 6 sprites" in capsys.readouterr().out


# --- Integration: real vanilla files ------------------------------------------


@needs_ufo
def test_real_ufo_palettes():
    pals = pd.load_palettes_dat(UFO_DIR / "GEODATA" / "PALETTES.DAT")
    assert len(pals) == 5


@needs_ufo
@pytest.mark.parametrize(
    "archive,palette,height,count",
    [
        ("GEOGRAPH/BASEBITS", pd.PALETTE_BASESCAPE, 40, 54),
        ("UNITS/BIGOBS", pd.PALETTE_BATTLESCAPE, 48, 57),
        ("UFOGRAPH/SMOKE", pd.PALETTE_BATTLESCAPE, 40, 56),
    ],
)
def test_real_ufo_pck_archives(archive, palette, height, count):
    pals = pd.load_palettes_dat(UFO_DIR / "GEODATA" / "PALETTES.DAT")
    frames = pd.decode_pck_archive(
        (UFO_DIR / f"{archive}.PCK").read_bytes(),
        (UFO_DIR / f"{archive}.TAB").read_bytes(),
        pals[palette],
        height=height,
    )
    assert len(frames) == count
    # Every frame should contain at least one visible pixel.
    assert all(f.getbbox() is not None for f in frames)


@needs_ufo
def test_real_ufo_spk():
    pals = pd.load_palettes_dat(UFO_DIR / "GEODATA" / "PALETTES.DAT")
    img = pd.decode_spk_bytes(
        (UFO_DIR / "GEOGRAPH" / "UP001.SPK").read_bytes(), pals[pd.PALETTE_UFOPAEDIA]
    )
    assert img.size == (320, 200)
    assert img.getbbox() == (0, 0, 320, 200)


@needs_ufo
def test_real_ufo_soldier_dat():
    soldiers = pd.parse_soldier_dat_bytes(
        (UFO_DIR / "MISSDAT" / "SOLDIER.DAT").read_bytes()
    )
    assert soldiers
    for s in soldiers:
        assert 0 <= s.rank <= 5
        assert 10 <= s.initial_stats["bravery"] <= 110
        assert s.current_stats["tu"] >= s.initial_stats["tu"]


@needs_ufo
def test_real_ufo_base_dat():
    bases = pd.parse_base_dat_bytes((UFO_DIR / "MISSDAT" / "BASE.DAT").read_bytes())
    assert len(bases) == 1
    flat = [c for row in bases[0].facilities_grid for c in row]
    assert 0x00 in flat  # access lift
    assert all(c <= 0x13 or c == 0xFF for c in flat)


@needs_tftd
def test_real_tftd_base_dat():
    bases = pd.parse_base_dat_bytes(
        (TFTD_DIR / "MISSDAT" / "BASE.DAT").read_bytes(), is_tftd=True
    )
    assert bases
    flat = [c for row in bases[0].facilities_grid for c in row]
    assert 0x00 in flat  # air lock
    assert all(c <= 0x13 or c == 0xFF for c in flat)
