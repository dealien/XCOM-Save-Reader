from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageDraw

from pck_decoder import PALETTE_BATTLESCAPE, VanillaAssetExtractor, recolor_palette

logger = logging.getLogger(__name__)

VANILLA_ARCHIVE_TYPES = {
    "BASEBITS.PCK",
    "BASEBITS",
    "BIGOBS.PCK",
    "BIGOBS",
    "SMOKE.PCK",
    "SMOKE",
}

BASE_TILE_WIDTH = 32
BASE_TILE_HEIGHT = 40
BASE_TILE_SIZE = 32
BASE_GRID_SIZE = 6
BASEBIT_EMPTY_DIRT = 0
BASEBIT_CONSTRUCTION = 13
BASEBIT_CRAFT_OFFSET = 33
BASEBIT_RANK_OFFSET = 42


def _composite_tile(
    canvas: Image.Image,
    tile: Image.Image | None,
    gx: int,
    gy: int,
) -> bool:
    """Alpha-composite a 32x32 tile sprite onto the 6x6 base canvas."""
    if tile is None:
        return False
    rgba = tile.convert("RGBA")
    if rgba.size == (BASE_TILE_WIDTH, BASE_TILE_HEIGHT):
        # Vanilla BASEBITS tiles only occupy the top 32x32 of their 32x40 frame.
        rgba = rgba.crop((0, 0, BASE_TILE_SIZE, BASE_TILE_SIZE))
    elif rgba.size != (BASE_TILE_SIZE, BASE_TILE_SIZE):
        rgba = rgba.resize((BASE_TILE_SIZE, BASE_TILE_SIZE), Image.Resampling.NEAREST)
    canvas.alpha_composite(rgba, dest=(gx * BASE_TILE_SIZE, gy * BASE_TILE_SIZE))
    return True


