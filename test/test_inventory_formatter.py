import os
import sys

# Add src directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from inventory_formatter import format_inventory_for_display


def test_format_inventory_for_display_full():
    """Test the inventory formatter with a full and varied inventory."""
    equipment_layout = [
        {
            "itemType": "STR_NITRO_EXPRESS",
            "slot": "STR_RIGHT_HAND",
            "ammoItemSlots": ["STR_NITRO_EXPRESS_CLIP"],
        },
        {"itemType": "STR_NITRO_EXPRESS_CLIP", "slot": "STR_BELT"},
        {"itemType": "STR_SMOKE_GRENADE", "slot": "STR_BELT", "fuseTimer": 5},
        {
            "itemType": "STR_PLASMA_RIFLE",
            "slot": "STR_LEFT_HAND",
            "ammoItem": "STR_PLASMA_RIFLE_CLIP",
        },
        {"itemType": "STR_GRENADE", "slot": "STR_BELT", "fuseTimer": 0},
    ]

    expected_output = {
        "STR_RIGHT_HAND": [
            "  - STR_NITRO_EXPRESS (Loaded with: STR_NITRO_EXPRESS_CLIP)"
        ],
        "STR_BELT": [
            "  - STR_NITRO_EXPRESS_CLIP",
            "  - STR_SMOKE_GRENADE | Active[5]",
            "  - STR_GRENADE | Active[0]",
        ],
        "STR_LEFT_HAND": ["  - STR_PLASMA_RIFLE (Loaded with: STR_PLASMA_RIFLE_CLIP)"],
    }

    assert format_inventory_for_display(equipment_layout) == expected_output


def test_format_inventory_for_display_empty():
    """Test the inventory formatter with an empty equipment layout."""
    assert format_inventory_for_display([]) == {}


def test_format_inventory_for_display_none():
    """Test the inventory formatter with a None equipment layout."""
    assert format_inventory_for_display(None) == {}


def test_format_inventory_fuse_timer_zero():
    """Test that fuseTimer: 0 is correctly formatted."""
    equipment_layout = [{"itemType": "STR_GRENADE", "slot": "STR_BELT", "fuseTimer": 0}]
    expected_output = {"STR_BELT": ["  - STR_GRENADE | Active[0]"]}
    assert format_inventory_for_display(equipment_layout) == expected_output
