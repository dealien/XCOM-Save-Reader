from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image

from pck_decoder import VanillaAssetExtractor

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

    def reset(self) -> None:
        """Clear in-memory image cache and reset auto-initialized vanilla extractor."""
        self.image_cache.clear()
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
    ) -> ctk.CTkImage | Image.Image:
        """Resize and convert a PIL Image to CTkImage or PIL copy."""
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)

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
