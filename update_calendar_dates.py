#!/usr/bin/env python3
"""
Calendar Date Update Script

This script updates all calendar files in the data/calendar directory to correspond
with the current week. It updates both filenames and date fields within the JSON content.

Usage: python update_calendar_dates.py
"""

import json
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def get_current_week_monday():
    """Get the Monday of the current week."""
    today = datetime.now()
    # Calculate days since Monday (0 = Monday, 1 = Tuesday, etc.)
    days_since_monday = today.weekday()
    # Go back to Monday
    monday = today - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_datetime_from_filename(filename):
    """Parse datetime from filename like '2025-06-04T15_00_00.0000000.json' or '2025-07-02T20_00_00.json'."""
    # Try to match format with microseconds first
    match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}\.\d+)\.json", filename)
    if match:
        # Convert underscores back to colons
        datetime_str = match.group(1).replace("_", ":")

        # Handle 7-digit microseconds by truncating to 6 digits
        if len(datetime_str.split(".")[-1]) == 7:
            parts = datetime_str.split(".")
            microseconds = parts[-1][:6]  # Take only first 6 digits
            datetime_str = ".".join(parts[:-1]) + "." + microseconds

        try:
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            return None

    # Try to match format without microseconds
    match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2})\.json", filename)
    if match:
        # Convert underscores back to colons
        datetime_str = match.group(1).replace("_", ":")

        try:
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            return None

    return None


def format_datetime_for_filename(dt):
    """Format datetime for filename like '2025-06-04T15_00_00.0000000'."""
    # Convert colons to underscores for filename compatibility
    return dt.isoformat().replace(":", "_")


def update_json_dates(data, date_offset):
    """Update all date fields in the JSON data by the given offset."""
    date_fields = ["start", "end", "startWithTimeZone", "endWithTimeZone"]

    for field in date_fields:
        if field in data and data[field]:
            try:
                # Handle 7-digit microseconds by truncating to 6 digits
                date_str = data[field].replace("Z", "+00:00")
                if len(date_str.split(".")[-1].split("+")[0]) == 7:
                    parts = date_str.split(".")
                    microseconds = parts[-1].split("+")[0][
                        :6
                    ]  # Take only first 6 digits
                    timezone_part = (
                        "+" + parts[-1].split("+")[1] if "+" in parts[-1] else ""
                    )
                    date_str = ".".join(parts[:-1]) + "." + microseconds + timezone_part

                # Parse the original date
                original_date = datetime.fromisoformat(date_str)
                # Add the offset
                new_date = original_date + date_offset
                # Format back to ISO format
                data[field] = new_date.isoformat()
            except (ValueError, TypeError) as e:
                print(
                    f"Warning: Could not parse date in field '{field}': {data[field]} - {e}"
                )

    return data


def update_calendar_files():
    """Main function to update all calendar files."""
    calendar_dir = Path("data/calendar")

    if not calendar_dir.exists():
        print(f"Error: Calendar directory {calendar_dir} does not exist.")
        return

    # Get the Monday of the current week
    current_monday = get_current_week_monday()
    print(f"Current week Monday: {current_monday}")

    # Get all JSON files in the calendar directory
    json_files = list(calendar_dir.glob("*.json"))

    if not json_files:
        print("No JSON files found in calendar directory.")
        return

    print(f"Found {len(json_files)} calendar files to update.")

    # Process each file
    for file_path in json_files:
        filename = file_path.name
        print(f"\nProcessing: {filename}")

        # Parse the original date from filename
        original_date = parse_datetime_from_filename(filename)
        if not original_date:
            print(f"  Warning: Could not parse date from filename: {filename}")
            continue

        # Calculate the offset to move to current week
        # Find the Monday of the original date's week
        original_monday = original_date - timedelta(days=original_date.weekday())
        original_monday = original_monday.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Calculate the offset
        date_offset = current_monday - original_monday

        print(f"  Original date: {original_date}")
        print(f"  Original week Monday: {original_monday}")
        print(f"  Date offset: {date_offset}")

        # Skip if no offset (already in current week)
        if date_offset.total_seconds() == 0:
            print(f"  ⚠️  File already in current week, skipping: {filename}")
            continue

        # Calculate new date
        new_date = original_date + date_offset
        print(f"  New date: {new_date}")

        # Create new filename
        new_filename = format_datetime_for_filename(new_date) + ".json"
        new_file_path = file_path.parent / new_filename

        print(f"  New filename: {new_filename}")

        # Safety check: don't overwrite existing files
        if new_file_path.exists():
            print(f"  ⚠️  Target file already exists, skipping: {new_filename}")
            continue

        # Read and update the JSON content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Update the date fields in the JSON
            updated_data = update_json_dates(data, date_offset)

            # Write the updated content to the new file
            with open(new_file_path, "w", encoding="utf-8") as f:
                json.dump(updated_data, f, indent=4, ensure_ascii=False)

            # Remove the old file only after successful creation of new file
            file_path.unlink()

            print(f"  ✓ Successfully updated and moved to: {new_filename}")

        except Exception as e:
            print(f"  ✗ Error processing file: {e}")
            # Don't delete the original file if there was an error
            continue

    print(f"\nCompleted! Updated {len(json_files)} calendar files to current week.")


if __name__ == "__main__":
    update_calendar_files()
