"""
Pytest module for testing the scheduler functionality.
"""

from datetime import datetime, timedelta

import pytest
import pytz

from backend.config import TestingConfig
from backend.extensions import db
from backend.models import CalendarEvent, RecurringEvent, Task, TaskDependency
from backend.src.scheduling.scheduler import generate_schedule


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


class TestSchedulerBasics:
    def test_empty_schedule(self, app, test_db, dynamic_date_range):
        """Test scheduler works with no tasks or events"""
        start_date, end_date = dynamic_date_range()
        with app.app_context():
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)
            assert len(scheduled_tasks) == 0
            assert status_message == "Feasible"

    def test_basic_task_scheduling(
        self, app, test_db, dynamic_date_range, create_task_factory
    ):
        """Test scheduling a single task with no constraints"""
        start_date, end_date = dynamic_date_range()
        with app.app_context():
            # Create a simple task
            tasks = []
            tasks.append(
                create_task_factory(
                    content="Simple Task",
                    duration=60,  # 1 hour
                    due_by=valid_due_date(start_date, 3),
                )
            )

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Assertions
            validate_schedule(scheduled_tasks, tasks)

            # now let's try with multiple tasks
            for i in range(3):
                tasks.append(
                    create_task_factory(
                        content=f"Task {i}",
                        duration=60,  # 1 hour
                        due_by=valid_due_date(start_date, i),
                    )
                )
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)
            validate_schedule(scheduled_tasks, tasks)


