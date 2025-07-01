import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from datetime import datetime, timedelta

import pytest
import pytz

from backend import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models.calendar import CalendarEvent
from backend.models.task import RecurringEvent, Task, TaskDependency

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
    """Create a configurable date range for testing"""

    def _date_range(days=7):
        start_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # if start_date is a weekend, move it to the next monday
        while start_date.weekday() > 4:
            start_date = start_date + timedelta(days=1)
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


def create_time(hour, minute):
    """Helper function to create a time object in UTC."""
    return (
        datetime.now(pytz.UTC)
        .replace(hour=hour, minute=minute, second=0, microsecond=0)
        .time()
    )


def valid_due_date(start_date, days=3, eod=True):
    """Create a valid due date for a task, aka it will make sure the due date is not on a weekend"""
    due_date = start_date + timedelta(days=days)
    if due_date.weekday() > 4:
        due_date = due_date + timedelta(days=2)
    if eod:
        due_date = datetime.combine(
            due_date.date(), create_time(TestingConfig.WORK_END_HOUR, 0)
        )
    return due_date


def validate_schedule(scheduled_tasks, tasks: list[Task], expected_order=None):
    assert scheduled_tasks is not None
    assert len(scheduled_tasks) == len(tasks)
    for i, scheduled_task in enumerate(scheduled_tasks):
        rel_task = [task for task in tasks if task.id == scheduled_task["task_id"]][0]
        assert scheduled_task["end"] <= rel_task.due_by

        if expected_order is not None:
            assert expected_order[i] == rel_task.id
    return scheduled_tasks
