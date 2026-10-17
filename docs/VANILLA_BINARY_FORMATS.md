# Vanilla X-COM Binary File Formats

> Research notes and proposed approach for loading vanilla (non-YAML) game data.
> Related issues: [#25](https://github.com/dealien/XCOM-Save-Reader/issues/25), [#26](https://github.com/dealien/XCOM-Save-Reader/issues/26), [#24](https://github.com/dealien/XCOM-Save-Reader/issues/24), [#2](https://github.com/dealien/XCOM-Save-Reader/issues/2).
> Back to [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md).

## Contents

1. [The Problem](#1-the-problem)
2. [Available Resources](#2-available-resources)
3. [Graphics and Palette Formats](#3-graphics-and-palette-formats)
4. [Fixed-Length Record DAT Files](#4-fixed-length-record-dat-files)
5. [Proposed Solutions](#5-proposed-solutions)

---

## 1. The Problem

- `src/data_manager.py` only scans `standard/` and `user/mods/` for YAML rulesets (`.rul`, `.yaml`, `.yml`).
- `src/resource_manager.py` only finds sprites through mod `extraSprites` entries, loaded with Pillow (`Image.open()`).

**Modded vs. vanilla assets:** Mods ship `.png` sprite sheets and list them under `extraSprites`. The original 1994 MicroProse art is copyrighted, so OpenXcom does not ship PNG versions of it for `xcom1` (UFO) or `xcom2` (TFTD). Instead, vanilla rulesets use integer sprite indices (`spriteShape`, `spriteFacility`, `bigSprite`, `floorSprite`, `handSprite`; see the [Ruleset Reference](https://www.ufopaedia.org/Ruleset_Reference_Nightly_(OpenXcom))). These indices point into binary archives (`BASEBITS.PCK`, `BIGOBS.PCK`, `SMOKE.PCK`, …) in the user's game install.

**Binary `.DAT` files:** Static data (`GEODATA/OBDATA.DAT`, `PALETTES.DAT`, `ENGLISH.DAT`) and original DOS/Steam saves (`SOLDIER.DAT`, `BASE.DAT`, `LOC.DAT`, `UNITREF.DAT`) are fixed-length binary records, not YAML.

---

## 2. Available Resources

Both the binary specs and YAML versions of vanilla rulesets are publicly available.

1. **Binary specifications (UFOPaedia):** [Game Files](https://www.ufopaedia.org/Game_Files), [Category:Game Files](https://www.ufopaedia.org/Category:Game_Files), [Image Formats](https://www.ufopaedia.org/Image_Formats). These are documented down to the byte offset.
2. **Vanilla rulesets already in YAML (OpenXcom):** All non-graphical vanilla data and `ENGLISH.DAT` strings are already converted and live in `standard/xcom1/` and `standard/xcom2/` ([Rulesets (OpenXcom)](https://www.ufopaedia.org/Rulesets_(OpenXcom)), [OpenXcom GitHub](https://github.com/OpenXcom), [XcomDataPatch](https://github.com/OpenXcom/XcomDataPatch)).
3. **Reference implementations:** The C++ [OpenXcom](https://github.com/OpenXcom) engine and the C# [kevL/OpenXCOM.Tools](https://github.com/kevL/OpenXCOM.Tools) (`PckView`, `McdView`, `MapView`).

---

## 3. Graphics and Palette Formats

Found in `GEOGRAPH/`, `UNITS/`, `GEODATA/`, `UFOGRAPH/`.

### PALETTES.DAT / BACKPALS.DAT — [spec](https://www.ufopaedia.org/PALETTES.DAT)

- **Purpose:** Color palettes for all screens. `GEODATA/PALETTES.DAT` is 3,870 bytes in UFO (5 palettes) and 2,322 bytes in TFTD (3 palettes).
- **Structure:** Each palette is 768 bytes (256 × RGB) followed by 6 padding bytes.
- **Color values:** 6-bit VGA values (`0–63`). Multiply by 4 to get 8-bit RGB.
- **Transparency:** Index `0` is transparent.
- **BACKPALS.DAT** (384 bytes): eight 16-color sub-palettes that replace colors `224–239` for UI window backgrounds.

### .PCK + .TAB — [Image Formats](https://www.ufopaedia.org/Image_Formats), [UNITS](https://www.ufopaedia.org/UNITS)

- **Purpose:** RLE-compressed sprite sheets. Sprites are `32×40`, or `32×48` for `UNITS/BIGOBS.PCK`.
- **Key files:**
  - [BASEBITS.PCK](https://www.ufopaedia.org/BASEBITS.PCK): facilities, craft, ranks
  - [BIGOBS.PCK](https://www.ufopaedia.org/BIGOBS.PCK): 57 inventory items, `0x00–0x38`
  - [HANDOB.PCK](https://www.ufopaedia.org/HANDOB.PCK)
  - [SMOKE.PCK](https://www.ufopaedia.org/SMOKE.PCK): rank insignia
  - [INTICON.PCK](https://www.ufopaedia.org/INTICON.PCK)
- **.TAB:** A list of little-endian offsets, one per sprite, giving where that sprite starts in the `.PCK`.
  - `uint16` for UFO and TFTD terrain; `uint32` for TFTD units.
  - Single-image `UFOGRAPH/BIGOBS*.PCK` files have no `.TAB`.
- **.PCK RLE decoding:**
  1. Byte 0 = number of transparent rows to skip at the top.
  2. Read the following bytes until you hit `0xFF` (end of sprite):
     - `0xFE N` → skip `N` transparent pixels.
     - Any other byte → draw one pixel using that palette index.

### .SPK — [Image Formats](https://www.ufopaedia.org/Image_Formats), [UNIBORD.PCK](https://www.ufopaedia.org/UNIBORD.PCK)

- **Purpose:** Compressed `320×200` backgrounds and inventory paper dolls (`MAN_*.SPK`, `UNIBORD.PCK`).
- **Decoding:** The file is a stream of `uint16` little-endian values:
  - `0xFFFF N` → skip `N × 2` transparent pixels.
  - `0xFFFE N` → read and draw the next `N × 2` palette-index bytes.
  - `0xFFFD` → end of file.

### .BDY (TFTD) — [Image Formats](https://www.ufopaedia.org/Image_Formats)

- **Purpose:** Compressed `320×200` backgrounds and paper dolls (`MAN_*.BDY`, `UP*.BDY`).
- **Decoding:** Row-by-row RLE. Read a byte `a`:
  - `a >= 129` → repeat the next byte `257 − a` times.
  - `a < 129` → copy the next `a + 1` bytes as-is.

### .SCR and image .DAT — [Image Formats](https://www.ufopaedia.org/Image_Formats)

- **Purpose:** Uncompressed `320×200` backgrounds (`BACK01.SCR`–`BACK17.SCR`) and Geoscape textures (`TEXTURE.DAT`).
- **Structure:** A flat array of 1-byte palette indices, row by row (64,000 bytes for a 320×200 screen). No header and no compression.

---

## 4. Fixed-Length Record DAT Files

Used by original saves and static game data.

### SOLDIER.DAT — [spec](https://www.ufopaedia.org/SOLDIER.DAT)

250 records × 68 bytes (17,000 bytes total).

| Offset | Field |
| --- | --- |
| `0x00–0x01` | Rank (`0–5`; `0xFFFF` = dead/empty) |
| `0x02–0x03` | Base index into `LOC.DAT` (`0xFF` = in transfer) |
| `0x04–0x05` | Craft index |
| `0x08–0x09` | Missions (`int16`) |
| `0x0A–0x0B` | Kills (`int16`) |
| `0x0C–0x0D` | Wound recovery days |
| `0x10–0x28` | Name (25-byte null-terminated ASCII) |
| `0x2A–0x34` | Initial stats. Initial Bravery = `110 − 10 × byte[0x34]` |
| `0x35–0x3D` | Stat improvements, added to the initial stats. Bravery improvement = `10 × byte[0x3D]` |
| `0x3E` | Armor (`0–3`) |
| `0x42` | Gender (`0` = M, `1` = F) |
| `0x43` | Appearance (`0–3`) |

### BASE.DAT — [TFTD spec](https://www.ufopaedia.org/BASE.DAT_(TFTD)), [Base Facilities (EU)](https://www.ufopaedia.org/Base_Facilities_(EU))

Up to 8 records × 292 bytes (UFO) or 296 bytes (TFTD).

| Offset | Field |
| --- | --- |
| `0x00–0x0F` | Base name (16-byte null-terminated) |
| `0x10–0xD3` | Item store counts (`int16` LE array) |
| `0xD4–0xD8` | Radar/sonar detection values |
| `0xDA–0xFD` | 6×6 facility type grid (`0x00` = Access Lift/Air Lock, `0xFF` = empty) |
| `0xFE–0x121` | 6×6 days-until-complete grid (`0x00` = done, `0xFF` = empty) |
| `0x122` | Engineers/Technicians (`uint8`) |
| `0x123` | Scientists (`uint8`) |

### LOC.DAT — [spec](https://www.ufopaedia.org/LOC.DAT)

50 records × 20 bytes (1,000 bytes total).

| Offset | Field |
| --- | --- |
| `0x00` | Object type (`0x01` UFO, `0x02` X-COM craft, `0x03` X-COM base, `0x04` alien base) |
| `0x01` | Index into `BASE.DAT` / `CRAFT.DAT` |
| `0x02–0x05` | Longitude, latitude (`int16`) |
| `0x0A–0x0B` | Object number suffix |

### UNITREF.DAT — [spec](https://www.ufopaedia.org/UNITREF.DAT)

80 records × 124 bytes (UFO) or 132 bytes (TFTD). Holds battlescape unit state:

- Byte `0x28` links each unit to its `SOLDIER.DAT` entry.
- Tracks health, stun, morale, and armor damage.
- Hand items at `0x35–0x36` (indices into `OBDATA.DAT`).
- Experience counters at `0x50–0x55`.

---

## 5. Proposed Solutions

### 5.1 Pure-Python sprite and palette decoder — *recommended (fixes #25, #26)*

Add `src/pck_decoder.py`, using `struct` and Pillow to decode `PALETTES.DAT`, `.TAB`/`.PCK`, `.SPK`, and `.BDY` straight from the user's game directory.

- **Fallback in `ResourceManager`:** if no mod `extraSprites` PNG exists, take the sprite index from the ruleset and decode it from the vanilla archive:
  - Facilities (`spriteShape`, `spriteFacility`): `GEOGRAPH/BASEBITS.PCK`, Basescape palette #2 (#26)
  - Inventory items (`bigSprite`): `UNITS/BIGOBS.PCK`, Tactical palette #5
  - Rank icons: `UFOGRAPH/SMOKE.PCK` or `BASEBITS.PCK`
- **Caching:** save decoded sprites as PNGs under `user/cache/sprites/` with `0o700` permissions. Decoding then only happens once per install.
- **Prototype:** A reference implementation (`pck_decoder.py`) exists in the project's [Google Drive folder](https://drive.google.com/drive/folders/1rLGKLO6RnYuF7Po5l-w-gQBLiEWKrihQ) ([file](https://drive.google.com/file/d/1q_MaR9AmuWVCKvuNbAQ0dPlqJI6eI62t/view?usp=drivesdk)). It provides:
  - `parse_palettes_bytes`
  - `decode_pck_archive`, `decode_spk_bytes`, `decode_bdy_bytes`, `decode_scr_bytes`
  - `parse_soldier_dat_bytes`, `parse_base_dat_bytes`
  - `VanillaAssetExtractor`, a class that can be dropped into the existing code

### 5.2 Use OpenXcom's `standard/xcom1` and `standard/xcom2` YAML for non-graphical data

Don't write parsers for `OBDATA.DAT` or `ENGLISH.DAT`. OpenXcom already ships them as YAML (`Ruleset/*.rul`, `Language/en-US.yml`). Make sure `GameDataManager` and `TranslationManager` load these folders from the OpenXcom path in `user/config.json`. That gives you vanilla item and facility data plus readable names, which unblocks #24 and #2.

### 5.3 Optional: legacy binary save adapter

Add `src/vanilla_save_reader.py`, using `struct.unpack` to read original DOS/Steam save folders (`GAME_1`–`GAME_10`): `SOLDIER.DAT`, `BASE.DAT`, `LOC.DAT`, `PROJECT.DAT`. It would build the existing `Soldier` and `Base` objects from `src/reader.py`.

### 5.4 Alternative: offline conversion and test fixtures

Use `PckView` from [OpenXCOM.Tools](https://github.com/kevL/OpenXCOM.Tools) to inspect `.PCK` archives, or to generate small `.PCK`/`.TAB` test files for `test/test_resource_manager.py`.
