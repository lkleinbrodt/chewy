from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from backend.extensions import create_logger, db
from backend.models import RecurringEvent, Task
from backend.src.utils import parse_iso_datetime

logger = create_logger(__name__, level="DEBUG")

recurring_bp = Blueprint("recurring", __name__, url_prefix="/api/recurring-events")


@recurring_bp.route("", methods=["GET"])
def get_recurring_events():
    """Get all recurring events"""
    recurring_events = RecurringEvent.query.all()

    result = [event.to_dict() for event in recurring_events]

    return jsonify(result)


@recurring_bp.route("/<recurring_event_id>", methods=["GET"])
def get_recurring_event(recurring_event_id):
    """Get details of a specific recurring event"""
    event = RecurringEvent.query.get_or_404(recurring_event_id)

    return jsonify(event.to_dict())


@recurring_bp.route("", methods=["POST"])
def create_recurring_event():
    """Create a new recurring event"""
    data = request.json

    if not data or not data.get("content") or not data.get("duration"):
        return jsonify({"error": "Missing required fields"}), 400

    # Make a copy of the data and remove any read-only properties
    event_data = data.copy()
    read_only_props = ["created_at", "updated_at", "tasks"]
    for prop in read_only_props:
        if prop in event_data:
            event_data.pop(prop)

    # Handle the frontend using 'recurrence_days' instead of 'recurrence'
    if "recurrence_days" in event_data and "recurrence" not in event_data:
        event_data["recurrence"] = event_data.pop("recurrence_days")

    time_window_start = None
    if event_data.get("time_window_start"):
        time_window_start = datetime.strptime(
            event_data["time_window_start"], "%H:%M"
        ).time()

    time_window_end = None
    if event_data.get("time_window_end"):
        time_window_end = datetime.strptime(
            event_data["time_window_end"], "%H:%M"
        ).time()

    recurring_event = RecurringEvent(
        content=event_data["content"],
        duration=event_data["duration"],
        recurrence=event_data.get("recurrence", []),
        time_window_start=time_window_start,
        time_window_end=time_window_end,
    )

    db.session.add(recurring_event)
    db.session.commit()

    # Generate initial tasks for the next 7 days
    start_date = datetime.utcnow()
    end_date = datetime.utcnow() + timedelta(days=7)
    recurring_event.create_tasks(start_date, end_date)

    return (
        jsonify(
            {
                "id": recurring_event.id,
                "content": recurring_event.content,
                "message": "Recurring event created successfully",
            }
        ),
        201,
    )


@recurring_bp.route("/<recurring_event_id>", methods=["PUT"])
def update_recurring_event(recurring_event_id):
    """Update a recurring event"""
    event = RecurringEvent.query.get_or_404(recurring_event_id)
    data = request.json

    # Remove any read-only properties
    read_only_props = ["created_at", "updated_at", "tasks"]
    for prop in read_only_props:
        if prop in data:
            data.pop(prop)

    # Handle the frontend using 'recurrence_days' instead of 'recurrence'
    if "recurrence_days" in data:
        data["recurrence"] = data.pop("recurrence_days")

    if "content" in data:
        event.content = data["content"]

    if "duration" in data:
        event.duration = data["duration"]

    if "recurrence" in data:
        event.recurrence = data["recurrence"]

    if "time_window_start" in data:
        event.time_window_start = (
            datetime.strptime(data["time_window_start"], "%H:%M").time()
            if data["time_window_start"]
            else None
        )

    if "time_window_end" in data:
        event.time_window_end = (
            datetime.strptime(data["time_window_end"], "%H:%M").time()
            if data["time_window_end"]
            else None
        )

    db.session.commit()

    return jsonify({"message": "Recurring event updated successfully"})


@recurring_bp.route("/<recurring_event_id>", methods=["DELETE"])
def delete_recurring_event(recurring_event_id):
    """Delete a recurring event and all its associated tasks"""
    event = RecurringEvent.query.get_or_404(recurring_event_id)

    # Delete all tasks associated with this recurring event
    Task.query.filter_by(recurring_event_id=event.id).delete()

    db.session.delete(event)
    db.session.commit()

    return jsonify(
        {"message": "Recurring event and associated tasks deleted successfully"}
    )


@recurring_bp.route("/<recurring_event_id>/reset-tasks", methods=["POST"])
def reset_recurring_event_tasks(recurring_event_id):
    """Reset tasks for a recurring event (delete and recreate all tasks)"""
    event = RecurringEvent.query.get_or_404(recurring_event_id)
    data = request.json

    start_date = parse_iso_datetime(data.get("start_date"))
    end_date = parse_iso_datetime(data.get("end_date"))

    if not start_date or not end_date:
        return jsonify({"error": "Invalid date range"}), 400

    event.reset_tasks(start_date, end_date)

    return jsonify({"message": "Tasks have been reset for this recurring event"})
