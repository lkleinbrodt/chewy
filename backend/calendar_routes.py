import json
import os

from flask import Blueprint, jsonify, request

from backend.extensions import create_logger, db
from backend.models import CalendarEvent
from backend.settings import get_calendar_dir
from backend.src.utils import parse_iso_datetime

logger = create_logger(__name__, level="DEBUG")
calendar_bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")


@calendar_bp.route("", methods=["GET"])
def get_calendar():
    """Get current calendar events within a date range"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"error": "Missing start_date or end_date parameters"}), 400

    try:
        start = parse_iso_datetime(start_date)
        end = parse_iso_datetime(end_date)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    events = CalendarEvent.query.filter(
        CalendarEvent.end >= start, CalendarEvent.start <= end
    ).all()

    result = []
    for event in events:
        result.append(
            {
                "id": event.id,
                "subject": event.subject,
                "start": event.start.isoformat() + "Z",
                "end": event.end.isoformat() + "Z",
                "is_chewy_managed": event.is_chewy_managed,
                "categories": event.categories,
            }
        )

    return jsonify(result)


@calendar_bp.route("/sync", methods=["POST"])
def sync_calendar():
    """Sync calendar events from JSON files"""
    calendar_dir = get_calendar_dir()

    if not calendar_dir:
        return (
            jsonify(
                {
                    "error": "CALENDAR_DIR_NOT_SET",
                    "message": "Calendar directory not configured",
                }
            ),
            400,
        )

    if not os.path.exists(calendar_dir):
        return (
            jsonify(
                {
                    "error": "CALENDAR_DIR_NOT_FOUND",
                    "message": "Calendar directory does not exist",
                }
            ),
            400,
        )

    # Track files processed and events synced
    processed_files = []
    events_synced = 0
    all_day_events_skipped = 0  # Track skipped all-day events

    # List all JSON files in the directory
    json_files = [f for f in os.listdir(calendar_dir) if f.endswith(".json")]

    if not json_files:
        return (
            jsonify(
                {
                    "error": "NO_JSON_FILES",
                    "message": "No JSON files found in calendar directory",
                }
            ),
            400,
        )

    # Get all current event IDs in database to track removed events
    current_event_ids = set(event.id for event in CalendarEvent.query.all())
    synced_event_ids = set()

    for json_file in json_files:
        file_path = os.path.join(calendar_dir, json_file)
        processed_files.append(json_file)

        try:
            with open(file_path, "r") as f:
                events_data = json.load(f)

                if not isinstance(events_data, list):
                    events_data = [events_data]

                for event_data in events_data:
                    # Check for required fields
                    if not all(
                        key in event_data for key in ["id", "subject", "start", "end"]
                    ):
                        continue

                    # Skip all-day events
                    # TODO: Improve handling of all-day events in the future - consider adding them
                    # with special treatment or as a different event type
                    if event_data.get("isAllDay", False):
                        all_day_events_skipped += 1
                        continue

                    # Parse dates with timezone conversion
                    # Prioritize using the fields with timezone information
                    raw_start_obj = event_data["start"]
                    start_str = raw_start_obj.get("dateTime", raw_start_obj.get("date"))
                    if "startWithTimeZone" in event_data:
                        start_time = parse_iso_datetime(event_data["startWithTimeZone"])
                    else:
                        start_time = parse_iso_datetime(start_str)

                    raw_end_obj = event_data["end"]
                    end_str = raw_end_obj.get("dateTime", raw_end_obj.get("date"))
                    if "endWithTimeZone" in event_data:
                        end_time = parse_iso_datetime(event_data["endWithTimeZone"])
                    else:
                        end_time = parse_iso_datetime(end_str)

                    if not start_time or not end_time:
                        continue

                    # Check if the event has "Chewy" in categories
                    categories = event_data.get("categories", [])
                    is_chewy_managed = any("chewy" in cat.lower() for cat in categories)

                    # Check if event already exists
                    event = CalendarEvent.query.get(event_data["id"])

                    if event:
                        # Update existing event
                        event.subject = event_data["subject"]
                        event.start = start_time
                        event.end = end_time
                        event.is_chewy_managed = is_chewy_managed
                        event.source_file = json_file
                        event.categories = categories
                        event.raw_data = event_data
                    else:
                        # Create new event
                        event = CalendarEvent(
                            id=event_data["id"],
                            subject=event_data["subject"],
                            start=start_time,
                            end=end_time,
                            is_chewy_managed=is_chewy_managed,
                            source_file=json_file,
                            categories=categories,
                            raw_data=event_data,
                        )
                        db.session.add(event)

                    events_synced += 1
                    synced_event_ids.add(event_data["id"])

        except Exception as e:
            logger.error(f"Error processing file {json_file}: {str(e)}")
            # Log more detailed error information
            import traceback

            logger.error(traceback.format_exc())

    # Delete events that are no longer present in the JSON files
    events_to_delete = current_event_ids - synced_event_ids
    if events_to_delete:
        CalendarEvent.query.filter(CalendarEvent.id.in_(events_to_delete)).delete(
            synchronize_session="fetch"
        )

    db.session.commit()

    return jsonify(
        {
            "message": "Calendar synced successfully",
            "files_processed": processed_files,
            "events_synced": events_synced,
            "events_deleted": len(events_to_delete),
            "all_day_events_skipped": all_day_events_skipped,
        }
    )


@calendar_bp.route("/events", methods=["GET"])
def get_all_events():
    """Get all calendar events"""
    events = CalendarEvent.query.all()

    result = []
    for event in events:
        result.append(
            {
                "id": event.id,
                "subject": event.subject,
                "start": event.start.isoformat() + "Z",
                "end": event.end.isoformat() + "Z",
                "is_chewy_managed": event.is_chewy_managed,
                "categories": event.categories,
            }
        )

    return jsonify(result)


@calendar_bp.route("/events/<event_id>", methods=["PUT"])
def update_event(event_id):
    """Update a Chewy-managed event"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Only allow updating Chewy-managed events
    if not event.is_chewy_managed:
        return jsonify({"error": "Cannot update events not managed by Chewy"}), 403

    data = request.json

    if "subject" in data:
        event.subject = data["subject"]
    if "start" in data:
        event.start = parse_iso_datetime(data["start"])
    if "end" in data:
        event.end = parse_iso_datetime(data["end"])

    db.session.commit()

    return jsonify({"message": "Event updated successfully"})


@calendar_bp.route("/events/clear", methods=["DELETE"])
def clear_all_events():
    """Clear all calendar events - for testing purposes"""
    try:
        CalendarEvent.query.delete()
        db.session.commit()
        return jsonify({"message": "All calendar events cleared successfully"})
    except Exception as e:
        logger.error(f"Error clearing calendar events: {str(e)}")
        return jsonify({"error": f"Failed to clear events: {str(e)}"}), 500
