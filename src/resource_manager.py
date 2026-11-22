from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image

from pck_decoder import VanillaAssetExtractor

logger = logging.getLogger(__name__)


class ResourceManager:
    def __init__(
        self,
        data_manager: Any,
        vanilla_extractor: VanillaAssetExtractor | None = None,
        cache_dir: str | Path = Path("user/cache/sprites"),
    ) -> None:
        self.data_manager = data_manager
        self.image_cache: dict[str, Any] = {}
        self.cache_dir = Path(cache_dir)
        self.vanilla_extractor = vanilla_extractor

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
                        self.vanilla_extractor = VanillaAssetExtractor(
                            game_dir=candidate_dir, cache_dir=self.cache_dir
                        )
                        logger.info(
                            "Initialized VanillaAssetExtractor with game_dir: %s",
                            candidate_dir,
                        )
                        return self.vanilla_extractor
                    except Exception as e:
                        logger.warning(
                            "Failed to initialize VanillaAssetExtractor for %s: %e",
                            candidate_dir,
                            e,
                        )

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
        # 1. Try extraSprites definitions (modded assets)
        extra_sprites = (
            getattr(self.data_manager, "extraSprites", {}) if self.data_manager else {}
        )
        if sprite_type in extra_sprites:
            sprite_def = extra_sprites[sprite_type]
            files = sprite_def.get("files", {})

            # files is a dict mapping index -> path (e.g. {0: "Resources/UI/icon.png"})
            if index not in files:
                if files:
                    index = list(files.keys())[0]
                else:
                    return None

            rel_path = files[index]
            source_dir = sprite_def.get("_source_dir", "")

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

            cache_key = f"{resolved}_{index}_{size}_{ctk_image}"
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

        # 2. Check for vanilla archive names as fallback
        upper_type = sprite_type.upper()
        if upper_type in ("BASEBITS.PCK", "BASEBITS"):
            return self.get_basebit_sprite(index, ctk_image=ctk_image, size=size)
        if upper_type in ("BIGOBS.PCK", "BIGOBS"):
            return self.get_bigob_sprite(index, ctk_image=ctk_image, size=size)
        if upper_type in ("SMOKE.PCK", "SMOKE"):
            return self.get_smoke_sprite(index, ctk_image=ctk_image, size=size)

        return None

    def get_basebit_sprite(
        self,
        index: int,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a 32x40 base facility/craft/rank sprite from BASEBITS.PCK."""
        cache_key = f"basebit_{index}_{size}_{ctk_image}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        # Check if a mod overrode BASEBITS.PCK via extraSprites
        extra_sprites = (
            getattr(self.data_manager, "extraSprites", {}) if self.data_manager else {}
        )
        if "BASEBITS.PCK" in extra_sprites:
            sprite = self.get_sprite(
                "BASEBITS.PCK", index=index, ctk_image=ctk_image, size=size
            )
            if sprite is not None:
                self.image_cache[cache_key] = sprite
                return sprite

        # Fallback to vanilla archive decoder
        extractor = self._get_vanilla_extractor()
        if extractor is not None:
            try:
                pil_img = extractor.get_basebit_sprite(index)
                result = self._format_image(pil_img, size=size, ctk_image=ctk_image)
                self.image_cache[cache_key] = result
                return result
            except (IndexError, FileNotFoundError) as e:
                logger.warning(f"Failed to load vanilla basebit sprite {index}: {e}")

        return None

    def get_bigob_sprite(
        self,
        index: int,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a 32x48 inventory item sprite from BIGOBS.PCK."""
        cache_key = f"bigob_{index}_{size}_{ctk_image}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        # Check if a mod overrode BIGOBS.PCK via extraSprites
        extra_sprites = (
            getattr(self.data_manager, "extraSprites", {}) if self.data_manager else {}
        )
        if "BIGOBS.PCK" in extra_sprites:
            sprite = self.get_sprite(
                "BIGOBS.PCK", index=index, ctk_image=ctk_image, size=size
            )
            if sprite is not None:
                self.image_cache[cache_key] = sprite
                return sprite

        # Fallback to vanilla archive decoder
        extractor = self._get_vanilla_extractor()
        if extractor is not None:
            try:
                pil_img = extractor.get_bigob_sprite(index)
                result = self._format_image(pil_img, size=size, ctk_image=ctk_image)
                self.image_cache[cache_key] = result
                return result
            except (IndexError, FileNotFoundError) as e:
                logger.warning(f"Failed to load vanilla bigob sprite {index}: {e}")

        return None

    def get_smoke_sprite(
        self,
        index: int,
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a 32x40 smoke or rank sprite from SMOKE.PCK."""
        cache_key = f"smoke_{index}_{size}_{ctk_image}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        # Check if a mod overrode SMOKE.PCK via extraSprites
        extra_sprites = (
            getattr(self.data_manager, "extraSprites", {}) if self.data_manager else {}
        )
        if "SMOKE.PCK" in extra_sprites:
            sprite = self.get_sprite(
                "SMOKE.PCK", index=index, ctk_image=ctk_image, size=size
            )
            if sprite is not None:
                self.image_cache[cache_key] = sprite
                return sprite

        # Fallback to vanilla archive decoder
        extractor = self._get_vanilla_extractor()
        if extractor is not None:
            try:
                pil_img = extractor.get_smoke_sprite(index)
                result = self._format_image(pil_img, size=size, ctk_image=ctk_image)
                self.image_cache[cache_key] = result
                return result
            except (IndexError, FileNotFoundError) as e:
                logger.warning(f"Failed to load vanilla smoke sprite {index}: {e}")

        return None

    def get_facility_sprite(
        self,
        facility_type: str | dict[str, Any],
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve a facility sprite using ruleset data, resolving spriteFacility."""
        if isinstance(facility_type, dict):
            facility_def = facility_type
        else:
            facilities = (
                getattr(self.data_manager, "facilities", {})
                if self.data_manager
                else {}
            )
            facility_def = facilities.get(facility_type, {})

        sprite_facility = facility_def.get("spriteFacility")
        if sprite_facility is not None:
            try:
                sprite_index = int(sprite_facility)
                return self.get_basebit_sprite(
                    sprite_index, ctk_image=ctk_image, size=size
                )
            except ValueError, TypeError:
                logger.warning(f"Invalid spriteFacility value: {sprite_facility}")

        return None

    def get_item_sprite(
        self,
        item_type: str | dict[str, Any],
        ctk_image: bool = True,
        size: tuple[int, int] | None = None,
    ) -> ctk.CTkImage | Image.Image | None:
        """Retrieve an inventory item sprite using ruleset data, resolving bigSprite."""
        if isinstance(item_type, dict):
            item_def = item_type
        else:
            items = getattr(self.data_manager, "items", {}) if self.data_manager else {}
            item_def = items.get(item_type, {})

        big_sprite = item_def.get("bigSprite")
        if big_sprite is not None:
            try:
                sprite_index = int(big_sprite)
                return self.get_bigob_sprite(
                    sprite_index, ctk_image=ctk_image, size=size
                )
            except ValueError, TypeError:
                logger.warning(f"Invalid bigSprite value: {big_sprite}")

        return None
