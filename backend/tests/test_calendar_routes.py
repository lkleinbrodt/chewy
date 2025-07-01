import json
import os
from datetime import datetime, timedelta

import pytest

from backend.models.calendar import CalendarEvent
from backend.settings import set_calendar_dir
from backend.src.utils import parse_iso_datetime


class TestCalendarSyncDetection:
    """Test suite for calendar sync change detection."""

    def test_sync_no_changes(self, app, test_db, tmp_path):
        with app.app_context():
            # Create a test event in DB
            event = CalendarEvent(
                id="test-event-1",
                subject="Test Event",
                start=datetime.utcnow(),
                end=datetime.utcnow() + timedelta(hours=1),
                is_chewy_managed=False,
            )
            test_db.session.add(event)
            test_db.session.commit()

            # Write matching event JSON file to tmp_path
            event_data = {
                "id": "test-event-1",
                "subject": "Test Event",
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
            }
            event_file = tmp_path / "test-event-1.json"
            event_file.write_text(json.dumps(event_data))

            set_calendar_dir(str(tmp_path))

            response = app.test_client().post("/api/calendar/sync")
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data["changes_detected"] is False

    def test_sync_new_event_added(self, app, test_db, tmp_path):
        with app.app_context():
            # Write new event JSON file to tmp_path
            event_data = {
                "id": "new-event-1",
                "subject": "New Event",
                "start": datetime.utcnow().isoformat(),
                "end": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            }
            event_file = tmp_path / "new-event-1.json"
            event_file.write_text(json.dumps(event_data))

            set_calendar_dir(str(tmp_path))

            response = app.test_client().post("/api/calendar/sync")
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data["changes_detected"] is True

    def test_sync_event_modified(self, app, test_db, tmp_path):
        with app.app_context():
            # Create a test event in DB
            event = CalendarEvent(
                id="test-event-1",
                subject="Original Subject",
                start=datetime.utcnow(),
                end=datetime.utcnow() + timedelta(hours=1),
                is_chewy_managed=False,
            )
            test_db.session.add(event)
            test_db.session.commit()

            # Write modified event JSON file to tmp_path
            event_data = {
                "id": "test-event-1",
                "subject": "Modified Subject",  # Changed subject
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
            }
            event_file = tmp_path / "test-event-1.json"
            event_file.write_text(json.dumps(event_data))

            set_calendar_dir(str(tmp_path))

            response = app.test_client().post("/api/calendar/sync")
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data["changes_detected"] is True

    def test_sync_event_deleted(self, app, test_db, tmp_path):
        with app.app_context():
            # Create a test event in DB
            event = CalendarEvent(
                id="test-event-1",
                subject="Test Event",
                start=datetime.utcnow(),
                end=datetime.utcnow() + timedelta(hours=1),
                is_chewy_managed=False,
            )
            test_db.session.add(event)
            test_db.session.commit()

            # No event file written (simulates deletion)
            set_calendar_dir(str(tmp_path))

            response = app.test_client().post("/api/calendar/sync")
            data = json.loads(response.data)

            assert response.status_code == 400
            assert data["error"] == "NO_JSON_FILES"

    def test_sync_only_chewy_managed_event_changed_no_detection(
        self, app, test_db, tmp_path
    ):
        with app.app_context():
            # Create a Chewy-managed event in DB
            event = CalendarEvent(
                id="chewy-event-1",
                subject="Chewy Event",
                start=datetime.utcnow(),
                end=datetime.utcnow() + timedelta(hours=1),
                is_chewy_managed=True,
            )
            test_db.session.add(event)
            test_db.session.commit()

            # Write modified Chewy event JSON file to tmp_path
            event_data = {
                "id": "chewy-event-1",
                "subject": "Modified Chewy Event",
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "categories": ["Chewy Managed"],
            }
            event_file = tmp_path / "chewy-event-1.json"
            event_file.write_text(json.dumps(event_data))

            set_calendar_dir(str(tmp_path))

            response = app.test_client().post("/api/calendar/sync")
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data["changes_detected"] is False

    def test_sync_all_day_event_skipped_no_change_detected(
        self, app, test_db, tmp_path
    ):
        with app.app_context():
            # Write all-day event JSON file to tmp_path
            event_data = {
                "id": "all-day-event-1",
                "subject": "All Day Event",
                "start": datetime.utcnow().isoformat(),
                "end": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "isAllDay": True,
            }
            event_file = tmp_path / "all-day-event-1.json"
            event_file.write_text(json.dumps(event_data))

            set_calendar_dir(str(tmp_path))

            response = app.test_client().post("/api/calendar/sync")
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data["all_day_events_skipped"] > 0
            assert data["changes_detected"] is False
