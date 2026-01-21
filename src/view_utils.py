def format_service_record_summary(service_record):
    """
    Formats the service record summary string.

    Args:
        service_record: The ServiceRecord object.

    Returns:
        str: The formatted summary string.
    """
    return (
        f"Months of Service: {service_record.months_service}\n"
        f"Days Wounded: {service_record.days_wounded_total} "
        f"(Wounded {service_record.times_wounded_total} times)\n"
        f"Times Unconscious: {service_record.unconscious_total}\n"
        f"Shots Fired: {service_record.shots_fired_counter_total} | "
        f"Shots Landed: {service_record.shots_landed_counter_total}\n"
        f"Times Shot At: {service_record.shot_at_counter_total} | "
        f"Times Hit: {service_record.hit_counter_total}"
    )


def format_death_info(death_info, translator):
    """
    Formats the death information string.

    Args:
        death_info: The death info dictionary from the soldier object.
        translator: A function to translate strings.

    Returns:
        str: The formatted death info string, or empty string if no death info.
    """
    if not death_info:
        return ""

    cause = death_info.get("cause", {})
    # Translate death fields
    race = translator(cause.get("race", "Unknown"))
    rank = translator(cause.get("rank", "Unknown"))
    weapon = translator(cause.get("weapon", "Unknown"))
    ammo_key = cause.get("weaponAmmo")
    ammo = translator(ammo_key) if ammo_key else "Unknown"

    return (
        f"\n--- KIA ---\n"
        f"Date: {death_info.get('time')}\n"
        f"Killed by: {race} ({rank})\n"
        f"Weapon: {weapon} ({ammo})"
    )


def format_mission_death_detail(death_info, translator):
    """
    Formats the death details for a mission card.

    Args:
        death_info: The death info dictionary.
        translator: A function to translate strings.

    Returns:
        str: The formatted death detail string, e.g. "KIA: Weapon (Race)"
    """
    if not death_info:
        return ""

    cause = death_info.get("cause", {})
    race = translator(cause.get("race", "Unknown"))
    weapon = translator(cause.get("weapon", "Unknown"))

    return f"KIA: {weapon} ({race})"
