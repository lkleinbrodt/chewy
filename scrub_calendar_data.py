#!/usr/bin/env python3
"""
Calendar Data Scrubber Script

This script removes personal information from calendar files and replaces it with dummy data.
It preserves the structure and date information while removing sensitive content.

Usage: python scrub_calendar_data.py
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path


def generate_dummy_subject():
    """Generate a random meeting subject."""
    subjects = [
        "Team Sync Meeting",
        "Project Review",
        "Weekly Standup",
        "Client Discussion",
        "Strategy Session",
        "Planning Meeting",
        "Status Update",
        "Brainstorming Session",
        "Quarterly Review",
        "All Hands Meeting",
        "Department Meeting",
        "Cross-functional Sync",
        "Product Discussion",
        "Technical Review",
        "Business Meeting",
    ]
    return random.choice(subjects)


def generate_dummy_organizer():
    """Generate a dummy organizer email."""
    names = ["john.doe", "jane.smith", "mike.johnson", "sarah.wilson", "david.brown"]
    domains = ["company.com", "corp.org", "business.net", "enterprise.com"]
    name = random.choice(names)
    domain = random.choice(domains)
    return f"{name}@{domain}"


def generate_dummy_attendees():
    """Generate dummy attendee lists."""
    names = [
        "alice.jones",
        "bob.miller",
        "carol.white",
        "dan.garcia",
        "eve.davis",
        "frank.rodriguez",
        "grace.martinez",
        "henry.anderson",
        "iris.taylor",
        "jack.thomas",
        "kate.jackson",
        "leo.white",
        "maya.harris",
        "nick.clark",
        "olivia.lewis",
        "paul.robinson",
        "quinn.walker",
        "rachel.young",
    ]
    domains = ["company.com", "corp.org", "business.net"]

    # Generate 3-8 random attendees
    num_attendees = random.randint(3, 8)
    selected_names = random.sample(names, min(num_attendees, len(names)))

    attendees = []
    for name in selected_names:
        domain = random.choice(domains)
        attendees.append(f"{name}@{domain}")

    return ";".join(attendees) + ";"


def generate_dummy_location():
    """Generate a dummy location."""
    locations = [
        "Conference Room A",
        "Meeting Room 1",
        "Virtual Meeting",
        "Board Room",
        "Training Room",
        "Breakout Room",
        "Main Conference Room",
        "Executive Suite",
        "Collaboration Space",
        "Microsoft Teams Meeting",
        "Zoom Meeting",
        "Google Meet",
    ]
    return random.choice(locations)


def generate_dummy_body():
    """Generate a dummy meeting body."""
    bodies = [
        "<html><body><p>Please join us for this important meeting.</p></body></html>",
        "<html><body><p>Agenda and materials will be shared prior to the meeting.</p></body></html>",
        "<html><body><p>This is a scheduled meeting. Please prepare accordingly.</p></body></html>",
        "<html><body><p>Meeting details and objectives will be discussed.</p></body></html>",
        "<html><body><p>Please review the attached materials before the meeting.</p></body></html>",
    ]
    return random.choice(bodies)


def generate_dummy_id():
    """Generate a dummy ID that looks like the original format."""
    # Generate a random string that looks like the original ID format
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    id_length = random.randint(20, 30)
    return "".join(random.choice(chars) for _ in range(id_length))


def scrub_calendar_file(data):
    """Scrub personal information from a calendar file."""
    # Create a copy of the data to avoid modifying the original
    scrubbed_data = data.copy()

    # Replace sensitive fields with dummy data
    scrubbed_data["subject"] = generate_dummy_subject()
    scrubbed_data["organizer"] = generate_dummy_organizer()

    # Replace IDs with dummy IDs
    if "id" in scrubbed_data:
        scrubbed_data["id"] = generate_dummy_id()
    if "seriesMasterId" in scrubbed_data:
        scrubbed_data["seriesMasterId"] = generate_dummy_id()
    if "iCalUId" in scrubbed_data:
        scrubbed_data["iCalUId"] = generate_dummy_id()

    # Replace web link with dummy link
    if "webLink" in scrubbed_data:
        scrubbed_data["webLink"] = "https://example.com/meeting"

    # Replace attendees with dummy attendees
    if "requiredAttendees" in scrubbed_data:
        scrubbed_data["requiredAttendees"] = generate_dummy_attendees()
    if "optionalAttendees" in scrubbed_data:
        scrubbed_data["optionalAttendees"] = generate_dummy_attendees()
    if "resourceAttendees" in scrubbed_data:
        scrubbed_data["resourceAttendees"] = generate_dummy_attendees()

    # Replace location with dummy location
    if "location" in scrubbed_data:
        scrubbed_data["location"] = generate_dummy_location()

    # Replace body with dummy body
    if "body" in scrubbed_data:
        scrubbed_data["body"] = generate_dummy_body()

    # Ensure start and end dates are in Microsoft Outlook format (7-digit microseconds)
    if "start" in scrubbed_data and scrubbed_data["start"]:
        try:
            # Remove timezone info for parsing
            date_str = scrubbed_data["start"].replace("Z", "").split("+")[0]
            dt = datetime.fromisoformat(date_str)
            # Format with 7-digit microseconds
            scrubbed_data["start"] = dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "000"
        except Exception as e:
            print(f"Warning: Could not reformat start date: {e}")

    if "end" in scrubbed_data and scrubbed_data["end"]:
        try:
            # Remove timezone info for parsing
            date_str = scrubbed_data["end"].replace("Z", "").split("+")[0]
            dt = datetime.fromisoformat(date_str)
            # Format with 7-digit microseconds
            scrubbed_data["end"] = dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "000"
        except Exception as e:
            print(f"Warning: Could not reformat end date: {e}")

    return scrubbed_data


def scrub_calendar_files():
    """Main function to scrub all calendar files."""
    calendar_dir = Path("data/calendar")

    if not calendar_dir.exists():
        print(f"Error: Calendar directory {calendar_dir} does not exist.")
        return

    # Get all JSON files in the calendar directory
    json_files = list(calendar_dir.glob("*.json"))

    if not json_files:
        print("No JSON files found in calendar directory.")
        return

    print(f"Found {len(json_files)} calendar files to scrub.")

    # Process each file
    for file_path in json_files:
        filename = file_path.name
        print(f"Processing: {filename}")

        try:
            # Read the original file
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Scrub the data
            scrubbed_data = scrub_calendar_file(data)

            # Write the scrubbed data back to the same file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(scrubbed_data, f, indent=4, ensure_ascii=False)

            print(f"  ✓ Successfully scrubbed: {filename}")

        except Exception as e:
            print(f"  ✗ Error processing file {filename}: {e}")
            continue

    print(f"\nCompleted! Scrubbed {len(json_files)} calendar files.")


if __name__ == "__main__":
    scrub_calendar_files()