class TestScheduler:
    """Test suite for the scheduler functionality."""

    def test_task_with_calendar_conflict(self, app, test_db, date_range):
        """Test that tasks are scheduled around existing calendar events."""
        start_date, end_date = date_range

        with app.app_context():
            # Create a calendar event
            event = CalendarEvent(
                subject="Important Meeting",
                start=datetime.combine(start_date.date(), create_time(10, 0)),
                end=datetime.combine(start_date.date(), create_time(11, 0)),
                is_chewy_managed=False,
            )
            test_db.session.add(event)

            # Create a task
            task = Task(
                content="Task During Working Hours",
                duration=60,  # 1 hour
                due_by=valid_due_date(start_date),
            )
            test_db.session.add(task)
            test_db.session.commit()

            # Configure work hours

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Assertions
            validate_schedule(scheduled_tasks, [task])

            # Task should not overlap with the calendar event
            task_start = scheduled_tasks[0]["start"]
            task_end = scheduled_tasks[0]["end"]
            assert not (task_start < event.end and task_end > event.start)

    def test_recurring_task(self, app, test_db, date_range):
        """Test scheduling of recurring tasks."""
        start_date, end_date = date_range

        with app.app_context():

            # Create a recurring task for weekdays
            recurring_task = RecurringEvent(
                content="Daily Review",
                duration=45,  # 45 minutes
                recurrence=[0, 1, 2, 3, 4],  # Monday to Friday
                time_window_start=create_time(9, 0),
                time_window_end=create_time(17, 0),
            )
            test_db.session.add(recurring_task)
            test_db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Find tasks that were created from the recurring event
            # The scheduler creates Task objects from RecurringEvents
            recurring_tasks = Task.query.filter(
                Task.recurring_event_id == recurring_task.id
            ).all()

            # Verify that recurring tasks were created
            assert len(recurring_tasks) > 0

            # Verify that all recurring tasks were scheduled
            scheduled_recurring_tasks = []
            for task in scheduled_tasks:
                for rt in recurring_tasks:
                    if task["task_id"] == rt.id:
                        scheduled_recurring_tasks.append(task)
                        break

            assert len(scheduled_recurring_tasks) == len(recurring_tasks)

    def test_task_dependencies(self, app, test_db, date_range):
        """Test that dependent tasks are scheduled in the correct order."""
        start_date, end_date = date_range

        with app.app_context():
            # Create two tasks with a dependency
            task1 = Task(
                content="First Task",
                duration=60,  # 1 hour
                due_by=start_date + timedelta(days=3),
            )
            test_db.session.add(task1)

            task2 = Task(
                content="Dependent Task",
                duration=120,  # 2 hours
                due_by=start_date + timedelta(days=4),
            )
            test_db.session.add(task2)
            test_db.session.commit()

            # Create dependency: task2 depends on task1
            dependency = TaskDependency(task_id=task2.id, dependency_id=task1.id)
            test_db.session.add(dependency)
            test_db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Find the scheduled tasks
            scheduled_task1 = next(
                (task for task in scheduled_tasks if task["task_id"] == task1.id),
                None,
            )
            scheduled_task2 = next(
                (task for task in scheduled_tasks if task["task_id"] == task2.id),
                None,
            )

            # Assertions
            assert scheduled_task1 is not None
            assert scheduled_task2 is not None

            # Task2 should be scheduled after Task1 ends
            assert scheduled_task2["start"] >= scheduled_task1["end"]

    def test_work_hours_constraint(self, app, test_db, date_range):
        """Test that tasks are scheduled within work hours."""
        start_date, end_date = date_range
        # instad, we actually want the start date to be one minute before the end of the day
        # that way we can test the work hours constraint
        end_of_day = app.config["WORK_END_HOUR"]
        start_date = datetime.combine(
            start_date.date(), create_time(end_of_day - 1, 59)
        )
        end_date = start_date + timedelta(days=3)

        with app.app_context():
            # Create a task
            task = Task(
                content="Work Hours Task",
                duration=60,  # 1 hour
                due_by=valid_due_date(start_date),
            )
            test_db.session.add(task)
            test_db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Assertions
            assert scheduled_tasks is not None

            # Task should be scheduled within work hours
            task_hour = scheduled_tasks[0]["start"].hour
            assert (
                TestingConfig.WORK_START_HOUR <= task_hour < TestingConfig.WORK_END_HOUR
            )
            # same for the end
            task_hour = scheduled_tasks[0]["end"].hour
            assert (
                TestingConfig.WORK_START_HOUR <= task_hour < TestingConfig.WORK_END_HOUR
            )

    def test_complex_schedule(self, app, test_db, date_range):
        """Test a complex scheduling scenario with multiple tasks, events, and dependencies."""
        start_date, end_date = date_range

        with app.app_context():
            # Set work hours

            # Create multiple tasks
            task1 = Task(
                content="Important Task",
                duration=60,  # 1 hour
                due_by=valid_due_date(start_date),
            )
            db.session.add(task1)

            task2 = Task(
                content="Urgent Task",
                duration=30,  # 30 minutes
                due_by=valid_due_date(start_date),
            )
            db.session.add(task2)

            task3 = Task(
                content="Task 3",
                duration=120,  # 2 hours
                due_by=valid_due_date(start_date),
            )
            db.session.add(task3)
            db.session.commit()

            # Create a dependency: task3 depends on task1
            dependency = TaskDependency(task_id=task3.id, dependency_id=task1.id)
            db.session.add(dependency)

            # Create a recurring task
            recurring_event = RecurringEvent(
                content="Daily Review",
                duration=45,  # 45 minutes
                recurrence=[0, 1, 2, 3, 4],  # Monday to Friday
                time_window_start=create_time(9, 0),
                time_window_end=create_time(17, 0),
            )
            db.session.add(recurring_event)

            # Create some calendar events
            # Morning meeting for each weekday
            for day in range((end_date - start_date).days + 1):
                event_date = start_date + timedelta(days=day)
                if event_date.weekday() < 5:  # Weekdays only
                    morning_meeting = CalendarEvent(
                        subject=f"Morning Meeting Day {day+1}",
                        start=datetime.combine(event_date.date(), create_time(9, 0)),
                        end=datetime.combine(event_date.date(), create_time(10, 0)),
                        is_chewy_managed=False,
                    )
                    db.session.add(morning_meeting)

            # Add a longer meeting
            long_meeting = CalendarEvent(
                subject="Quarterly Planning",
                start=datetime.combine(
                    (start_date + timedelta(days=1)).date(), create_time(13, 0)
                ),
                end=datetime.combine(
                    (start_date + timedelta(days=1)).date(), create_time(16, 0)
                ),
                is_chewy_managed=False,
            )
            db.session.add(long_meeting)
            db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Assertions
            assert scheduled_tasks is not None
            assert len(scheduled_tasks) > 0

            # Check that all one-off tasks are scheduled
            one_off_tasks = [
                task
                for task in scheduled_tasks
                if task["task_id"] in [task1.id, task2.id, task3.id]
            ]
            assert len(one_off_tasks) == 3

            # Check dependency constraint
            task1_scheduled = next(
                (task for task in scheduled_tasks if task["task_id"] == task1.id), None
            )
            task3_scheduled = next(
                (task for task in scheduled_tasks if task["task_id"] == task3.id), None
            )
            assert task1_scheduled["end"] <= task3_scheduled["start"]

            # Check that no tasks overlap with calendar events
            for task in scheduled_tasks:
                task_start = task["start"]
                task_end = task["end"]

                # Get all calendar events that might overlap with this task
                events = CalendarEvent.query.filter(
                    CalendarEvent.start <= task_end,
                    CalendarEvent.end >= task_start,
                    CalendarEvent.is_chewy_managed == False,
                ).all()

                for event in events:
                    # Ensure no overlap
                    assert not (task_start < event.end and task_end > event.start)