class ResourceManager:
    def __init__(
        self,
        data_manager: Any,
        vanilla_extractor: VanillaAssetExtractor | None = None,
        cache_dir: str | Path | None = None,
    ) -> None:
        self.data_manager = data_manager
        self.image_cache: dict[str, Any] = {}
        self.cache_dir = (
            Path(cache_dir)
            if cache_dir is not None
            else Path(tempfile.gettempdir()) / "xcom-save-reader" / "sprite_cache"
        )
        self.vanilla_extractor = vanilla_extractor
        self._injected_extractor = vanilla_extractor is not None
        self._font_small_img: Image.Image | None = None
        self._font_small_checked = False

    def reset(self) -> None:
        """Clear in-memory image cache and reset auto-initialized vanilla extractor."""
        self.image_cache.clear()
        self._font_small_img = None
        self._font_small_checked = False
        if not self._injected_extractor:
            self.vanilla_extractor = None

    def clear_cache(self) -> None:
        """Reset in-memory caches and remove on-disk decoded sprite cache."""
        self.reset()
        if self.cache_dir.is_dir():
            try:
                shutil.rmtree(self.cache_dir)
            except OSError as e:
                logger.warning(
                    "Failed to remove sprite cache %s: %s", self.cache_dir, e
                )

    def _format_image(
        self,
        img: Image.Image,
        size: tuple[int, int] | None = None,
        ctk_image: bool = True,
        resample: Image.Resampling = Image.Resampling.LANCZOS,
    ) -> ctk.CTkImage | Image.Image:
        """Resize and convert a PIL Image to CTkImage or PIL copy."""
        if size and img.size != size:
            img = img.resize(size, resample)

        if ctk_image:
            final_size = size if size else img.size
            return ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=final_size,
            )
        return img.copy()

    def _get_vanilla_extractor(self) -> VanillaAssetExtractor | None:
        """Lazily initialize and return a VanillaAssetExtractor if available."""
        if self.vanilla_extractor is not None:
            return self.vanilla_extractor

        if self.data_manager is None or not getattr(
            self.data_manager, "base_path", None
        ):
            return None

        base_path = Path(self.data_manager.base_path)
        master = getattr(self.data_manager, "master", "xcom1")

        # Try master-preferred directories first, then fallbacks
        preferred = ["TFTD", "xcom2"] if master == "xcom2" else ["UFO", "xcom1"]
        fallbacks = ["UFO", "xcom1"] if master == "xcom2" else ["TFTD", "xcom2"]
        candidate_subdirs = preferred + [""] + fallbacks

        for sub in candidate_subdirs:
            candidate_dir = base_path / sub if sub else base_path
            if not candidate_dir.is_dir():
                continue

            # Check for GEODATA/PALETTES.DAT (case-insensitive)
            geodata_match = next(
                (
                    p
                    for p in candidate_dir.iterdir()
                    if p.is_dir() and p.name.lower() == "geodata"
                ),
                None,
            )
            if geodata_match is not None:
                pal_match = next(
                    (
                        p
                        for p in geodata_match.iterdir()
                        if p.is_file() and p.name.lower() == "palettes.dat"
                    ),
                    None,
                )
                if pal_match is not None:
                    try:
                        key_raw = (
                            f"{candidate_dir.resolve()}|{pal_match.stat().st_mtime}"
                        )
                        cache_subdir = (
                            self.cache_dir
                            / hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:12]
                        )
                        self.vanilla_extractor = VanillaAssetExtractor(
                            game_dir=candidate_dir, cache_dir=cache_subdir
                        )
                        logger.info(
                            "Initialized VanillaAssetExtractor with game_dir: %s",
                            candidate_dir,
                        )
                        return self.vanilla_extractor
                    except Exception as e:
                        logger.warning(
                            "Failed to initialize VanillaAssetExtractor for %s: %s",
                            candidate_dir,
                            e,
                        )

        return None

    def _get_mod_sprite(
        self,
        sprite_type: str,
        index: int = 0,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
        allow_first_fallback: bool = True,
    ) -> ctk.CTkImage | Image.Image | None:
        """Resolve and load a sprite defined in mod extraSprites."""
        extra_sprites = (
            getattr(self.data_manager, "extraSprites", {}) if self.data_manager else {}
        )
        if sprite_type not in extra_sprites:
            return None

        sprite_def = extra_sprites[sprite_type]
        files = sprite_def.get("files", {})
        if not isinstance(files, dict) or not files:
            return None

        if index in files:
            matched_key: int | str = index
        elif str(index) in files:
            matched_key = str(index)
        elif allow_first_fallback:
            matched_key = next(iter(files.keys()))
        else:
            return None

        rel_path = files[matched_key]
        file_sources = sprite_def.get("_file_sources", {})
        source_dir = (
            (
                file_sources.get(matched_key)
                or file_sources.get(str(matched_key))
                or sprite_def.get("_source_dir", "")
            )
            if isinstance(file_sources, dict)
            else sprite_def.get("_source_dir", "")
        )
        if not source_dir:
            return None

        # OXCE paths are relative to the mod/standard dir
        abs_path = os.path.join(source_dir, rel_path)

        # Prevent path traversal (e.g. "../../secrets")
        resolved = os.path.realpath(abs_path)
        root = os.path.realpath(source_dir)
        if os.path.commonpath([root, resolved]) != root:
            logger.warning(f"Blocked path traversal attempt: {rel_path}")
            return None

        if not os.path.exists(resolved):
            logger.warning(f"Sprite file missing: {resolved}")
            return None

        cache_key = f"{resolved}_{matched_key}_{size}_{ctk_image}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        try:
            with Image.open(resolved) as img:
                img.load()
                result = self._format_image(img, size=size, ctk_image=ctk_image)

            self.image_cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"Failed to load sprite {resolved}: {e}")
            return None

    def get_sprite(
        self,
        sprite_type: str,
        index: int = 0,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """
        Retrieves a sprite from extraSprites rulesets, falling back to vanilla archives.
        :param sprite_type: The `type` identifier in extraSprites or archive name.
        :param index: For sprite sheets, which index to grab. If singleImage, usually 0.
        :param ctk_image: Whether to return a CustomTkinter CTkImage or a PIL Image.
        :param size: Tuple (width, height) to resize or frame the image.
        """
        upper_type = sprite_type.upper()
        is_vanilla_archive = upper_type in VANILLA_ARCHIVE_TYPES
        mod_sprite = self._get_mod_sprite(
            sprite_type,
            index=index,
            ctk_image=ctk_image,
            size=size,
            allow_first_fallback=not is_vanilla_archive,
        )
        if mod_sprite is not None:
            return mod_sprite

        if upper_type in ("BASEBITS.PCK", "BASEBITS"):
            return self.get_basebit_sprite(index, ctk_image=ctk_image, size=size)
        if upper_type in ("BIGOBS.PCK", "BIGOBS"):
            return self.get_bigob_sprite(index, ctk_image=ctk_image, size=size)
        if upper_type in ("SMOKE.PCK", "SMOKE"):
            return self.get_smoke_sprite(index, ctk_image=ctk_image, size=size)

        return None

    def _get_archive_sprite(
        self,
        cache_prefix: str,
        archive_name: str,
        extractor_method: str,
        index: int,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve sprite from mod extraSprites or fall back to vanilla extractor."""
        cache_key = f"{cache_prefix}_{index}_{size}_{ctk_image}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        mod_sprite = self._get_mod_sprite(
            archive_name,
            index=index,
            ctk_image=ctk_image,
            size=size,
            allow_first_fallback=False,
        )
        if mod_sprite is not None:
            self.image_cache[cache_key] = mod_sprite
            return mod_sprite

        extractor = self._get_vanilla_extractor()
        if extractor is not None:
            try:
                pil_img = getattr(extractor, extractor_method)(index)
                result = self._format_image(pil_img, size=size, ctk_image=ctk_image)
                self.image_cache[cache_key] = result
                return result
            except (IndexError, FileNotFoundError) as e:
                logger.warning(
                    "Failed to load vanilla %s sprite %s: %s", cache_prefix, index, e
                )

        return None

    def get_basebit_sprite(
        self,
        index: int,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a 32x40 base facility/craft/rank sprite from BASEBITS.PCK."""
        return self._get_archive_sprite(
            "basebit",
            "BASEBITS.PCK",
            "get_basebit_sprite",
            index,
            ctk_image=ctk_image,
            size=size,
        )

    def get_bigob_sprite(
        self,
        index: int,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a 32x48 inventory item sprite from BIGOBS.PCK."""
        return self._get_archive_sprite(
            "bigob",
            "BIGOBS.PCK",
            "get_bigob_sprite",
            index,
            ctk_image=ctk_image,
            size=size,
        )

    def get_smoke_sprite(
        self,
        index: int,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a 32x40 smoke or rank sprite from SMOKE.PCK."""
        return self._get_archive_sprite(
            "smoke",
            "SMOKE.PCK",
            "get_smoke_sprite",
            index,
            ctk_image=ctk_image,
            size=size,
        )

    def _resolve_ruleset_sprite(
        self,
        entity: str | dict[str, Any],
        collection_attr: str,
        sprite_key: str,
        getter: Any,
        offset: int = 0,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Resolve an indexed sprite field from a ruleset dict or type name."""
        if isinstance(entity, dict):
            entity_def = entity
        else:
            collection = (
                getattr(self.data_manager, collection_attr, {})
                if self.data_manager
                else {}
            )
            entity_def = collection.get(entity, {})

        sprite_val = entity_def.get(sprite_key)
        if sprite_val is not None:
            try:
                sprite_index = int(sprite_val) + offset
                return getter(sprite_index, ctk_image=ctk_image, size=size)
            except ValueError, TypeError:
                logger.warning("Invalid %s value: %s", sprite_key, sprite_val)

        return None

    def get_facility_sprite(
        self,
        facility_type: str | dict[str, Any],
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a facility sprite using ruleset data, resolving spriteFacility."""
        return self._resolve_ruleset_sprite(
            facility_type,
            "facilities",
            "spriteFacility",
            self.get_basebit_sprite,
            ctk_image=ctk_image,
            size=size,
        )

    def get_item_sprite(
        self,
        item_type: str | dict[str, Any],
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve an inventory item sprite using ruleset data, resolving bigSprite."""
        return self._resolve_ruleset_sprite(
            item_type,
            "items",
            "bigSprite",
            self.get_bigob_sprite,
            ctk_image=ctk_image,
            size=size,
        )

    def get_craft_sprite(
        self,
        craft_type: str | dict[str, Any],
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a craft sprite from BASEBITS using ruleset sprite + offset 33."""
        return self._resolve_ruleset_sprite(
            craft_type,
            "crafts",
            "sprite",
            self.get_basebit_sprite,
            offset=BASEBIT_CRAFT_OFFSET,
            ctk_image=ctk_image,
            size=size,
        )

    def get_rank_sprite(
        self,
        rank_index: int,
        soldier_type: str | None = None,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a soldier rank insignia sprite from BASEBITS."""
        if (
            not isinstance(rank_index, int)
            or isinstance(rank_index, bool)
            or rank_index < 0
        ):
            return None

        soldiers = (
            getattr(self.data_manager, "soldiers", {}) if self.data_manager else {}
        )
        soldier_def = soldiers.get(soldier_type, {}) if soldier_type else {}
        rank_sprite = soldier_def.get("rankSprite", BASEBIT_RANK_OFFSET)
        try:
            if isinstance(rank_sprite, list):
                if rank_index >= len(rank_sprite):
                    return None
                sprite_index = int(rank_sprite[rank_index])
            else:
                sprite_index = int(rank_sprite) + rank_index
            return self.get_basebit_sprite(sprite_index, ctk_image=ctk_image, size=size)
        except ValueError, TypeError:
            logger.warning("Invalid rankSprite value: %s", rank_sprite)
            return None

    def render_base_layout(
        self,
        base: Any,
        scale: int = 2,
        ctk_image: bool = True,
    ) -> ctk.CTkImage | Image.Image | None:
        """Render the 6x6 base facility grid including 2x2 hangars and parked craft."""
        width = BASE_GRID_SIZE * BASE_TILE_SIZE
        height = BASE_GRID_SIZE * BASE_TILE_SIZE
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        has_any_sprite = False

        dirt = self.get_basebit_sprite(BASEBIT_EMPTY_DIRT, ctk_image=False)
        if dirt is not None:
            for gy in range(BASE_GRID_SIZE):
                for gx in range(BASE_GRID_SIZE):
                    if _composite_tile(canvas, dirt, gx, gy):
                        has_any_sprite = True

        facilities_db = (
            getattr(self.data_manager, "facilities", {}) if self.data_manager else {}
        )
        hangars: list[tuple[int, int, int]] = []

        for fac in getattr(base, "facilities", []) or []:
            fx = getattr(fac, "x", None)
            fy = getattr(fac, "y", None)
            if (
                not isinstance(fx, int)
                or isinstance(fx, bool)
                or not isinstance(fy, int)
                or isinstance(fy, bool)
                or not (0 <= fx < BASE_GRID_SIZE and 0 <= fy < BASE_GRID_SIZE)
            ):
                continue

            fac_type = getattr(fac, "type", None)
            fac_def = facilities_db.get(fac_type, {})
            try:
                fac_size = max(1, int(fac_def.get("size", 1)))
            except ValueError, TypeError:
                fac_size = 1

            build_time = getattr(fac, "build_time", 0) or 0
            is_hangar = (fac_def.get("crafts", 0) or 0) > 0 or fac_type == "STR_HANGAR"
            if build_time == 0 and is_hangar:
                hangars.append((fx, fy, fac_size))

            for dy in range(fac_size):
                for dx in range(fac_size):
                    gx, gy = fx + dx, fy + dy
                    if not (0 <= gx < BASE_GRID_SIZE and 0 <= gy < BASE_GRID_SIZE):
                        continue
                    tile_offset = dy * fac_size + dx

                    if build_time > 0:
                        tile = self.get_basebit_sprite(
                            BASEBIT_CONSTRUCTION + tile_offset, ctk_image=False
                        )
                        if _composite_tile(canvas, tile, gx, gy):
                            has_any_sprite = True
                        continue

                    shape_idx = fac_def.get("spriteShape")
                    fac_idx = fac_def.get("spriteFacility")
                    if shape_idx is not None:
                        try:
                            tile = self.get_basebit_sprite(
                                int(shape_idx) + tile_offset, ctk_image=False
                            )
                            if _composite_tile(canvas, tile, gx, gy):
                                has_any_sprite = True
                        except ValueError, TypeError:
                            pass

                    if fac_idx is not None and fac_idx != shape_idx:
                        try:
                            tile = self.get_basebit_sprite(
                                int(fac_idx) + tile_offset, ctk_image=False
                            )
                            if _composite_tile(canvas, tile, gx, gy):
                                has_any_sprite = True
                        except ValueError, TypeError:
                            pass

        parked_crafts = [
            c
            for c in (getattr(base, "crafts", []) or [])
            if getattr(c, "status", "STR_READY") != "STR_OUT"
        ]
        for craft, (hx, hy, fac_size) in zip(parked_crafts, hangars, strict=False):
            craft_type = getattr(craft, "type", None)
            if not craft_type:
                continue
            craft_img = self.get_craft_sprite(craft_type, ctk_image=False)
            if craft_img is None:
                continue
            craft_rgba = craft_img.convert("RGBA")
            px = (
                hx * BASE_TILE_SIZE
                + (fac_size * BASE_TILE_SIZE - craft_rgba.width) // 2
            )
            py = (
                hy * BASE_TILE_SIZE
                + (fac_size * BASE_TILE_SIZE - craft_rgba.height) // 2
            )
            px = max(0, min(width - craft_rgba.width, px))
            py = max(0, min(height - craft_rgba.height, py))
            canvas.alpha_composite(craft_rgba, dest=(px, py))
            has_any_sprite = True

        if not has_any_sprite:
            return None

        if scale > 1:
            canvas = canvas.resize(
                (width * scale, height * scale), Image.Resampling.NEAREST
            )

        if ctk_image:
            return ctk.CTkImage(light_image=canvas, dark_image=canvas, size=canvas.size)
        return canvas

    def _recolor_paletted_sheet(
        self,
        img: Image.Image,
        face_group: int | None,
        face_color: int | None,
        hair_group: int | None,
        hair_color: int | None,
    ) -> Image.Image:
        """Apply face/hair 16-color ramp swaps to a paletted sprite sheet PNG."""
        if img.mode == "P" and (face_group is not None or hair_group is not None):
            img = img.copy()
            raw_pal = list(img.getpalette() or [])
            if len(raw_pal) < 768:
                raw_pal.extend([0] * (768 - len(raw_pal)))
            new_pal = list(raw_pal)
            for group, target in ((face_group, face_color), (hair_group, hair_color)):
                if (
                    isinstance(group, int)
                    and not isinstance(group, bool)
                    and isinstance(target, int)
                    and not isinstance(target, bool)
                    and group >= 0
                    and target >= 0
                ):
                    base_dst = group * 16
                    for shade in range(16):
                        dst_idx = base_dst + shade
                        src_idx = target + shade
                        if dst_idx != 0 and 0 <= dst_idx < 256 and 0 <= src_idx < 256:
                            new_pal[dst_idx * 3 : dst_idx * 3 + 3] = raw_pal[
                                src_idx * 3 : src_idx * 3 + 3
                            ]
            img.putpalette(new_pal)
        return img.convert("RGBA")

    def _compose_mod_unit_sheet(
        self,
        sprite_sheet: str,
        frame_indices: list[int],
        face_group: int | None,
        face_color: int | None,
        hair_group: int | None,
        hair_color: int | None,
    ) -> Image.Image | None:
        """Slice and composite unit frames from a mod extraSprites sheet."""
        extra_sprites = (
            getattr(self.data_manager, "extraSprites", {}) if self.data_manager else {}
        )
        if sprite_sheet not in extra_sprites:
            return None

        sprite_def = extra_sprites[sprite_sheet]
        files = sprite_def.get("files", {})
        if not isinstance(files, dict) or not files:
            return None

        key = 0 if 0 in files else ("0" if "0" in files else next(iter(files.keys())))
        rel_path = files[key]
        file_sources = sprite_def.get("_file_sources", {})
        source_dir = (
            (
                file_sources.get(key)
                or file_sources.get(str(key))
                or sprite_def.get("_source_dir", "")
            )
            if isinstance(file_sources, dict)
            else sprite_def.get("_source_dir", "")
        )
        if not source_dir:
            return None

        resolved = os.path.realpath(os.path.join(source_dir, rel_path))
        root = os.path.realpath(source_dir)
        if os.path.commonpath([root, resolved]) != root or not os.path.exists(resolved):
            return None

        try:
            sub_x = int(sprite_def.get("subX", BASE_TILE_WIDTH) or BASE_TILE_WIDTH)
            sub_y = int(sprite_def.get("subY", BASE_TILE_HEIGHT) or BASE_TILE_HEIGHT)
        except ValueError, TypeError:
            sub_x, sub_y = BASE_TILE_WIDTH, BASE_TILE_HEIGHT

        try:
            with Image.open(resolved) as raw_sheet:
                raw_sheet.load()
                sheet_rgba = self._recolor_paletted_sheet(
                    raw_sheet, face_group, face_color, hair_group, hair_color
                )
        except Exception as e:
            logger.warning("Failed to load unit sprite sheet %s: %s", resolved, e)
            return None

        cols = max(1, sheet_rgba.width // sub_x)
        rows = max(1, sheet_rgba.height // sub_y)
        total_frames = cols * rows
        if total_frames <= 0:
            return None

        selected = list(frame_indices)
        if any(idx < 0 or idx >= total_frames for idx in selected):
            selected = [3] if total_frames > 3 else [0]

        canvas = Image.new("RGBA", (sub_x, sub_y), (0, 0, 0, 0))
        for idx in selected:
            col, row = idx % cols, idx // cols
            cell = sheet_rgba.crop(
                (col * sub_x, row * sub_y, (col + 1) * sub_x, (row + 1) * sub_y)
            )
            canvas.alpha_composite(cell)
        return canvas

    def get_soldier_sprite(
        self,
        soldier: Any,
        ctk_image: bool = False,
        size: tuple[int, int] | None = (32, 40),
    ) -> ctk.CTkImage | Image.Image | None:
        """Render a soldier sprite using armor spriteSheet, gender, and look."""
        armors_db = (
            getattr(self.data_manager, "armors", {}) if self.data_manager else {}
        )
        armor_name = getattr(soldier, "armor", None) or "STR_NONE_UC"
        armor_def = armors_db.get(armor_name) or armors_db.get("STR_NONE_UC") or {}

        sprite_sheet = armor_def.get("spriteSheet", "XCOM_0.PCK")
        gender = int(getattr(soldier, "gender", 0) or 0)
        look = int(getattr(soldier, "look", 0) or 0)
        forced_torso = int(armor_def.get("forcedTorso", 0) or 0)
        drawing_routine = int(
            armor_def.get("drawingRoutine", armor_def.get("drawRoutine", 0)) or 0
        )

        color_idx = max(0, look * 2 + gender)
        face_group = armor_def.get("spriteFaceGroup")
        face_colors = armor_def.get("spriteFaceColor")
        face_color = (
            face_colors[color_idx]
            if isinstance(face_colors, list) and color_idx < len(face_colors)
            else None
        )
        hair_group = armor_def.get("spriteHairGroup")
        hair_colors = armor_def.get("spriteHairColor")
        hair_color = (
            hair_colors[color_idx]
            if isinstance(hair_colors, list) and color_idx < len(hair_colors)
            else None
        )

        cache_key = (
            f"soldier_{sprite_sheet}_{gender}_{look}_{forced_torso}_"
            f"{drawing_routine}_{face_color}_{hair_color}_{size}_{ctk_image}"
        )
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        if drawing_routine == 0:
            use_female = (forced_torso == 2) or (forced_torso == 0 and gender == 1)
            torso_frame = (267 + 3) if use_female else (32 + 3)
            frame_indices = [3, 19, torso_frame, 11]
        else:
            frame_indices = [3]

        canvas = self._compose_mod_unit_sheet(
            sprite_sheet,
            frame_indices,
            face_group,
            face_color,
            hair_group,
            hair_color,
        )

        if canvas is None:
            extractor = self._get_vanilla_extractor()
            if extractor is not None:
                try:
                    base_pal = extractor.get_palette(PALETTE_BATTLESCAPE)
                    pal = recolor_palette(
                        base_pal, face_group, face_color, source_palette=base_pal
                    )
                    pal = recolor_palette(
                        pal, hair_group, hair_color, source_palette=base_pal
                    )
                    frames = extractor.decode_unit_frames(
                        sprite_sheet, frame_indices, palette=pal
                    )
                    if any(idx not in frames for idx in frame_indices):
                        frames = extractor.decode_unit_frames(
                            sprite_sheet, [3, 0], palette=pal
                        )
                        order = [3] if 3 in frames else ([0] if 0 in frames else [])
                    else:
                        order = frame_indices

                    if order:
                        canvas = Image.new(
                            "RGBA",
                            (BASE_TILE_WIDTH, BASE_TILE_HEIGHT),
                            (0, 0, 0, 0),
                        )
                        for idx in order:
                            canvas.alpha_composite(frames[idx])
                except (FileNotFoundError, IndexError, ValueError) as e:
                    logger.warning(
                        "Failed to decode unit sprite %s: %s", sprite_sheet, e
                    )

        if canvas is None:
            return None

        result = self._format_image(
            canvas,
            size=size,
            ctk_image=ctk_image,
            resample=Image.Resampling.NEAREST,
        )
        self.image_cache[cache_key] = result
        return result

    def _get_font_small(self) -> Image.Image | None:
        """Lazily load common/Language/FontSmall.png if available."""
        if self._font_small_checked:
            return self._font_small_img

        self._font_small_checked = True
        if self.data_manager is None or not getattr(
            self.data_manager, "base_path", None
        ):
            return None

        font_path = (
            Path(self.data_manager.base_path) / "common" / "Language" / "FontSmall.png"
        )
        if font_path.is_file():
            try:
                with Image.open(font_path) as img:
                    img.load()
                    self._font_small_img = img.convert("RGBA")
            except Exception as e:
                logger.warning("Failed to load FontSmall.png: %s", e)

        return self._font_small_img

    def render_game_text(
        self,
        text: str,
        color: tuple[int, int, int] = (255, 224, 96),
        scale: int = 1,
    ) -> Image.Image:
        """Render text using OpenXcom's FontSmall.png bitmap font with drop shadow."""
        if not text:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

        font_img = self._get_font_small()
        if font_img is None:
            tmp = Image.new("RGBA", (max(16, len(text) * 8 + 4), 14), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tmp)
            draw.text((2, 2), text, fill=(0, 0, 0, 255))
            draw.text((1, 1), text, fill=(*color, 255))
            bbox = tmp.getbbox()
            out = tmp.crop(bbox) if bbox else tmp
            if scale > 1:
                out = out.resize(
                    (out.width * scale, out.height * scale), Image.Resampling.NEAREST
                )
            return out

        cell_w, cell_h = 8, 9
        cols = max(1, font_img.width // cell_w)
        glyphs: list[Image.Image | None] = []
        total_w = 0

        for ch in text:
            code = ord(ch)
            if ch == " " or not (33 <= code <= 126):
                glyphs.append(None)
                total_w += 4
                continue
            idx = code - 33
            gx = (idx % cols) * cell_w
            gy = (idx // cols) * cell_h
            raw_glyph = font_img.crop((gx, gy, gx + cell_w, gy + cell_h))
            bbox = raw_glyph.getbbox()
            gw = bbox[2] if bbox else 4
            glyphs.append(raw_glyph.crop((0, 0, gw, cell_h)))
            total_w += gw

        canvas = Image.new("RGBA", (max(1, total_w + 1), cell_h + 1), (0, 0, 0, 0))
        cx = 0
        for glyph in glyphs:
            if glyph is None:
                cx += 4
                continue
            gw, gh = glyph.size
            tinted = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
            shadow = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
            src_pixels = (
                list(glyph.get_flattened_data())
                if hasattr(glyph, "get_flattened_data")
                else list(glyph.getdata())
            )
            tinted.putdata(
                [
                    (
                        color[0] * r // 255,
                        color[1] * g // 255,
                        color[2] * b // 255,
                        a,
                    )
                    for r, g, b, a in src_pixels
                ]
            )
            shadow.putdata([(0, 0, 0, a) for _r, _g, _b, a in src_pixels])
            canvas.alpha_composite(shadow, dest=(cx + 1, 1))
            canvas.alpha_composite(tinted, dest=(cx, 0))
            cx += gw

        if scale > 1:
            canvas = canvas.resize(
                (canvas.width * scale, canvas.height * scale), Image.Resampling.NEAREST
            )
        return canvas

    def render_storage_item_tile(
        self,
        item_key: str,
        qty: int,
        scale: int = 2,
        ctk_image: bool = True,
    ) -> ctk.CTkImage | Image.Image:
        """Render a 32x48-based storage grid cell with item sprite and game-font qty."""
        w = 32 * scale
        h = 48 * scale
        tile = Image.new("RGBA", (w, h), (30, 33, 36, 255))
        draw = ImageDraw.Draw(tile)

        grid_color = (54, 60, 68, 255)
        border_color = (74, 82, 92, 255)
        cell = 16 * scale
        for x in range(cell, w, cell):
            draw.line([(x, 0), (x, h - 1)], fill=grid_color)
        for y in range(cell, h, cell):
            draw.line([(0, y), (w - 1, y)], fill=grid_color)
        draw.rectangle([(0, 0), (w - 1, h - 1)], outline=border_color)

        item_img = self.get_item_sprite(item_key, ctk_image=False)
        if item_img is not None:
            rgba = item_img.convert("RGBA")
            if scale != 1:
                rgba = rgba.resize(
                    (rgba.width * scale, rgba.height * scale), Image.Resampling.NEAREST
                )
            px = max(0, (w - rgba.width) // 2)
            py = max(0, (h - rgba.height) // 2)
            tile.alpha_composite(rgba, dest=(px, py))

        txt_img = self.render_game_text(str(qty), color=(255, 224, 96), scale=scale)
        tx = max(2, w - txt_img.width - 3)
        ty = max(2, h - txt_img.height - 2)
        tile.alpha_composite(txt_img, dest=(tx, ty))

        if ctk_image:
            return ctk.CTkImage(light_image=tile, dark_image=tile, size=tile.size)
        return tile

    @staticmethod
    def _resolve_item_grid_size(
        item_def: dict[str, Any],
        item_img: Image.Image | None,
        max_cols: int,
    ) -> tuple[int, int]:
        """Determine an item's (invWidth, invHeight) footprint in 16x16 grid cells."""
        raw_w = item_def.get("invWidth")
        raw_h = item_def.get("invHeight")
        try:
            inv_w = int(raw_w) if raw_w is not None else None
        except ValueError, TypeError:
            inv_w = None
        try:
            inv_h = int(raw_h) if raw_h is not None else None
        except ValueError, TypeError:
            inv_h = None

        if item_img is not None and (inv_w is None or inv_h is None):
            bbox = item_img.getbbox()
            if bbox is not None:
                if inv_w is None:
                    inv_w = max(1, (bbox[2] + 15) // 16)
                if inv_h is None:
                    inv_h = max(1, (bbox[3] + 15) // 16)

        return (
            max(1, min(max_cols, inv_w if inv_w is not None else 1)),
            max(1, min(6, inv_h if inv_h is not None else 1)),
        )

    @staticmethod
    def _find_grid_slot(
        occupied: list[list[bool]],
        grid_cols: int,
        inv_w: int,
        inv_h: int,
    ) -> tuple[int, int]:
        """Find the first free top-to-bottom, left-to-right 2D grid slot."""
        gy = 0
        while True:
            while len(occupied) < gy + inv_h:
                occupied.append([False] * grid_cols)
            for gx in range(grid_cols - inv_w + 1):
                if all(
                    not occupied[gy + dy][gx + dx]
                    for dy in range(inv_h)
                    for dx in range(inv_w)
                ):
                    for dy in range(inv_h):
                        for dx in range(inv_w):
                            occupied[gy + dy][gx + dx] = True
                    return gx, gy
            gy += 1

    def render_storage_grid(
        self,
        items: Sequence[tuple[str, int]],
        grid_cols: int = 16,
        scale: int = 2,
        ctk_image: bool = True,
    ) -> ctk.CTkImage | Image.Image | None:
        """Pack stored items into a single contiguous grid with game-font counts."""
        if not items:
            return None

        cell_px = 16 * scale
        items_db = getattr(self.data_manager, "items", {}) if self.data_manager else {}
        if not isinstance(items_db, dict):
            items_db = {}

        occupied: list[list[bool]] = []
        placements: list[tuple[int, int, int, int, Image.Image | None, int]] = []

        for item_key, qty in items:
            item_def = items_db.get(item_key, {})
            item_img = self.get_item_sprite(item_key, ctk_image=False)
            inv_w, inv_h = self._resolve_item_grid_size(item_def, item_img, grid_cols)
            gx, gy = self._find_grid_slot(occupied, grid_cols, inv_w, inv_h)
            placements.append((gx, gy, inv_w, inv_h, item_img, qty))

        grid_rows = max(6, len(occupied))
        canvas_w = grid_cols * cell_px
        canvas_h = grid_rows * cell_px
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (24, 27, 30, 255))
        draw = ImageDraw.Draw(canvas)

        grid_line = (44, 50, 58, 255)
        for col in range(1, grid_cols):
            x = col * cell_px
            draw.line([(x, 0), (x, canvas_h - 1)], fill=grid_line)
        for row in range(1, grid_rows):
            y = row * cell_px
            draw.line([(0, y), (canvas_w - 1, y)], fill=grid_line)
        draw.rectangle(
            [(0, 0), (canvas_w - 1, canvas_h - 1)], outline=(74, 82, 92, 255)
        )

        slot_fill = (32, 36, 42, 255)
        slot_inner = (42, 47, 54, 255)
        slot_border = (64, 72, 84, 255)

        for gx, gy, inv_w, inv_h, item_img, qty in placements:
            x0, y0 = gx * cell_px, gy * cell_px
            fw, fh = inv_w * cell_px, inv_h * cell_px
            draw.rectangle(
                [(x0, y0), (x0 + fw - 1, y0 + fh - 1)],
                fill=slot_fill,
                outline=slot_border,
            )
            for dx in range(1, inv_w):
                lx = x0 + dx * cell_px
                draw.line([(lx, y0 + 1), (lx, y0 + fh - 2)], fill=slot_inner)
            for dy in range(1, inv_h):
                ly = y0 + dy * cell_px
                draw.line([(x0 + 1, ly), (x0 + fw - 2, ly)], fill=slot_inner)

            if item_img is not None:
                rgba = item_img.convert("RGBA")
                bbox = rgba.getbbox()
                if bbox is not None:
                    slot_raw_w, slot_raw_h = inv_w * 16, inv_h * 16
                    if bbox[2] <= slot_raw_w and bbox[3] <= slot_raw_h:
                        rgba = rgba.crop(
                            (
                                0,
                                0,
                                min(rgba.width, slot_raw_w),
                                min(rgba.height, slot_raw_h),
                            )
                        )
                    else:
                        rgba = rgba.crop(bbox)
                scaled_w = rgba.width * scale
                scaled_h = rgba.height * scale
                if scaled_w > fw or scaled_h > fh:
                    ratio = min(fw / rgba.width, fh / rgba.height)
                    scaled_w = max(1, int(rgba.width * ratio))
                    scaled_h = max(1, int(rgba.height * ratio))
                if (scaled_w, scaled_h) != rgba.size:
                    rgba = rgba.resize((scaled_w, scaled_h), Image.Resampling.NEAREST)
                px = x0 + max(0, (fw - rgba.width) // 2)
                py = y0 + max(0, (fh - rgba.height) // 2)
                canvas.alpha_composite(rgba, dest=(px, py))

            count_str = str(qty)
            txt_scale = (
                max(1, scale - 1) if (inv_w == 1 and len(count_str) >= 3) else scale
            )
            txt_img = self.render_game_text(
                count_str, color=(255, 224, 96), scale=txt_scale
            )
            tx = max(x0 + 1, x0 + fw - txt_img.width - 2)
            ty = max(y0 + 1, y0 + fh - txt_img.height - 1)
            canvas.alpha_composite(txt_img, dest=(tx, ty))

        if ctk_image:
            return ctk.CTkImage(light_image=canvas, dark_image=canvas, size=canvas.size)
        return canvas
