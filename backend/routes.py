import os
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from backend.extensions import create_logger, db
from backend.models import Task, TaskDependency
from backend.settings import get_calendar_dir, set_calendar_dir
from backend.src.scheduling.scheduler import generate_schedule
from backend.src.utils import parse_iso_datetime

logger = create_logger(__name__, level="DEBUG")

base_bp = Blueprint("base", __name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
task_bp = Blueprint("task", __name__, url_prefix="/api/tasks")

schedule_bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")
settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@base_bp.route("/")
def index():
    """API root endpoint - returns API status and basic information"""
    logger.info("Root endpoint accessed")
    return (
        jsonify(
            {
                "status": "healthy",
            }
        ),
        200,
    )


# Task routes
@task_bp.route("", methods=["GET"])
def get_tasks():
    """Get all tasks with optional filtering"""
    task_type = request.args.get("type")
    is_completed = request.args.get("is_completed")

    query = Task.query

    if task_type:
        query = query.filter(Task.task_type == task_type)

    if is_completed is not None:
        is_completed = is_completed.lower() == "true"
        query = query.filter(Task.is_completed == is_completed)

    tasks = query.all()

    result = [task.to_dict() for task in tasks]

    return jsonify(result)


@task_bp.route("", methods=["POST"])
def create_task():
    """Create a new task"""
    data = request.json

    if (
        not data
        or not data.get("content")
        or not data.get("duration")
        or not data.get("task_type")
    ):
        return jsonify({"error": "Missing required fields"}), 400

    task = Task(**data)

    db.session.add(task)
    db.session.commit()

    # Handle dependencies for one-off tasks
    if data.get("dependencies"):
        for dep_id in data["dependencies"]:
            dependency = TaskDependency(task_id=task.id, dependency_id=dep_id)
            db.session.add(dependency)
        db.session.commit()

    return (
        jsonify(
            {
                "id": task.id,
                "content": task.content,
                "message": "Task created successfully",
            }
        ),
        201,
    )


@task_bp.route("/<task_id>", methods=["GET"])
def get_task(task_id):
    """Get task details"""
    task = Task.query.get_or_404(task_id)

    result = task.to_dict()
    return jsonify(result)


@task_bp.route("/<task_id>", methods=["PUT"])
def update_task(task_id):
    """Update a task"""
    task = Task.query.get_or_404(task_id)
    data = request.json

    if "content" in data:
        task.content = data["content"]
    if "duration" in data:
        task.duration = data["duration"]

    if "due_by" in data:
        task.due_by = parse_iso_datetime(data.get("due_by"))

    if "dependencies" in data:
        # Remove all existing dependencies
        TaskDependency.query.filter_by(task_id=task.id).delete()

        # Add new dependencies
        for dep_id in data["dependencies"]:
            dependency = TaskDependency(task_id=task.id, dependency_id=dep_id)
            db.session.add(dependency)

    if "time_window_start" in data:
        task.time_window_start = datetime.strptime(
            data["time_window_start"], "%H:%M"
        ).time()
    if "time_window_end" in data:
        task.time_window_end = datetime.strptime(
            data["time_window_end"], "%H:%M"
        ).time()

    if "status" in data:
        if data["status"] in ["unscheduled", "scheduled", "completed"]:
            task.status = data["status"]
        else:
            raise ValueError(f"Invalid status: {data['status']}")

    db.session.commit()

    return jsonify({"message": "Task updated successfully"})


@task_bp.route("/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a task"""
    task = Task.query.get_or_404(task_id)

    # Delete related dependencies
    TaskDependency.query.filter_by(task_id=task.id).delete()
    TaskDependency.query.filter_by(dependency_id=task.id).delete()

    db.session.delete(task)
    db.session.commit()

    return jsonify({"message": "Task deleted successfully"})


@task_bp.route("/<task_id>/complete", methods=["POST"])
def complete_task(task_id):
    """Mark task as complete"""
    task: Task = Task.query.get_or_404(task_id)
    task.complete()
    db.session.commit()

    return jsonify({"message": "Task marked as complete"})


# Calendar routes


@schedule_bp.route("/clear", methods=["DELETE"])
def clear_all_scheduled_tasks():
    """goes through all the tasks in the db and sets their status to unscheduled"""
    tasks = Task.query.all()
    for task in tasks:
        task.status = "unscheduled"
        task.start = None
        task.end = None
    db.session.commit()
    return jsonify({"message": "All tasks set to unscheduled"})


# Schedule routes
@schedule_bp.route("/schedule", methods=["POST"])
def generate_new_schedule():
    """Schedules all the tasks in the db for the given date range"""
    data = request.json or {}

    # Get date range for scheduling
    start_date = parse_iso_datetime(
        data.get("start_date", datetime.utcnow().isoformat())
    )
    # start date cant be before right now. if it is, set it to right now
    # Ensure both datetimes are timezone-naive for comparison
    now = datetime.utcnow().replace(tzinfo=None)
    if start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
    if start_date < now:
        start_date = now

    end_date = parse_iso_datetime(
        data.get("end_date", (datetime.utcnow() + timedelta(days=7)).isoformat())
    )

    if not start_date or not end_date:
        return jsonify({"error": "Invalid date range"}), 400

    try:
        scheduled_tasks, status_message = generate_schedule(start_date, end_date)

        if scheduled_tasks is None:
            return jsonify({"error": status_message}), 500

        logger.debug(f"Scheduled tasks: {scheduled_tasks}")

        # now update each task in the db with the scheduled start and end times
        for task_data in scheduled_tasks:
            task: Task = Task.query.get(task_data["task_id"])
            if not task:
                raise Exception(f"Task {task_data['task_id']} not found")
            task.start = task_data["start"]
            task.end = task_data["end"]
            task.status = "scheduled"

        db.session.commit()

        # now return those tasks
        scheduled_tasks = Task.query.filter(
            Task.start >= start_date, Task.start <= end_date
        ).all()

        result = [task.to_dict() for task in scheduled_tasks]

        return jsonify(
            {
                "message": "Schedule generated successfully (times in UTC)",
                "tasks": result,
            }
        )
    except Exception as e:
        logger.error(f"Error generating schedule: {str(e)}")
        return jsonify({"error": f"Failed to generate schedule: {str(e)}"}), 500


@settings_bp.route("/calendar-dir", methods=["GET"])
def get_calendar_directory():
    """Get the current calendar directory setting"""
    calendar_dir = get_calendar_dir()
    return jsonify(
        {
            "calendar_dir": calendar_dir,
            "is_set": calendar_dir is not None and os.path.exists(calendar_dir),
        }
    )


@settings_bp.route("/calendar-dir", methods=["POST"])
def set_calendar_directory():
    """Set the calendar directory"""
    data = request.json

    if not data or "calendar_dir" not in data:
        return jsonify({"error": "Missing calendar_dir parameter"}), 400

    calendar_dir = data["calendar_dir"]

    # Validate that the directory exists
    if not os.path.exists(calendar_dir):
        return jsonify({"error": "Directory does not exist"}), 400

    # Validate that the directory contains JSON files
    json_files = [f for f in os.listdir(calendar_dir) if f.endswith(".json")]
    if not json_files:
        return jsonify({"error": "No JSON files found in directory"}), 400

    # Set the calendar directory
    set_calendar_dir(calendar_dir)

    return jsonify(
        {
            "message": "Calendar directory set successfully",
            "calendar_dir": calendar_dir,
            "files_found": len(json_files),
        }
    )