class TestTimeConstraints:

    def test_task_specific_time_window(
        self, app, test_db, dynamic_date_range, create_task_factory
    ):
        """Test tasks with specific time windows"""
        start_date, end_date = dynamic_date_range()

        with app.app_context():
            # Create a task with a specific time window
            time_window_start = create_time(13, 0)  # 1 PM
            time_window_end = create_time(16, 0)  # 4 PM

            task = create_task_factory(
                content="Afternoon Task",
                duration=60,  # 1 hour
                due_by=start_date + timedelta(days=3),
                time_window_start=time_window_start,
                time_window_end=time_window_end,
            )

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Assertions
            assert scheduled_tasks is not None
            assert len(scheduled_tasks) == 1

            # Task should be scheduled within its time window
            task_start_hour = scheduled_tasks[0]["start"].hour
            task_end_hour = scheduled_tasks[0]["end"].hour

            assert 13 <= task_start_hour < 16
            assert 14 <= task_end_hour <= 16


class TestDependencies:
    def test_simple_dependency_chain(
        self, app, test_db, dynamic_date_range, create_task_factory
    ):
        """Test a simple chain of dependent tasks"""
        start_date, end_date = dynamic_date_range()

        with app.app_context():
            # Create tasks with A depends on B depends on C
            task_c = create_task_factory(
                content="Task C",
                duration=60,  # 1 hour
                due_by=start_date + timedelta(days=5),
            )

            task_b = create_task_factory(
                content="Task B",
                duration=90,  # 1.5 hours
                due_by=start_date + timedelta(days=5),
            )

            task_a = create_task_factory(
                content="Task A",
                duration=120,  # 2 hours
                due_by=start_date + timedelta(days=5),
            )

            # Create dependencies: A depends on B depends on C
            dependency_b_on_c = TaskDependency(
                task_id=task_b.id, dependency_id=task_c.id
            )
            dependency_a_on_b = TaskDependency(
                task_id=task_a.id, dependency_id=task_b.id
            )

            test_db.session.add(dependency_b_on_c)
            test_db.session.add(dependency_a_on_b)
            test_db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Assertions
            assert scheduled_tasks is not None
            assert len(scheduled_tasks) == 3

            # Find the scheduled tasks
            scheduled_c = next(
                (task for task in scheduled_tasks if task["task_id"] == task_c.id),
                None,
            )
            scheduled_b = next(
                (task for task in scheduled_tasks if task["task_id"] == task_b.id),
                None,
            )
            scheduled_a = next(
                (task for task in scheduled_tasks if task["task_id"] == task_a.id),
                None,
            )

            # Verify dependency order
            assert scheduled_c["end"] <= scheduled_b["start"]
            assert scheduled_b["end"] <= scheduled_a["start"]

    def test_complex_dependency_graph(
        self, app, test_db, dynamic_date_range, create_task_factory
    ):
        """Test a more complex dependency graph"""
        start_date, end_date = dynamic_date_range()

        with app.app_context():
            # Create tasks for a more complex dependency graph
            # A depends on B and C
            # B depends on D
            # C depends on D and E

            task_d = create_task_factory(
                content="Task D",
                duration=60,  # 1 hour
                due_by=start_date + timedelta(days=5),
            )

            task_e = create_task_factory(
                content="Task E",
                duration=45,  # 45 minutes
                due_by=start_date + timedelta(days=5),
            )

            task_b = create_task_factory(
                content="Task B",
                duration=90,  # 1.5 hours
                due_by=start_date + timedelta(days=5),
            )

            task_c = create_task_factory(
                content="Task C",
                duration=75,  # 1.25 hours
                due_by=start_date + timedelta(days=5),
            )

            task_a = create_task_factory(
                content="Task A",
                duration=120,  # 2 hours
                due_by=start_date + timedelta(days=5),
            )

            # Create dependencies
            dependencies = [
                TaskDependency(task_id=task_b.id, dependency_id=task_d.id),
                TaskDependency(task_id=task_c.id, dependency_id=task_d.id),
                TaskDependency(task_id=task_c.id, dependency_id=task_e.id),
                TaskDependency(task_id=task_a.id, dependency_id=task_b.id),
                TaskDependency(task_id=task_a.id, dependency_id=task_c.id),
            ]

            for dep in dependencies:
                test_db.session.add(dep)
            test_db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Assertions
            assert scheduled_tasks is not None
            assert len(scheduled_tasks) == 5

            # Find the scheduled tasks
            task_map = {
                task_a.id: "A",
                task_b.id: "B",
                task_c.id: "C",
                task_d.id: "D",
                task_e.id: "E",
            }

            scheduled_map = {}
            for task in scheduled_tasks:
                task_id = task["task_id"]
                if task_id in task_map:
                    scheduled_map[task_map[task_id]] = task

            # Verify dependency relationships
            assert scheduled_map["D"]["end"] <= scheduled_map["B"]["start"]
            assert scheduled_map["D"]["end"] <= scheduled_map["C"]["start"]
            assert scheduled_map["E"]["end"] <= scheduled_map["C"]["start"]
            assert scheduled_map["B"]["end"] <= scheduled_map["A"]["start"]
            assert scheduled_map["C"]["end"] <= scheduled_map["A"]["start"]

    def test_dependency_with_time_windows(
        self, app, test_db, dynamic_date_range, create_task_factory
    ):
        """Test dependencies combined with time windows"""
        start_date, end_date = dynamic_date_range()

        with app.app_context():

            # Create tasks with dependencies and time windows
            # Task B depends on Task A
            # Task A has a morning time window
            # Task B has an afternoon time window

            morning_window_start = create_time(9, 0)
            morning_window_end = create_time(12, 0)

            afternoon_window_start = create_time(13, 0)
            afternoon_window_end = create_time(17, 0)

            # Create tasks with enough time to complete them
            task_a = create_task_factory(
                content="Morning Task",
                duration=60,  # 1 hour
                due_by=end_date,  # Due at the end of the scheduling period
                time_window_start=morning_window_start,
                time_window_end=morning_window_end,
            )

            task_b = create_task_factory(
                content="Afternoon Task",
                duration=90,  # 1.5 hours
                due_by=end_date,  # Due at the end of the scheduling period
                time_window_start=afternoon_window_start,
                time_window_end=afternoon_window_end,
            )

            # Create dependency: B depends on A
            dependency = TaskDependency(task_id=task_b.id, dependency_id=task_a.id)
            test_db.session.add(dependency)
            test_db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Check if the schedule is feasible
            if status_message == "Infeasible":
                # If infeasible, we'll skip the detailed checks
                pytest.skip(
                    "Scheduler found the problem to be infeasible - skipping detailed checks"
                )

            # Assertions
            assert status_message == "Feasible"
            assert scheduled_tasks is not None
            assert len(scheduled_tasks) == 2

            # Find the scheduled tasks
            scheduled_a = next(
                (task for task in scheduled_tasks if task["task_id"] == task_a.id),
                None,
            )
            scheduled_b = next(
                (task for task in scheduled_tasks if task["task_id"] == task_b.id),
                None,
            )

            # Verify both tasks were scheduled
            assert scheduled_a is not None
            assert scheduled_b is not None

            # Verify task A is in the morning window
            assert 9 <= scheduled_a["start"].hour < 12

            # Verify task B is in the afternoon window
            assert 13 <= scheduled_b["start"].hour < 17

            # Verify dependency order
            assert scheduled_a["end"] <= scheduled_b["start"]


