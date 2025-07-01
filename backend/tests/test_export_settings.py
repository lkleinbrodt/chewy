import os
from pathlib import Path

import pytest

from backend.settings import get_export_dir, set_export_dir


@pytest.fixture(autouse=True)
def reset_export_dir():
    """Reset export directory setting before each test."""
    # Clear any existing setting
    try:
        from backend.settings import set_setting

        set_setting("task_export_dir", None)
    except:
        pass
    yield
    # Clean up after test
    try:
        from backend.settings import set_setting

        set_setting("task_export_dir", None)
    except:
        pass


def test_get_export_dir_default(client):
    """Test getting export directory when none is set"""
    response = client.get("/api/settings/export-dir")
    assert response.status_code == 200
    data = response.get_json()
    assert data["export_dir"] is None
    assert data["is_set"] is False


def test_set_export_dir_success(client, tmp_path):
    """Test setting a valid export directory"""
    # Create a real directory for testing
    export_dir = tmp_path / "export_dir"
    export_dir.mkdir()

    response = client.post(
        "/api/settings/export-dir", json={"export_dir": str(export_dir)}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Task export directory set successfully"
    assert data["export_dir"] == str(export_dir)

    # Verify the setting was actually stored
    assert get_export_dir() == str(export_dir)


def test_set_export_dir_nonexistent_path(client):
    """Test setting a non-existent export directory"""
    response = client.post(
        "/api/settings/export-dir", json={"export_dir": "/this/path/does/not/exist"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "does not exist" in data["error"]


def test_set_export_dir_not_a_directory(client, tmp_path):
    """Test setting a path that exists but is not a directory"""
    # Create a file instead of a directory
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test")

    response = client.post(
        "/api/settings/export-dir", json={"export_dir": str(test_file)}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "not a directory" in data["error"]


def test_get_export_dir_after_set(client, tmp_path):
    """Test getting export directory after it has been set"""
    # Create a real directory for testing
    export_dir = tmp_path / "export_dir"
    export_dir.mkdir()

    # First set the directory
    client.post("/api/settings/export-dir", json={"export_dir": str(export_dir)})

    # Then get it
    response = client.get("/api/settings/export-dir")
    assert response.status_code == 200
    data = response.get_json()
    assert data["export_dir"] == str(export_dir)
    assert data["is_set"] is True
