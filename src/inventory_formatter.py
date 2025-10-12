def format_inventory_for_display(equipment_layout):
    """
    Formats the soldier's inventory data for display.

    Args:
        equipment_layout: A list of inventory items from the soldier data.

    Returns:
        A dictionary where keys are slot names and values are lists of
        formatted item strings. Returns an empty dictionary if equipment_layout
        is None or empty.
    """
    if not equipment_layout:
        return {}

    inventory_by_slot = {}
    for item in equipment_layout:
        slot = item.get("slot", "Unslotted")
        if slot not in inventory_by_slot:
            inventory_by_slot[slot] = []

        item_text = f"  - {item['itemType']}"
        if "ammoItemSlots" in item and isinstance(item["ammoItemSlots"], list):
            ammo_text = ", ".join(item["ammoItemSlots"])
            item_text += f" (Loaded with: {ammo_text})"
        elif "ammoItem" in item:
            item_text += f" (Loaded with: {item['ammoItem']})"

        if "fuseTimer" in item and item['fuseTimer'] is not None:
            item_text += f" | Active[{item['fuseTimer']}]"

        inventory_by_slot[slot].append(item_text)

    return inventory_by_slot
