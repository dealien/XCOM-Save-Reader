"""Decoder for vanilla X-COM (UFO: Enemy Unknown / TFTD) binary assets.

Status: experimental. Not yet wired into the GUI (see Issues #25 and #26).
Format notes live in ``docs/VANILLA_BINARY_FORMATS.md``.

Pure-Python + Pillow decoders for the 1994 MicroProse binary formats
documented on UFOPaedia (https://www.ufopaedia.org/Image_Formats):

1. ``PALETTES.DAT`` & ``BACKPALS.DAT``: 6-bit VGA RGB palettes.
2. ``.PCK`` + ``.TAB``: RLE sprite archives (32x40, or 32x48 for ``BIGOBS.PCK``).
3. ``.SPK``, ``.BDY``, ``.SCR``: 320x200 backgrounds and inventory paper dolls.
4. ``SOLDIER.DAT`` (UFO only) & ``BASE.DAT`` (UFO and TFTD): legacy save records.
5. ``VanillaAssetExtractor``: extracts and caches vanilla sprites as PNGs for a
   future ``ResourceManager`` fallback, using ``0o700`` cache directories.

Manual check against a real game install::

    python src/pck_decoder.py --game-dir reference/UFO --cache-dir user/cache/sprites
"""

from __future__ import annotations

import argparse
import logging
import os
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, PngImagePlugin  # noqa: F401 - register PNG writer eagerly

logger = logging.getLogger(__name__)

# Palette indices inside UFO: Enemy Unknown's GEODATA/PALETTES.DAT
PALETTE_GEOSCAPE = 0
PALETTE_BASESCAPE = 1
PALETTE_GRAPHS = 2
PALETTE_UFOPAEDIA = 3
PALETTE_BATTLESCAPE = 4

PALETTE_COLORS = 256
PALETTE_RGB_BYTES = PALETTE_COLORS * 3  # 768 bytes
PALETTE_TRAILER_BYTES = 6
PALETTE_RECORD_SIZE = PALETTE_RGB_BYTES + PALETTE_TRAILER_BYTES  # 774 bytes

BACKPALS_SUBPALETTE_COLORS = 16
BACKPALS_SUBPALETTE_BYTES = BACKPALS_SUBPALETTE_COLORS * 3  # 48 bytes
BACKPALS_TARGET_OFFSET = 224  # Replaces color indices 224..239

DEFAULT_PCK_WIDTH = 32
DEFAULT_PCK_HEIGHT = 40
BIGOBS_PCK_HEIGHT = 48

FULLSCREEN_WIDTH = 320
FULLSCREEN_HEIGHT = 200

SOLDIER_DAT_RECORD_SIZE = 68
SOLDIER_DAT_MAX_RECORDS = 250
UFO_BASE_DAT_RECORD_SIZE = 292
TFTD_BASE_DAT_RECORD_SIZE = 296

# BASE.DAT field offsets differ between games (UFOPaedia BASE.DAT / BASE.DAT_(TFTD)).
# UFO stores the facility grid right after the detection values; TFTD stores the
# item counts first and the grid later.
UFO_BASE_GRID_OFFSET = 0x16
UFO_BASE_DISABLED_OFFSET = 0x120
TFTD_BASE_GRID_OFFSET = 0xDA
TFTD_BASE_DISABLED_OFFSET = 0x124

RGBA = tuple[int, int, int, int]


def _vga6_to_uint8(value: int) -> int:
    """Convert a 6-bit VGA color channel (0..63) to 8-bit RGB (0..255)."""
    return min(255, max(0, (value & 0x3F) * 4))


def parse_palettes_bytes(data: bytes) -> list[list[RGBA]]:
    """Parse raw ``PALETTES.DAT`` bytes into a list of 256-entry RGBA palettes.

    Each palette record in ``PALETTES.DAT`` is 774 bytes: 256 3-byte RGB triplets
    (using 6-bit VGA intensity 0..63) followed by a 6-byte trailer buffer.
    Color index 0 is always treated as transparent ``(0, 0, 0, 0)``.
    """
    if len(data) < PALETTE_RGB_BYTES:
        raise ValueError(
            f"PALETTES.DAT data too short: expected at least "
            f"{PALETTE_RGB_BYTES} bytes, got {len(data)}"
        )

    palettes: list[list[RGBA]] = []
    offset = 0
    while offset + PALETTE_RGB_BYTES <= len(data):
        palette: list[RGBA] = []
        for color_idx in range(PALETTE_COLORS):
            base = offset + color_idx * 3
            r = _vga6_to_uint8(data[base])
            g = _vga6_to_uint8(data[base + 1])
            b = _vga6_to_uint8(data[base + 2])
            palette.append((0, 0, 0, 0) if color_idx == 0 else (r, g, b, 255))
        palettes.append(palette)
        offset += PALETTE_RECORD_SIZE

    return palettes


