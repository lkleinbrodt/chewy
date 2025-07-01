import json
import os
from datetime import datetime, timezone

import pytest

from backend.models.task import Task
from backend.src.scheduling.task_exporter import (
    _delete_task_file,
    _format_task_for_export,
    _get_export_filename,
    _read_exported_task_file,
    _write_task_to_file,
    format_datetime_for_outlook,
    synchronize_task_exports,
)


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    task = Task(
        id="test-task-1",
        content="Test Task",
        start=datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc),
        end=datetime(2024, 3, 20, 11, 0, tzinfo=timezone.utc),
        status="scheduled",
    )
    return task


def test_format_task_for_export(create_task_factory):
    """Test formatting a task for export."""
    # Create a task using the factory
    task = create_task_factory(content="Test Task", duration=60)

    # Set the scheduling fields manually for testing
    task.start = datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc)
    task.end = datetime(2024, 3, 20, 11, 0, tzinfo=timezone.utc)
    task.status = "scheduled"

    result = _format_task_for_export(task)

    assert result["id"] == task.id
    assert result["subject"] == "Test Task"
    assert result["start"] == "2024-03-20T10:00:00.0000000"
    assert result["end"] == "2024-03-20T11:00:00.0000000"
    assert result["isAllDay"] is False
    assert "Chewy Scheduled" in result["categories"]
    assert result["body"]["contentType"] == "HTML"
    assert result["body"]["content"] == "Test Task"
    assert result["location"]["displayName"] == ""


def test_get_export_filename():
    """Test generating export filename."""
    task_id = "test-task-1"
    expected = "chewy_task_test-task-1.json"
    assert _get_export_filename(task_id) == expected


def test_read_exported_task_file(tmp_path):
    """Test reading a task file."""
    # Create a test file with known content
    test_data = {
        "id": "test-task-1",
        "subject": "Test Task",
        "start": "2024-03-20T10:00:00+00:00",
        "end": "2024-03-20T11:00:00+00:00",
    }

    test_file = tmp_path / "test_task.json"
    test_file.write_text(json.dumps(test_data))

    result = _read_exported_task_file(str(test_file))
    assert result == test_data


def test_write_task_to_file(tmp_path):
    """Test writing a task to file."""
    task_data = {"id": "test-task-1", "subject": "Test Task"}

    test_file = tmp_path / "test_task.json"
    _write_task_to_file(task_data, str(test_file))

    # Read back the file and verify content
    written_data = json.loads(test_file.read_text())
    assert written_data == task_data


def test_delete_task_file(tmp_path):
    """Test deleting a task file."""
    test_file = tmp_path / "test_task.json"
    test_file.write_text("test content")

    _delete_task_file(str(test_file))
    assert not test_file.exists()


@pytest.fixture
def tmp_export_dir(tmp_path):
    """Create a temporary export directory."""
    return str(tmp_path)


def test_synchronize_new_task(create_task_factory, tmp_path):
    """Test synchronizing a new task."""
    # Create a task using the factory
    task = create_task_factory(content="Test Task", duration=60)

    # Set the scheduling fields manually for testing
    task.start = datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc)
    task.end = datetime(2024, 3, 20, 11, 0, tzinfo=timezone.utc)
    task.status = "scheduled"

    export_dir = tmp_path / "export_dir"
    export_dir.mkdir()

    synchronize_task_exports([task], str(export_dir))

    # Verify file was created with correct data
    expected_file = export_dir / f"chewy_task_{task.id}.json"
    assert expected_file.exists()

    written_data = json.loads(expected_file.read_text())
    assert written_data["id"] == task.id
    assert written_data["subject"] == task.content


def test_synchronize_updated_task(create_task_factory, tmp_path):
    """Test synchronizing an updated task."""
    # Create a task using the factory
    task = create_task_factory(content="Updated Task", duration=60)

    # Set the scheduling fields manually for testing
    task.start = datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc)
    task.end = datetime(2024, 3, 20, 11, 0, tzinfo=timezone.utc)
    task.status = "scheduled"

    export_dir = tmp_path / "export_dir"
    export_dir.mkdir()

    # Create initial task data
    initial_data = {
        "id": task.id,
        "subject": "Old Subject",
        "start": "2024-03-20T09:00:00+00:00",
        "end": "2024-03-20T10:00:00+00:00",
    }

    # Write initial file
    initial_file = export_dir / f"chewy_task_{task.id}.json"
    initial_file.write_text(json.dumps(initial_data))

    synchronize_task_exports([task], str(export_dir))

    # Verify file was updated with new data
    written_data = json.loads(initial_file.read_text())
    assert written_data["subject"] == task.content
    assert written_data["start"] == format_datetime_for_outlook(task.start)
    assert written_data["end"] == format_datetime_for_outlook(task.end)


def test_synchronize_no_change_to_task(create_task_factory, tmp_path):
    """Test synchronizing a task with no changes."""
    # Create a task using the factory
    task = create_task_factory(content="Test Task", duration=60)

    # Set the scheduling fields manually for testing
    task.start = datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc)
    task.end = datetime(2024, 3, 20, 11, 0, tzinfo=timezone.utc)
    task.status = "scheduled"

    export_dir = tmp_path / "export_dir"
    export_dir.mkdir()

    # Write initial file with same data
    current_data = _format_task_for_export(task)
    initial_file = export_dir / f"chewy_task_{task.id}.json"
    initial_file.write_text(json.dumps(current_data))

    # Get file modification time before sync
    mtime_before = initial_file.stat().st_mtime

    synchronize_task_exports([task], str(export_dir))

    # Verify file was not modified
    mtime_after = initial_file.stat().st_mtime
    assert mtime_before == mtime_after


def test_synchronize_deleted_task(create_task_factory, tmp_path):
    """Test synchronizing when a task is deleted."""
    # Create a task using the factory
    task = create_task_factory(content="Test Task", duration=60)

    export_dir = tmp_path / "export_dir"
    export_dir.mkdir()

    # Create a file for the task
    task_file = export_dir / f"chewy_task_{task.id}.json"
    task_file.write_text(json.dumps({"id": task.id}))

    synchronize_task_exports([], str(export_dir))

    # Verify file was deleted
    assert not task_file.exists()


def test_synchronize_export_dir_not_set():
    """Test synchronizing when export directory is not set."""
    synchronize_task_exports([], None)
    # No assertions needed - just verifying it doesn't crash


def test_synchronize_io_error_writing_file(create_task_factory, tmp_path):
    """Test handling IO error when writing file."""
    # Create a task using the factory
    task = create_task_factory(content="Test Task", duration=60)

    # Set the scheduling fields manually for testing
    task.start = datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc)
    task.end = datetime(2024, 3, 20, 11, 0, tzinfo=timezone.utc)
    task.status = "scheduled"

    export_dir = tmp_path / "export_dir"
    export_dir.mkdir()

    # Make the directory read-only to force an IO error
    export_dir.chmod(0o444)

    with pytest.raises(IOError):
        synchronize_task_exports([task], str(export_dir))

    # Restore permissions
    export_dir.chmod(0o755)
