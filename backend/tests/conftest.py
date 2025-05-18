import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from datetime import datetime, timedelta

import pytest

from backend import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import CalendarEvent, RecurringEvent, Task, TaskDependency

"""
Pytest module for testing the scheduler functionality.
"""


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        yield app
        # Clean up after tests
        db.session.remove()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def test_db(app):
    """Set up the database for testing and clean it after tests."""
    with app.app_context():
        # Clear existing test data before each test
        RecurringEvent.query.delete()
        TaskDependency.query.delete()
        Task.query.delete()
        CalendarEvent.query.filter_by(is_chewy_managed=False).delete()
        db.session.commit()

        yield db

        # Clean up after test
        RecurringEvent.query.delete()
        TaskDependency.query.delete()
        Task.query.delete()
        CalendarEvent.query.filter_by(is_chewy_managed=False).delete()
        db.session.commit()


@pytest.fixture
def date_range():
    """Create a fixed date range for testing."""
    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=5)
    return start_date, end_date


@pytest.fixture
def dynamic_date_range():
    """Create a configurable date range for testing"""

    def _date_range(days=5):
        start_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = start_date + timedelta(days=days)
        return start_date, end_date

    return _date_range


@pytest.fixture
def create_task_factory(test_db):
    """Factory to create tasks with different configurations"""

    def _create_task(
        content, duration, due_by=None, time_window_start=None, time_window_end=None
    ):
        task = Task(
            content=content,
            duration=duration,
            due_by=due_by,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
        )
        test_db.session.add(task)
        test_db.session.commit()
        return task

    return _create_task


@pytest.fixture
def create_calendar_event_factory(test_db):
    """Factory to create calendar events"""

    def _create_event(subject, start, end, is_chewy_managed=False):
        event = CalendarEvent(
            subject=subject, start=start, end=end, is_chewy_managed=is_chewy_managed
        )
        test_db.session.add(event)
        test_db.session.commit()
        return event

    return _create_event


@pytest.fixture
def create_recurring_event_factory(test_db):
    """Factory to create recurring events"""

    def _create_recurring(
        content, duration, recurrence, time_window_start=None, time_window_end=None
    ):
        event = RecurringEvent(
            content=content,
            duration=duration,
            recurrence=recurrence,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
        )
        test_db.session.add(event)
        test_db.session.commit()
        return event

    return _create_recurring
