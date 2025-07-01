import json
import logging
import os
from typing import Dict, List, Optional

from backend.models.task import Task

logger = logging.getLogger(__name__)


def format_datetime_for_outlook(dt):
    """Format datetime in Microsoft Outlook format: YYYY-MM-DDTHH:MM:SS.0000000"""
    if dt is None:
        return None
    # Format as YYYY-MM-DDTHH:MM:SS.0000000
    return dt.strftime("%Y-%m-%dT%H:%M:%S.0000000")


def _format_task_for_export(task: Task) -> dict:
    """Format a task for export to JSON."""

    return {
        "id": task.id,
        "subject": task.content,
        "start": format_datetime_for_outlook(task.start),
        "end": format_datetime_for_outlook(task.end),
        "isAllDay": False,
        "categories": ["Chewy Scheduled"],
        "body": {"contentType": "HTML", "content": task.content},
        "location": {"displayName": ""},
    }


def _get_export_filename(task_id: str) -> str:
    """Generate the filename for a task's export file."""
    return f"chewy_task_{task_id}.json"


def _read_exported_task_file(filepath: str) -> Optional[dict]:
    """Read and parse a task's export file."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error reading task file {filepath}: {str(e)}")
        return None


def _write_task_to_file(task_data: dict, filepath: str) -> None:
    """Write task data to a JSON file."""
    try:
        with open(filepath, "w") as f:
            json.dump(task_data, f, indent=2)
    except IOError as e:
        logger.error(f"Error writing task file {filepath}: {str(e)}")
        raise


def _delete_task_file(filepath: str) -> None:
    """Delete a task's export file."""
    try:
        os.remove(filepath)
    except IOError as e:
        logger.error(f"Error deleting task file {filepath}: {str(e)}")
        raise


def synchronize_task_exports(
    scheduled_chewy_tasks: List[Task], export_dir: str
) -> None:
    """Synchronize task exports to JSON files in the export directory."""
    if not export_dir:
        logger.info("Task export directory not configured. Skipping export.")
        return

    try:
        # Get list of current export files
        current_files = os.listdir(export_dir)
        current_exported_ids = set()
        tasks_to_export_map = {task.id: task for task in scheduled_chewy_tasks}

        # Process each scheduled task
        for task in scheduled_chewy_tasks:
            task_id = task.id
            filename = _get_export_filename(task_id)
            filepath = os.path.join(export_dir, filename)
            new_task_data = _format_task_for_export(task)

            if os.path.exists(filepath):
                # Check if task data has changed
                existing_task_data = _read_exported_task_file(filepath)
                if existing_task_data != new_task_data:
                    _write_task_to_file(new_task_data, filepath)
            else:
                # Create new file
                _write_task_to_file(new_task_data, filepath)

            current_exported_ids.add(task_id)

        # Clean up orphaned files
        for filename in current_files:
            if not filename.startswith("chewy_task_") or not filename.endswith(".json"):
                continue

            task_id = filename[11:-5]  # Remove "chewy_task_" prefix and ".json" suffix
            if task_id not in tasks_to_export_map:
                filepath = os.path.join(export_dir, filename)
                _delete_task_file(filepath)

    except Exception as e:
        logger.error(f"Error during task export synchronization: {str(e)}")
        raise
