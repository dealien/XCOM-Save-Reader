import logging
import os

import customtkinter as ctk
from PIL import Image

logger = logging.getLogger(__name__)


class ResourceManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.image_cache = {}

    def get_sprite(self, sprite_type, index=0, ctk_image=True, size=None):
        """
        Retrieves a sprite from the extraSprites ruleset definitions.
        :param sprite_type: The `type` identifier in extraSprites.
        :param index: For sprite sheets, which index to grab. If singleImage, usually 0.
        :param ctk_image: Whether to return a CustomTkinter CTkImage or a PIL Image.
        :param size: Tuple (width, height) to resize or frame the image.
        """
        if sprite_type not in self.data_manager.extraSprites:
            return None

        sprite_def = self.data_manager.extraSprites[sprite_type]
        files = sprite_def.get("files", {})

        # files is a dict mapping index -> path (e.g. {0: "Resources/UI/icon.png"})
        if index not in files:
            # Try to grab the first one if the explicit index is missing
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

        abs_path = resolved

        cache_key = f"{abs_path}_{index}_{size}_{ctk_image}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        try:
            # Open with context manager to ensure file handle is released.
            # img.load() forces pixel data into memory before closing.
            with Image.open(abs_path) as img:
                img.load()

                if size:
                    img = img.resize(size, Image.Resampling.LANCZOS)

                if ctk_image:
                    final_size = size if size else img.size
                    result = ctk.CTkImage(
                        light_image=img,
                        dark_image=img,
                        size=final_size,
                    )
                else:
                    result = img.copy()

            self.image_cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to load sprite {abs_path}: {e}")
            return None