def load_palettes_dat(filepath: str | Path) -> list[list[RGBA]]:
    """Load all 256-color palettes from a ``PALETTES.DAT`` file on disk."""
    path = Path(filepath)
    return parse_palettes_bytes(path.read_bytes())


def apply_backpals(
    palette: Sequence[RGBA],
    backpals_data: bytes,
    subpalette_index: int = 0,
) -> list[RGBA]:
    """Splice a 16-color ``BACKPALS.DAT`` sub-palette into indices 224..239."""
    start = subpalette_index * BACKPALS_SUBPALETTE_BYTES
    if start + BACKPALS_SUBPALETTE_BYTES > len(backpals_data):
        raise ValueError(
            f"Subpalette index {subpalette_index} out of range for BACKPALS.DAT "
            f"({len(backpals_data)} bytes)"
        )

    merged = list(palette)
    for i in range(BACKPALS_SUBPALETTE_COLORS):
        base = start + i * 3
        r = _vga6_to_uint8(backpals_data[base])
        g = _vga6_to_uint8(backpals_data[base + 1])
        b = _vga6_to_uint8(backpals_data[base + 2])
        merged[BACKPALS_TARGET_OFFSET + i] = (r, g, b, 255)
    return merged


def parse_tab_bytes(tab_data: bytes, offset_size: int = 2) -> list[int]:
    """Parse a ``.TAB`` file into a list of byte offsets into a ``.PCK`` file.

    Args:
        tab_data: Raw bytes of the ``.TAB`` file.
        offset_size: 2 for unsigned 16-bit offsets (UFO and TFTD terrain) or
            4 for unsigned 32-bit offsets (TFTD units).
    """
    if offset_size not in (2, 4):
        raise ValueError(f"offset_size must be 2 or 4, got {offset_size}")
    if len(tab_data) % offset_size != 0:
        raise ValueError(
            f"TAB file size ({len(tab_data)} bytes) is not a multiple of {offset_size}"
        )

    fmt = "<H" if offset_size == 2 else "<I"
    return [val[0] for val in struct.iter_unpack(fmt, tab_data)]