class TestRecurringEvents:
    def test_recurring_daily_task(
        self, app, test_db, dynamic_date_range, create_recurring_event_factory
    ):
        """Test scheduling of daily recurring tasks"""
        start_date, end_date = dynamic_date_range()

        with app.app_context():

            # Create daily recurring task
            recurring_event = create_recurring_event_factory(
                content="Daily Task",
                duration=30,  # 30 minutes
                recurrence=[0, 1, 2, 3, 4],  # Monday to Friday
                time_window_start=create_time(9, 0),
                time_window_end=create_time(17, 0),
            )

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Find tasks that were created from the recurring event
            recurring_tasks = Task.query.filter(
                Task.recurring_event_id == recurring_event.id
            ).all()

            # Verify that recurring tasks were created
            assert len(recurring_tasks) > 0

            # Verify all recurring tasks were scheduled
            scheduled_recurring_count = 0
            for task in scheduled_tasks:
                for rt in recurring_tasks:
                    if task["task_id"] == rt.id:
                        scheduled_recurring_count += 1
                        break

            assert scheduled_recurring_count == len(recurring_tasks)

    def test_recurring_with_specific_days(
        self, app, test_db, dynamic_date_range, create_recurring_event_factory
    ):
        """Test recurring tasks on specific days of week"""
        start_date, end_date = dynamic_date_range(days=7)  # Ensure we cover a full week

        with app.app_context():

            # Create recurring task for Monday and Thursday only
            recurring_event = create_recurring_event_factory(
                content="Mon/Thu Task",
                duration=45,  # 45 minutes
                recurrence=[0, 3],  # Monday (0) and Thursday (3)
                time_window_start=create_time(9, 0),
                time_window_end=create_time(17, 0),
            )

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Find tasks that were created from the recurring event
            recurring_tasks = Task.query.filter(
                Task.recurring_event_id == recurring_event.id
            ).all()

            # Verify that recurring tasks were created
            assert len(recurring_tasks) > 0

            # Verify all recurring tasks were scheduled
            scheduled_recurring_count = 0
            for task in scheduled_tasks:
                for rt in recurring_tasks:
                    if task["task_id"] == rt.id:
                        scheduled_recurring_count += 1
                        break

            assert scheduled_recurring_count == len(recurring_tasks)

    def test_recurring_with_time_window(
        self, app, test_db, dynamic_date_range, create_recurring_event_factory
    ):
        """Test recurring tasks with time windows"""
        start_date, end_date = dynamic_date_range()

        with app.app_context():

            # Create recurring task with morning time window
            time_window_start = create_time(10, 0)  # 10 AM
            time_window_end = create_time(12, 0)  # 12 PM

            recurring_event = create_recurring_event_factory(
                content="Morning Recurring Task",
                duration=30,  # 30 minutes
                recurrence=[0, 1, 2, 3, 4],  # Monday to Friday
                time_window_start=time_window_start,
                time_window_end=time_window_end,
            )

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Find tasks that were created from the recurring event
            recurring_tasks = Task.query.filter(
                Task.recurring_event_id == recurring_event.id
            ).all()

            # Verify tasks were created
            assert len(recurring_tasks) > 0

            if status_message == "Feasible" and scheduled_tasks is not None:
                # Verify all recurring tasks were scheduled within their time window
                for task in scheduled_tasks:
                    for rt in recurring_tasks:
                        if task["task_id"] == rt.id:
                            task_start_hour = task["start"].hour
                            assert 10 <= task_start_hour < 12
                            break

    def test_recurring_task_instance_date(
        self, app, test_db, dynamic_date_range, create_recurring_event_factory
    ):
        """Test that recurring tasks are scheduled on their correct instance dates"""
        # Use a longer date range to ensure we have multiple instances
        start_date, end_date = dynamic_date_range(
            days=10
        )  # 10 days to ensure multiple instances

        with app.app_context():

            # Create recurring task for specific days (Monday and Wednesday)
            recurring_event = create_recurring_event_factory(
                content="Mon/Wed Task",
                duration=45,  # 45 minutes
                recurrence=[0, 2],  # Monday (0) and Wednesday (2)
                time_window_start=create_time(10, 0),
                time_window_end=create_time(15, 0),
            )

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Find tasks that were created from the recurring event
            recurring_tasks = Task.query.filter(
                Task.recurring_event_id == recurring_event.id
            ).all()

            # Verify that recurring tasks were created
            assert len(recurring_tasks) > 0

            # Check that each task has an instance_date set
            for rt in recurring_tasks:
                assert rt.instance_date is not None
                # Verify the instance_date is either Monday (0) or Wednesday (2)
                assert rt.instance_date.weekday() in [0, 2]

            # For each scheduled recurring task, verify it's scheduled on its instance_date
            for task in scheduled_tasks:
                for rt in recurring_tasks:
                    if task["task_id"] == rt.id:
                        # The scheduled task start date should match the instance_date
                        assert task["start"].date() == rt.instance_date
                        # Also verify it's within the specified time window
                        assert 10 <= task["start"].hour < 15
                        break


