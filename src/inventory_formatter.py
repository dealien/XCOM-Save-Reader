def format_inventory_for_display(equipment_layout, translator=None):
    """
    Formats the soldier's inventory data for display.

    Args:
        equipment_layout: A list of inventory items from the soldier data.
        translator: A callable that takes a key and returns a translated string.

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
        if translator:
            slot = translator(slot)

        if slot not in inventory_by_slot:
            inventory_by_slot[slot] = []

        item_type = item["itemType"]
        if translator:
            item_type = translator(item_type)

        item_text = f"  - {item_type}"

        if "ammoItemSlots" in item and isinstance(item["ammoItemSlots"], list):
            ammo_list = item["ammoItemSlots"]
            if translator:
                ammo_list = [translator(a) for a in ammo_list]
            ammo_text = ", ".join(ammo_list)
            item_text += f" (Loaded with: {ammo_text})"
        elif "ammoItem" in item:
            ammo_item = item["ammoItem"]
            if translator:
                ammo_item = translator(ammo_item)
            item_text += f" (Loaded with: {ammo_item})"

        if "fuseTimer" in item and item["fuseTimer"] is not None:
            item_text += f" | Active[{item['fuseTimer']}]"

        inventory_by_slot[slot].append(item_text)

    return inventory_by_slot