def decode_pck_frame(
    pck_data: bytes,
    palette: Sequence[RGBA],
    start_offset: int = 0,
    width: int = DEFAULT_PCK_WIDTH,
    height: int = DEFAULT_PCK_HEIGHT,
) -> Image.Image:
    """Decode a single RLE-compressed sprite frame from ``.PCK`` bytes.

    PCK RLE algorithm:
    - First byte: number of initial transparent rows (``skip_rows * width`` px).
    - Subsequent bytes until ``0xFF`` (end of sprite):
      - ``0xFE``: next byte ``N`` specifies ``N`` transparent pixels to skip.
      - Any other byte ``C``: draw 1 pixel with ``palette[C]`` (index 0 is transparent).
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if start_offset >= len(pck_data):
        return img

    pixels: list[RGBA] = [(0, 0, 0, 0)] * (width * height)
    total_pixels = width * height

    pos = start_offset
    initial_skip_rows = pck_data[pos]
    pos += 1
    pixel_idx = initial_skip_rows * width

    while pos < len(pck_data):
        b = pck_data[pos]
        pos += 1

        if b == 0xFF:
            break
        if b == 0xFE:
            if pos >= len(pck_data):
                break
            skip_count = pck_data[pos]
            pos += 1
            pixel_idx += skip_count
        else:
            if 0 <= pixel_idx < total_pixels and b != 0:
                pixels[pixel_idx] = palette[b]
            pixel_idx += 1

    img.putdata(pixels)
    return img


def decode_pck_archive(
    pck_data: bytes,
    tab_data: bytes | None,
    palette: Sequence[RGBA],
    width: int = DEFAULT_PCK_WIDTH,
    height: int = DEFAULT_PCK_HEIGHT,
    offset_size: int = 2,
) -> list[Image.Image]:
    """Decode all frames in a ``.PCK`` archive (with an optional ``.TAB``)."""
    if tab_data is None:
        return [
            decode_pck_frame(
                pck_data, palette, start_offset=0, width=width, height=height
            )
        ]

    offsets = parse_tab_bytes(tab_data, offset_size=offset_size)
    return [
        decode_pck_frame(
            pck_data, palette, start_offset=offset, width=width, height=height
        )
        for offset in offsets
    ]


def decode_spk_bytes(
    spk_data: bytes,
    palette: Sequence[RGBA],
    width: int = FULLSCREEN_WIDTH,
    height: int = FULLSCREEN_HEIGHT,
) -> Image.Image:
    """Decode a compressed ``.SPK`` background/paper-doll image (320x200).

    SPK format reads little-endian 16-bit unsigned integers:
    - ``0xFFFF``: read next uint16 ``N`` and skip ``N * 2`` transparent pixels.
    - ``0xFFFE``: read next uint16 ``N``, then read ``N * 2`` palette index bytes.
    - ``0xFFFD``: end of file.
    """
    total_pixels = width * height
    pixels: list[RGBA] = [(0, 0, 0, 0)] * total_pixels
    pixel_idx = 0
    pos = 0

    while pos + 2 <= len(spk_data):
        (flag,) = struct.unpack_from("<H", spk_data, pos)
        pos += 2

        if flag == 0xFFFD:
            break
        if flag == 0xFFFF:
            if pos + 2 > len(spk_data):
                break
            (count_words,) = struct.unpack_from("<H", spk_data, pos)
            pos += 2
            pixel_idx += count_words * 2
        elif flag == 0xFFFE:
            if pos + 2 > len(spk_data):
                break
            (count_words,) = struct.unpack_from("<H", spk_data, pos)
            pos += 2
            byte_count = count_words * 2
            end_pos = min(len(spk_data), pos + byte_count)
            for color_idx in spk_data[pos:end_pos]:
                if 0 <= pixel_idx < total_pixels and color_idx != 0:
                    pixels[pixel_idx] = palette[color_idx]
                pixel_idx += 1
            pos = end_pos
        else:
            break

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.putdata(pixels)
    return img


def decode_bdy_bytes(
    bdy_data: bytes,
    palette: Sequence[RGBA],
    width: int = FULLSCREEN_WIDTH,
    height: int = FULLSCREEN_HEIGHT,
) -> Image.Image:
    """Decode a TFTD ``.BDY`` scanline-RLE image (320x200)."""
    pixels: list[RGBA] = [(0, 0, 0, 0)] * (width * height)
    pos = 0

    for row in range(height):
        col = 0
        row_start = row * width
        while col < width and pos < len(bdy_data):
            code = bdy_data[pos]
            pos += 1
            if code >= 129:
                if pos >= len(bdy_data):
                    break
                run_len = 257 - code
                color_idx = bdy_data[pos]
                pos += 1
                for _ in range(run_len):
                    if col < width and color_idx != 0:
                        pixels[row_start + col] = palette[color_idx]
                    col += 1
            else:
                literal_len = code + 1
                for _ in range(literal_len):
                    if pos >= len(bdy_data):
                        break
                    color_idx = bdy_data[pos]
                    pos += 1
                    if col < width and color_idx != 0:
                        pixels[row_start + col] = palette[color_idx]
                    col += 1

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.putdata(pixels)
    return img


def decode_scr_bytes(
    scr_data: bytes,
    palette: Sequence[RGBA],
    width: int = FULLSCREEN_WIDTH,
    height: int = FULLSCREEN_HEIGHT,
) -> Image.Image:
    """Decode an uncompressed ``.SCR`` or raw image ``.DAT`` file (default 320x200)."""
    total_pixels = width * height
    pixels: list[RGBA] = [(0, 0, 0, 0)] * total_pixels
    limit = min(len(scr_data), total_pixels)
    for idx in range(limit):
        color_idx = scr_data[idx]
        if color_idx != 0:
            pixels[idx] = palette[color_idx]

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.putdata(pixels)
    return img


@dataclass
class VanillaSoldierRecord:
    """Parsed 68-byte record from a legacy UFO: Enemy Unknown ``SOLDIER.DAT`` file."""

    slot_index: int
    name: str
    rank: int
    base_index: int
    craft_index: int
    missions: int
    kills: int
    wound_recovery_days: int
    initial_stats: dict[str, int]
    current_stats: dict[str, int]
    armor: int
    gender: int
    appearance: int


@dataclass
class VanillaBaseRecord:
    """Parsed record from a legacy ``BASE.DAT`` file."""

    base_index: int
    name: str
    facilities_grid: list[list[int]]
    completion_days_grid: list[list[int]]
    engineers: int
    scientists: int


def parse_soldier_dat_bytes(data: bytes) -> list[VanillaSoldierRecord]:
    """Parse active soldiers from a 17,000-byte ``SOLDIER.DAT`` binary file."""
    if len(data) % SOLDIER_DAT_RECORD_SIZE != 0:
        raise ValueError(
            f"SOLDIER.DAT size ({len(data)}) is not a multiple of "
            f"{SOLDIER_DAT_RECORD_SIZE}"
        )

    soldiers: list[VanillaSoldierRecord] = []
    record_count = len(data) // SOLDIER_DAT_RECORD_SIZE

    for idx in range(record_count):
        rec = data[idx * SOLDIER_DAT_RECORD_SIZE : (idx + 1) * SOLDIER_DAT_RECORD_SIZE]
        (rank, base_idx, craft_idx, _prev_craft, missions, kills, recovery, _value) = (
            struct.unpack_from("<HHHHHHHH", rec, 0)
        )
        if rank == 0xFFFF:
            continue

        raw_name = rec[16:41].split(b"\x00", 1)[0]
        name = raw_name.decode("ascii", errors="replace").strip()
        if not name:
            continue

        init_tu, init_hp, init_sta, init_rea, init_str, init_fir, init_thr, init_mel = (
            rec[42:50]
        )
        psi_str = rec[50]
        psi_skill = rec[51]
        init_bravery = 110 - (10 * rec[52])

        (
            imp_tu,
            imp_hp,
            imp_sta,
            imp_rea,
            imp_str,
            imp_fir,
            imp_thr,
            imp_mel,
            imp_brv,
        ) = rec[53:62]

        initial_stats = {
            "tu": init_tu,
            "stamina": init_sta,
            "health": init_hp,
            "bravery": init_bravery,
            "reactions": init_rea,
            "firing": init_fir,
            "throwing": init_thr,
            "strength": init_str,
            "melee": init_mel,
            "psiStrength": psi_str,
            "psiSkill": 0,
        }
        current_stats = {
            "tu": init_tu + imp_tu,
            "stamina": init_sta + imp_sta,
            "health": init_hp + imp_hp,
            "bravery": init_bravery + (10 * imp_brv),
            "reactions": init_rea + imp_rea,
            "firing": init_fir + imp_fir,
            "throwing": init_thr + imp_thr,
            "strength": init_str + imp_str,
            "melee": init_mel + imp_mel,
            "psiStrength": psi_str,
            "psiSkill": psi_skill,
        }

        soldiers.append(
            VanillaSoldierRecord(
                slot_index=idx,
                name=name,
                rank=rank,
                base_index=base_idx,
                craft_index=craft_idx,
                missions=missions,
                kills=kills,
                wound_recovery_days=recovery,
                initial_stats=initial_stats,
                current_stats=current_stats,
                armor=rec[62],
                gender=rec[66],
                appearance=rec[67],
            )
        )

    return soldiers


def parse_base_dat_bytes(data: bytes, is_tftd: bool = False) -> list[VanillaBaseRecord]:
    """Parse active bases from a ``BASE.DAT`` binary file.

    Records whose "disabled" flag is set, or whose name is empty, are skipped.
    In both games the layout after the grid is: 36-byte days-to-completion grid,
    then 1 byte engineers/technicians, then 1 byte scientists.
    """
    if is_tftd:
        rec_size = TFTD_BASE_DAT_RECORD_SIZE
        grid_offset = TFTD_BASE_GRID_OFFSET
        disabled_offset = TFTD_BASE_DISABLED_OFFSET
    else:
        rec_size = UFO_BASE_DAT_RECORD_SIZE
        grid_offset = UFO_BASE_GRID_OFFSET
        disabled_offset = UFO_BASE_DISABLED_OFFSET
    if len(data) % rec_size != 0:
        raise ValueError(
            f"BASE.DAT size ({len(data)}) is not a multiple of record size {rec_size}"
        )

    days_offset = grid_offset + 36
    eng_offset = days_offset + 36
    sci_offset = eng_offset + 1

    bases: list[VanillaBaseRecord] = []
    for idx in range(len(data) // rec_size):
        rec = data[idx * rec_size : (idx + 1) * rec_size]
        if rec[disabled_offset] != 0:
            continue
        raw_name = rec[0:16].split(b"\x00", 1)[0]
        name = raw_name.decode("ascii", errors="replace").strip()
        if not name:
            continue

        flat_facilities = list(rec[grid_offset : grid_offset + 36])
        flat_days = list(rec[days_offset : days_offset + 36])
        facilities_grid = [flat_facilities[r * 6 : (r + 1) * 6] for r in range(6)]
        completion_days_grid = [flat_days[r * 6 : (r + 1) * 6] for r in range(6)]

        bases.append(
            VanillaBaseRecord(
                base_index=idx,
                name=name,
                facilities_grid=facilities_grid,
                completion_days_grid=completion_days_grid,
                engineers=rec[eng_offset],
                scientists=rec[sci_offset],
            )
        )

    return bases


class VanillaAssetExtractor:
    """Extracts and caches vanilla X-COM binary sprites for ``ResourceManager``.

    Designed to plug into ``src/resource_manager.py`` in dealien/XCOM-Save-Reader:
    when a vanilla item, facility, or rank lacks an ``extraSprites`` PNG file,
    ``VanillaAssetExtractor`` decodes the requested frame from the user's base
    game installation and caches the resulting PNG under ``cache_dir`` with
    ``0o700`` permissions.
    """

    def __init__(self, game_dir: str | Path, cache_dir: str | Path) -> None:
        self.game_dir = Path(game_dir)
        self.cache_dir = Path(cache_dir)
        self._ensure_secure_cache_dir()
        self._palettes: list[list[RGBA]] | None = None
        self._archive_cache: dict[tuple[str, int], list[Image.Image]] = {}

    def _ensure_secure_cache_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.cache_dir, 0o700)
        except OSError:
            logger.debug("Could not chmod cache directory %s", self.cache_dir)

    def _resolve_case_insensitive(self, relative_path: str) -> Path | None:
        """Find a file in ``game_dir`` regardless of DOS upper/lowercase naming."""
        current = self.game_dir
        for part in Path(relative_path).parts:
            if not current.is_dir():
                return None
            match = next(
                (
                    child
                    for child in current.iterdir()
                    if child.name.lower() == part.lower()
                ),
                None,
            )
            if match is None:
                return None
            current = match
        return current if current.is_file() else None

    def get_palette(self, palette_index: int = PALETTE_BASESCAPE) -> list[RGBA]:
        """Return the requested 256-color RGBA palette from ``GEODATA/PALETTES.DAT``."""
        if self._palettes is None:
            pal_path = self._resolve_case_insensitive("GEODATA/PALETTES.DAT")
            if pal_path is None:
                raise FileNotFoundError(
                    f"Could not find GEODATA/PALETTES.DAT in {self.game_dir}"
                )
            self._palettes = load_palettes_dat(pal_path)

        if not (0 <= palette_index < len(self._palettes)):
            raise IndexError(
                f"Palette index {palette_index} out of range "
                f"(loaded {len(self._palettes)})"
            )
        return self._palettes[palette_index]

    def _load_archive(
        self,
        pck_rel_path: str,
        tab_rel_path: str | None,
        palette_index: int,
        width: int = DEFAULT_PCK_WIDTH,
        height: int = DEFAULT_PCK_HEIGHT,
        offset_size: int = 2,
    ) -> list[Image.Image]:
        cache_key = (pck_rel_path.upper(), palette_index)
        if cache_key not in self._archive_cache:
            pck_path = self._resolve_case_insensitive(pck_rel_path)
            if pck_path is None:
                raise FileNotFoundError(f"Missing PCK archive: {pck_rel_path}")
            tab_bytes: bytes | None = None
            if tab_rel_path is not None:
                tab_path = self._resolve_case_insensitive(tab_rel_path)
                if tab_path is None:
                    raise FileNotFoundError(f"Missing TAB index: {tab_rel_path}")
                tab_bytes = tab_path.read_bytes()

            palette = self.get_palette(palette_index)
            self._archive_cache[cache_key] = decode_pck_archive(
                pck_data=pck_path.read_bytes(),
                tab_data=tab_bytes,
                palette=palette,
                width=width,
                height=height,
                offset_size=offset_size,
            )
        return self._archive_cache[cache_key]

    def get_cached_sprite_path(
        self,
        archive_name: str,
        sprite_index: int,
        palette_index: int,
    ) -> Path:
        """Return the deterministic cached PNG path for a decoded vanilla sprite."""
        safe_name = archive_name.replace("/", "_").replace("\\", "_").replace(".", "_")
        return self.cache_dir / f"{safe_name}_pal{palette_index}_{sprite_index:04d}.png"

    def get_basebit_sprite(self, sprite_index: int) -> Image.Image:
        """Extract a 32x40 facility/craft/rank sprite from ``BASEBITS.PCK`` (#26)."""
        cached_path = self.get_cached_sprite_path(
            "GEOGRAPH/BASEBITS.PCK", sprite_index, PALETTE_BASESCAPE
        )
        if cached_path.is_file():
            return Image.open(cached_path).convert("RGBA")

        frames = self._load_archive(
            pck_rel_path="GEOGRAPH/BASEBITS.PCK",
            tab_rel_path="GEOGRAPH/BASEBITS.TAB",
            palette_index=PALETTE_BASESCAPE,
            width=DEFAULT_PCK_WIDTH,
            height=DEFAULT_PCK_HEIGHT,
        )
        if not (0 <= sprite_index < len(frames)):
            raise IndexError(
                f"BASEBITS.PCK sprite index {sprite_index} out of range "
                f"(0..{len(frames) - 1})"
            )
        img = frames[sprite_index]
        img.save(cached_path, format="PNG")
        return img

    def get_bigob_sprite(self, sprite_index: int) -> Image.Image:
        """Extract a 32x48 inventory item sprite from ``UNITS/BIGOBS.PCK`` (#25)."""
        cached_path = self.get_cached_sprite_path(
            "UNITS/BIGOBS.PCK", sprite_index, PALETTE_BATTLESCAPE
        )
        if cached_path.is_file():
            return Image.open(cached_path).convert("RGBA")

        frames = self._load_archive(
            pck_rel_path="UNITS/BIGOBS.PCK",
            tab_rel_path="UNITS/BIGOBS.TAB",
            palette_index=PALETTE_BATTLESCAPE,
            width=DEFAULT_PCK_WIDTH,
            height=BIGOBS_PCK_HEIGHT,
        )
        if not (0 <= sprite_index < len(frames)):
            raise IndexError(
                f"BIGOBS.PCK sprite index {sprite_index} out of range "
                f"(0..{len(frames) - 1})"
            )
        img = frames[sprite_index]
        img.save(cached_path, format="PNG")
        return img

    def get_smoke_sprite(self, sprite_index: int) -> Image.Image:
        """Extract a 32x40 smoke/rank sprite from ``UFOGRAPH/SMOKE.PCK``."""
        cached_path = self.get_cached_sprite_path(
            "UFOGRAPH/SMOKE.PCK", sprite_index, PALETTE_BATTLESCAPE
        )
        if cached_path.is_file():
            return Image.open(cached_path).convert("RGBA")

        frames = self._load_archive(
            pck_rel_path="UFOGRAPH/SMOKE.PCK",
            tab_rel_path="UFOGRAPH/SMOKE.TAB",
            palette_index=PALETTE_BATTLESCAPE,
            width=DEFAULT_PCK_WIDTH,
            height=DEFAULT_PCK_HEIGHT,
        )
        if not (0 <= sprite_index < len(frames)):
            raise IndexError(
                f"SMOKE.PCK sprite index {sprite_index} out of range "
                f"(0..{len(frames) - 1})"
            )
        img = frames[sprite_index]
        img.save(cached_path, format="PNG")
        return img


def _extract_all(extractor: VanillaAssetExtractor) -> int:
    """Decode every BASEBITS, BIGOBS, and SMOKE frame into the extractor's cache dir."""
    total = 0
    for getter in (
        extractor.get_basebit_sprite,
        extractor.get_bigob_sprite,
        extractor.get_smoke_sprite,
    ):
        index = 0
        while True:
            try:
                getter(index)
            except IndexError:
                break
            index += 1
        total += index
    return total


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: decode vanilla sprites from a game install into PNGs for inspection."""
    parser = argparse.ArgumentParser(
        description=(
            "Decode vanilla X-COM BASEBITS.PCK and BIGOBS.PCK sprites to PNG files. "
            "Automated tests live in test/test_pck_decoder.py."
        )
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        required=True,
        help="Vanilla game folder containing GEODATA/, GEOGRAPH/, UNITS/ "
        "(e.g. reference/UFO).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("user/cache/sprites"),
        help="Output directory for PNG sprites (default: user/cache/sprites).",
    )
    args = parser.parse_args(argv)

    extractor = VanillaAssetExtractor(args.game_dir, args.cache_dir)
    count = _extract_all(extractor)
    print(f"Extracted {count} sprites from {args.game_dir} to {args.cache_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
