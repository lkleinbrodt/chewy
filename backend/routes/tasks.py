import os
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from backend.config import Config
from backend.extensions import create_logger, db
from backend.models.task import Task, TaskDependency
from backend.settings import (
    get_calendar_dir,
    get_export_dir,
    set_calendar_dir,
    set_export_dir,
)
from backend.src.scheduling.objectives import SchedulerObjectives
from backend.src.scheduling.scheduler import generate_schedule
from backend.src.scheduling.task_exporter import synchronize_task_exports
from backend.src.utils import parse_iso_datetime

logger = create_logger(__name__, level="INFO")

task_bp = Blueprint("task", __name__, url_prefix="/tasks")
schedule_bp = Blueprint("schedule", __name__, url_prefix="/schedule")
settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


# Task routes
@task_bp.route("", methods=["GET"])
def get_tasks():
    """
    Get all tasks with optional filtering

    Query parameters:
    - task_nature: 'recurring' or 'one-off' to filter by task type
    - is_completed: 'true' or 'false' to filter by completion status
    - recurring_event_id: Filter tasks by their recurring event ID
    - start_date: Filter tasks with due dates >= this date (ISO format)
    - end_date: Filter tasks with due dates <= this date (ISO format)
    """
    task_nature = request.args.get("task_nature")
    is_completed = request.args.get("is_completed")
    recurring_event_id = request.args.get("recurring_event_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = Task.query

    # Filter by task nature (recurring vs one-off)
    if task_nature:
        if task_nature == "recurring":
            # For recurring tasks, filter where recurring_event_id is not null
            query = query.filter(Task.recurring_event_id.isnot(None))
        elif task_nature == "one-off":
            # For one-off tasks, filter where recurring_event_id is null
            query = query.filter(Task.recurring_event_id.is_(None))

    # Filter by completion status
    if is_completed is not None:
        is_completed = is_completed.lower() == "true"
        if is_completed:
            query = query.filter(Task.status == "completed")
        else:
            query = query.filter(Task.status != "completed")

    # Filter by recurring event ID
    if recurring_event_id:
        query = query.filter(Task.recurring_event_id == recurring_event_id)

    # Filter by date range
    if start_date:
        try:
            start_datetime = parse_iso_datetime(start_date)
            query = query.filter(Task.due_by >= start_datetime)
        except Exception as e:
            logger.warning(f"Invalid start_date format: {e}")

    if end_date:
        try:
            end_datetime = parse_iso_datetime(end_date)
            query = query.filter(Task.due_by <= end_datetime)
        except Exception as e:
            logger.warning(f"Invalid end_date format: {e}")

    # Execute query and convert to dictionaries
    tasks = query.all()
    result = [task.to_dict() for task in tasks]

    return jsonify(result)


@task_bp.route("", methods=["POST"])
def create_task():
    """Create a new task"""
    data = request.json

    if not data or not data.get("content") or not data.get("duration"):
        return jsonify({"error": "Missing required fields"}), 400

    # Extract dependencies and recurrence if present, so they aren't passed to Task constructor
    dependencies = data.pop("dependencies", None)
    recurrence = data.pop("recurrence", None)

    # Remove read-only properties that cannot be set directly
    read_only_props = ["is_active", "is_completed", "task_type"]
    for prop in read_only_props:
        if prop in data:
            data.pop(prop)

    # Handle datetime fields - convert ISO strings to datetime objects
    if "due_by" in data and isinstance(data["due_by"], str):
        data["due_by"] = parse_iso_datetime(data["due_by"])

    if "start" in data and isinstance(data["start"], str):
        data["start"] = parse_iso_datetime(data["start"])

    if "end" in data and isinstance(data["end"], str):
        data["end"] = parse_iso_datetime(data["end"])

    # Handle time fields
    if "time_window_start" in data and isinstance(data["time_window_start"], str):
        try:
            data["time_window_start"] = datetime.strptime(
                data["time_window_start"], "%H:%M"
            ).time()
        except ValueError:
            # If the format is not as expected, try parsing it as a full datetime and extract the time
            try:
                full_dt = parse_iso_datetime(data["time_window_start"])
                data["time_window_start"] = full_dt.time()
            except Exception:
                data.pop("time_window_start")

    if "time_window_end" in data and isinstance(data["time_window_end"], str):
        try:
            data["time_window_end"] = datetime.strptime(
                data["time_window_end"], "%H:%M"
            ).time()
        except ValueError:
            # If the format is not as expected, try parsing it as a full datetime and extract the time
            try:
                full_dt = parse_iso_datetime(data["time_window_end"])
                data["time_window_end"] = full_dt.time()
            except Exception:
                data.pop("time_window_end")

    task = Task(**data)

    db.session.add(task)
    db.session.commit()

    # Handle dependencies for one-off tasks
    if dependencies:
        for dep_id in dependencies:
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
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    result = task.to_dict()
    return jsonify(result)


@task_bp.route("/<task_id>", methods=["PUT"])
def update_task(task_id):
    """Update a task"""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    data = request.json

    # Remove read-only properties that cannot be set directly
    read_only_props = ["is_active", "is_completed", "task_type"]
    for prop in read_only_props:
        if prop in data:
            data.pop(prop)

    if "content" in data:
        task.content = data["content"]
    if "duration" in data:
        task.duration = data["duration"]

    if "due_by" in data:
        if isinstance(data["due_by"], str):
            task.due_by = parse_iso_datetime(data["due_by"])
        else:
            task.due_by = data["due_by"]

    if "start" in data:
        if isinstance(data["start"], str):
            task.start = parse_iso_datetime(data["start"])
        else:
            task.start = data["start"]

    if "end" in data:
        if isinstance(data["end"], str):
            task.end = parse_iso_datetime(data["end"])
        else:
            task.end = data["end"]

    if "dependencies" in data:
        # Remove all existing dependencies
        TaskDependency.query.filter_by(task_id=task.id).delete()

        # Add new dependencies
        for dep_id in data["dependencies"]:
            dependency = TaskDependency(task_id=task.id, dependency_id=dep_id)
            db.session.add(dependency)

    if "time_window_start" in data:
        if isinstance(data["time_window_start"], str):
            try:
                task.time_window_start = datetime.strptime(
                    data["time_window_start"], "%H:%M"
                ).time()
            except ValueError:
                # Try parsing as a full ISO datetime
                try:
                    full_dt = parse_iso_datetime(data["time_window_start"])
                    task.time_window_start = full_dt.time()
                except Exception:
                    # If all parsing fails, set to None
                    task.time_window_start = None
        else:
            task.time_window_start = data["time_window_start"]

    if "time_window_end" in data:
        if isinstance(data["time_window_end"], str):
            try:
                task.time_window_end = datetime.strptime(
                    data["time_window_end"], "%H:%M"
                ).time()
            except ValueError:
                # Try parsing as a full ISO datetime
                try:
                    full_dt = parse_iso_datetime(data["time_window_end"])
                    task.time_window_end = full_dt.time()
                except Exception:
                    # If all parsing fails, set to None
                    task.time_window_end = None
        else:
            task.time_window_end = data["time_window_end"]

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
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    # Delete related dependencies
    TaskDependency.query.filter_by(task_id=task.id).delete()
    TaskDependency.query.filter_by(dependency_id=task.id).delete()

    db.session.delete(task)
    db.session.commit()

    return jsonify({"message": "Task deleted successfully"})


@task_bp.route("/<task_id>/complete", methods=["POST"])
def complete_task(task_id):
    """Mark task as complete"""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
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
@schedule_bp.route("/generate", methods=["POST"])
def generate_new_schedule():
    """Generate a new schedule based on current tasks and objectives."""
    try:
        # Get scheduling objectives from request
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        objective_config = data.get("objectives", {})
        # convert it into what our ScheduleObjective expects
        from backend.src.scheduling.objectives import ObjectiveConfig

        objectives = {
            key: ObjectiveConfig(enabled=value["enabled"], weight=value["weight"])
            for key, value in objective_config.items()
        }
        objectives = SchedulerObjectives(objectives)

        # Generate schedule
        result = generate_schedule(
            start_date=parse_iso_datetime(data.get("start_date")),
            end_date=parse_iso_datetime(data.get("end_date")),
            objectives=objectives,  # type: ignore
        )

        scheduled_tasks_data = result["scheduled_tasks"]
        unscheduled_tasks_data = result["unscheduled_tasks"]

        # Update DB for scheduled tasks
        for task_data in scheduled_tasks_data:
            task = db.session.get(Task, task_data["task_id"])
            if task:
                task.status = "scheduled"
                task.start = task_data["start"]
                task.end = task_data["end"]

        # Update DB for unscheduled tasks
        for failure in unscheduled_tasks_data:
            task = db.session.get(Task, failure["task"].id)
            if task:
                task.status = "unschedulable"
                task.start = None
                task.end = None

        db.session.commit()

        # Export scheduled tasks to JSON files
        try:

            # Get all successfully scheduled tasks
            successfully_scheduled_tasks = Task.query.filter_by(
                status="scheduled"
            ).all()

            # Get export directory
            current_export_dir = get_export_dir()
            print(f"current_export_dir: {current_export_dir}")
            if current_export_dir:
                synchronize_task_exports(
                    successfully_scheduled_tasks, current_export_dir
                )
                logger.info(
                    f"Successfully synchronized {len(successfully_scheduled_tasks)} tasks to export directory."
                )
            else:
                logger.info("Task export directory not configured. Skipping export.")
        except Exception as e_export:
            logger.error(f"Error during task export synchronization: {str(e_export)}")
            # Don't fail the schedule generation if export fails
            pass

        # Prepare response
        scheduled_tasks_response = [
            t.to_dict() for t in Task.query.filter_by(status="scheduled").all()
        ]
        unscheduled_tasks_response = [
            {"task": failure["task"].to_dict(), "reason": failure["reason"]}
            for failure in unscheduled_tasks_data
        ]

        return jsonify(
            {
                "message": "Schedule generated successfully",
                "scheduled_tasks": scheduled_tasks_response,
                "unscheduled_tasks": unscheduled_tasks_response,
                "status_message": result["status_message"],
            }
        )

    except Exception as e:
        logger.error(f"Error generating schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500


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
    print(f"calendar_dir: {calendar_dir}")
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


@settings_bp.route("/export-dir", methods=["GET"])
def get_task_export_directory_route():
    """Get the current task export directory setting."""
    export_dir = get_export_dir()
    is_set_val = (
        export_dir is not None
        and os.path.exists(export_dir)
        and os.path.isdir(export_dir)
    )
    return jsonify(
        {
            "export_dir": export_dir,
            "is_set": is_set_val,
        }
    )


@settings_bp.route("/export-dir", methods=["POST"])
def set_task_export_directory_route():
    """Set the task export directory setting."""
    data = request.json
    if not data or "export_dir" not in data:
        return jsonify({"error": "Missing export_dir parameter"}), 400

    export_dir = data["export_dir"]

    if not os.path.exists(export_dir):
        return jsonify({"error": f"Directory does not exist: {export_dir}"}), 400
    if not os.path.isdir(export_dir):
        return jsonify({"error": f"Path is not a directory: {export_dir}"}), 400

    set_export_dir(export_dir)
    return jsonify(
        {
            "message": "Task export directory set successfully",
            "export_dir": export_dir,
        }
    )
