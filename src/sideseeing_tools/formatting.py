from datetime import timedelta

import pandas as pd


def format_location_to_string(location_data):
    """Formats a location dictionary into a single string."""
    if not location_data or all(value == 'Unknown' for value in location_data.values()):
        return 'Unknown'

    parts = []

    for k in ["country", "state", "city", "street"]:
        v = location_data.get(k, "Unknown")

        if v != "Unknown":
            parts.append(v)

    return ', '.join(parts)


def format_duration(seconds):
    """Format seconds as HH:MM:SS, or N/A for missing values."""
    if pd.isna(seconds):
        return "N/A"

    try:
        sec = int(seconds)

        td = timedelta(seconds=sec)

        hours = td.days * 24 + td.seconds // 3600
        minutes = (td.seconds // 60) % 60
        seconds = td.seconds % 60

        return f"{str(hours).zfill(2)}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}"

    except Exception:
        return f"{seconds:.0f}"
