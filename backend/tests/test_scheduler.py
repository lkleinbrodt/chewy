import uuid
from datetime import datetime, time, timedelta

import pytz
from ortools.sat.python import cp_model

from backend import create_app
from backend.config import Config, TestingConfig
from backend.extensions import create_logger, db
from backend.models import CalendarEvent, RecurringEvent, Task, TaskDependency
from backend.src.scheduling.scheduler import generate_schedule


def create_test_environment(days=5):
    """
    Create a test environment with sample tasks and calendar events.

    Args:
        days (int): Number of days to include in the test period

    Returns:
        tuple: (start_date, end_date, created_tasks, created_events)
    """
    from backend.models import CalendarEvent, Task, TaskDependency

    # Clear existing test data
    RecurringEvent.query.delete()
    TaskDependency.query.delete()
    Task.query.delete()
    CalendarEvent.query.filter_by(is_chewy_managed=False).delete()

    # Create start and end dates
    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=days)

    # Create sample one-off tasks
    tasks = []
    task1 = Task(
        content="Important Task",
        duration=60,  # 1 hour
        task_type="one-off",
        due_by=start_date + timedelta(days=3),
    )
    db.session.add(task1)
    tasks.append(task1)

    task2 = Task(
        content="Urgent Task",
        duration=30,  # 30 minutes
        task_type="one-off",
        due_by=start_date + timedelta(days=1),
    )
    db.session.add(task2)
    tasks.append(task2)

    task3 = Task(
        content="Long Task (must be done after task1)",
        duration=120,  # 2 hours
        task_type="one-off",
        due_by=start_date + timedelta(days=5),
    )
    db.session.add(task3)
    tasks.append(task3)

    def create_time(hour, minute):
        return (
            datetime.now(pytz.UTC)
            .replace(hour=hour, minute=minute, second=0, microsecond=0)
            .time()
        )

    # Create a recurring task
    recurring_event = RecurringEvent(
        content="Daily Review",
        duration=45,  # 45 minutes
        recurrence=[0, 1, 2, 3, 4],
        time_window_start=create_time(0, 0),
        time_window_end=create_time(23, 0),
    )
    db.session.add(recurring_event)

    # Create some calendar events
    events = []
    # Morning meeting
    for day in range(days):
        event_date = start_date + timedelta(days=day)
        if event_date.weekday() not in [5, 6]:  # Skip weekends
            morning_meeting = CalendarEvent(
                subject=f"Morning Meeting Day {day+1}",
                start=datetime.combine(event_date.date(), create_time(9, 0)),
                end=datetime.combine(event_date.date(), create_time(10, 0)),
                is_chewy_managed=False,
            )
            db.session.add(morning_meeting)
            events.append(morning_meeting)

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
    events.append(long_meeting)

    db.session.commit()

    # Create a dependency: task3 depends on task1
    # Move this after the commit to ensure task IDs are available
    # dependency = TaskDependency(task_id=task3.id, dependency_id=task1.id)
    # db.session.add(dependency)
    db.session.commit()

    ### It's easier to just have everything in UTC, so update the config so work start/end makes sense
    # rightnow they are the utc times for my pacific time zone
    Config.WORK_START_HOUR = 9
    Config.WORK_END_HOUR = 17

    return start_date, end_date, tasks, events


def visualize_schedule(scheduled_tasks, start_date, end_date):
    """
    Visualize the schedule in a text-based format.

    Args:
        scheduled_tasks (list): List of scheduled task dictionaries
        start_date (datetime): Start date of the schedule
        end_date (datetime): End date of the schedule

    Returns:
        str: Text-based visualization of the schedule
    """
    from backend.models import CalendarEvent

    # Create a day-by-day schedule
    current_date = start_date.date()
    end_date = end_date.date()

    result = []

    while current_date <= end_date:
        day_str = current_date.strftime("%A, %Y-%m-%d")
        result.append(f"\n{day_str}")
        result.append("=" * len(day_str))

        # Get calendar events for this day
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())

        events = (
            CalendarEvent.query.filter(
                CalendarEvent.start <= day_end,
                CalendarEvent.end >= day_start,
                CalendarEvent.is_chewy_managed == False,
            )
            .order_by(CalendarEvent.start)
            .all()
        )

        # Get scheduled tasks for this day
        day_tasks = [
            task for task in scheduled_tasks if task["start"].date() == current_date
        ]

        # Sort all items by start time
        day_items = []

        for event in events:
            day_items.append(
                {
                    "type": "event",
                    "start": event.start,
                    "end": event.end,
                    "content": event.subject,
                }
            )

        for task in day_tasks:
            day_items.append(
                {
                    "type": "task",
                    "start": task["start"],
                    "end": task["end"],
                    "content": task["content"],
                    "task_type": task["task_type"],
                }
            )

        # Sort by start time
        day_items.sort(key=lambda x: x["start"])

        if not day_items:
            result.append("  No events or tasks scheduled")

        for item in day_items:
            start_str = item["start"].strftime("%H:%M")
            end_str = item["end"].strftime("%H:%M")

            if item["type"] == "event":
                result.append(f"  {start_str}-{end_str} | [EVENT] {item['content']}")
            else:
                task_type = (
                    "[RECURRING]"
                    if item["task_type"] == "recurring"
                    or item["task_type"] == "recurring_instance"
                    else "[ONE-OFF]"
                )
                result.append(
                    f"  {start_str}-{end_str} | {task_type} {item['content']}"
                )

        current_date += timedelta(days=1)

    return "\n".join(result)


def run_scheduler_test(days=5):
    """
    Run a test of the scheduler with sample data and visualize the results.

    Args:
        days (int): Number of days to include in the test period

    Returns:
        tuple: (scheduled_tasks, visualization)
    """
    # Create test environment
    start_date, end_date, tasks, events = create_test_environment(days)

    # Run scheduler
    scheduled_tasks, status_message = generate_schedule(start_date, end_date)
    if scheduled_tasks is None:
        print(f"No schedule found: {status_message}")
        return None, None

    # Visualize results
    visualization = visualize_schedule(scheduled_tasks, start_date, end_date)

    print("\nSCHEDULER TEST RESULTS")
    print("=====================")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Tasks created: {len(tasks)}")
    print(f"Events created: {len(events)}")
    print(f"Tasks scheduled: {len(scheduled_tasks)}")
    print(scheduled_tasks)
    print("\nSCHEDULE VISUALIZATION:")
    print(visualization)

    return scheduled_tasks, visualization


if __name__ == "__main__":
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        run_scheduler_test()
