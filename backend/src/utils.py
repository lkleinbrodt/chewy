import re
from datetime import datetime

import pytz


def parse_iso_datetime(datetime_str):
    """
    Parse an ISO format datetime string into a naive UTC datetime object.
    This function will consistently handle:
    - UTC ISO strings with 'Z' suffix
    - ISO strings with explicit timezone offsets
    - Naive ISO strings (assuming they represent UTC times)
    """
    if not datetime_str:
        return None

    # Handle the specific format with 7 decimal places
    if re.match(r"\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}\.\d{7}", datetime_str):
        # Convert from filename format to ISO format
        datetime_str = datetime_str.replace("_", ":")

    # Handle the format with 7 decimal places in the fractional seconds
    if re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}", datetime_str):
        # Truncate to 6 decimal places which is the maximum Python's fromisoformat can handle
        datetime_str = datetime_str[:-1]

    # Parse the ISO string - handling both timezone-aware and naive formats
    if "Z" in datetime_str or "+" in datetime_str[10:] or "-" in datetime_str[10:]:
        # String has timezone information
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    else:
        # String is naive - assume it's UTC already
        dt = datetime.fromisoformat(datetime_str)
        # Make it timezone-aware as UTC for consistent handling
        dt = pytz.utc.localize(dt)

    # Convert to UTC and make it naive for storage
    return dt.astimezone(pytz.utc).replace(tzinfo=None)