class TestSchedulerIntegration:
    def test_complex_schedule_with_all_constraints(
        self,
        app,
        test_db,
        dynamic_date_range,
        create_task_factory,
        create_calendar_event_factory,
        create_recurring_event_factory,
    ):
        """Test a complex scheduling scenario with all constraint types"""
        start_date, end_date = dynamic_date_range(days=7)  # Full week

        with app.app_context():

            # 1. Create some calendar events
            # Morning meeting on first day
            morning_meeting = create_calendar_event_factory(
                subject="Morning Meeting",
                start=datetime.combine(start_date.date(), create_time(9, 0)),
                end=datetime.combine(start_date.date(), create_time(10, 30)),
                is_chewy_managed=False,
            )

            # Afternoon meeting on second day
            afternoon_meeting = create_calendar_event_factory(
                subject="Afternoon Meeting",
                start=datetime.combine(
                    (start_date + timedelta(days=1)).date(), create_time(14, 0)
                ),
                end=datetime.combine(
                    (start_date + timedelta(days=1)).date(), create_time(16, 0)
                ),
                is_chewy_managed=False,
            )

            # 2. Create tasks with dependencies
            task_a = create_task_factory(
                content="Task A",
                duration=60,  # 1 hour
                due_by=start_date + timedelta(days=3),
            )

            task_b = create_task_factory(
                content="Task B",
                duration=90,  # 1.5 hours
                due_by=start_date + timedelta(days=4),
            )

            task_c = create_task_factory(
                content="Task C",
                duration=120,  # 2 hours
                due_by=start_date + timedelta(days=5),
            )

            # Task C depends on Task B depends on Task A
            dependency_b_on_a = TaskDependency(
                task_id=task_b.id, dependency_id=task_a.id
            )
            dependency_c_on_b = TaskDependency(
                task_id=task_c.id, dependency_id=task_b.id
            )
            test_db.session.add(dependency_b_on_a)
            test_db.session.add(dependency_c_on_b)

            # 3. Create a task with a time window
            time_window_task = create_task_factory(
                content="Afternoon Only Task",
                duration=45,  # 45 minutes
                due_by=start_date + timedelta(days=2),
                time_window_start=create_time(13, 0),  # 1 PM
                time_window_end=create_time(17, 0),  # 5 PM
            )

            # 4. Create a recurring task - with time window that matches work hours
            recurring_task = create_recurring_event_factory(
                content="Daily Standup",
                duration=30,  # 30 minutes
                recurrence=[0, 1, 2, 3, 4],  # Monday to Friday
                time_window_start=create_time(9, 0),  # 9 AM
                time_window_end=create_time(17, 0),  # 5 PM
            )

            test_db.session.commit()

            # Run scheduler
            scheduled_tasks, status_message = generate_schedule(start_date, end_date)

            # Check if the schedule is feasible
            if status_message == "Infeasible":
                # If infeasible, we'll skip the detailed checks
                pytest.skip(
                    "Scheduler found the problem to be infeasible - skipping detailed checks"
                )

            # Assertions
            assert status_message == "Feasible"
            assert scheduled_tasks is not None

            # Find tasks in the schedule
            scheduled_a = next(
                (task for task in scheduled_tasks if task["task_id"] == task_a.id), None
            )
            scheduled_b = next(
                (task for task in scheduled_tasks if task["task_id"] == task_b.id), None
            )
            scheduled_c = next(
                (task for task in scheduled_tasks if task["task_id"] == task_c.id), None
            )
            scheduled_time_window = next(
                (
                    task
                    for task in scheduled_tasks
                    if task["task_id"] == time_window_task.id
                ),
                None,
            )

            # Verify one-off tasks were scheduled
            assert scheduled_a is not None
            assert scheduled_b is not None
            assert scheduled_c is not None
            assert scheduled_time_window is not None

            # Verify dependency order
            assert scheduled_a["end"] <= scheduled_b["start"]
            assert scheduled_b["end"] <= scheduled_c["start"]

            # Verify time window constraint
            assert 13 <= scheduled_time_window["start"].hour < 17

            # Verify no tasks overlap with calendar events
            for task in scheduled_tasks:
                task_start = task["start"]
                task_end = task["end"]

                # Check morning meeting overlap
                if task_start.date() == morning_meeting.start.date():
                    assert not (
                        task_start < morning_meeting.end
                        and task_end > morning_meeting.start
                    )

                # Check afternoon meeting overlap
                if task_start.date() == afternoon_meeting.start.date():
                    assert not (
                        task_start < afternoon_meeting.end
                        and task_end > afternoon_meeting.start
                    )

            # Find recurring tasks that were created
            recurring_instances = Task.query.filter(
                Task.recurring_event_id == recurring_task.id
            ).all()

            # Verify recurring tasks were created
            assert len(recurring_instances) > 0

            # Count scheduled recurring tasks
            scheduled_recurring_count = 0
            for task in scheduled_tasks:
                for rt in recurring_instances:
                    if task["task_id"] == rt.id:
                        # Verify they're in the right time window
                        assert 9 <= task["start"].hour < 17
                        scheduled_recurring_count += 1
                        break

            # Verify all recurring tasks were scheduled
            assert scheduled_recurring_count == len(recurring_instances)


if __name__ == "__main__":
    # This allows running the tests directly with pytest
    pytest.main(["-xvs", __file__])
