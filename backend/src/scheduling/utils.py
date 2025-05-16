from backend.extensions import db
from backend.models import CalendarEvent, RecurringEvent, Task, TaskDependency


def force_infeasibility(model):
    """
    Force a CP model to be infeasible by adding contradictory constraints.

    Used when a scheduling requirement cannot be satisfied and we need to
    explicitly make the model infeasible rather than letting it fail silently.

    Args:
        model: The CP-SAT model to make infeasible
        message: Description of why infeasibility is being forced

    Returns:
        A boolean variable that's constrained to be both 0 and 1
    """

    false_literal = model.NewBoolVar("false_literal_for_infeasibility")
    model.Add(false_literal == 1)  # Assert it's true
    model.Add(false_literal == 0)  # Assert it's false - creates contradiction
    return false_literal


def merge_overlapping_intervals(
    intervals: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """
    Merge a list of potentially overlapping time intervals into a minimal set of disjoint intervals.

    This is used to consolidate the "forbidden zones" like calendar events and non-working hours
    into an optimal set of non-overlapping intervals to improve solver performance.

    Args:
        intervals: List of (start, end) tuples representing time intervals

    Returns:
        List of merged non-overlapping (start, end) intervals covering the same time ranges

    Example:
        Input: [(1, 5), (3, 7), (8, 10), (9, 12)]
        Output: [(1, 7), (8, 12)]
    """
    if not intervals:
        return []

    # Sort intervals by start time
    intervals.sort(key=lambda x: x[0])

    merged_intervals = []
    current_start, current_end = intervals[0]

    for i in range(1, len(intervals)):
        next_start, next_end = intervals[i]
        if next_start <= current_end:  # Overlap or contiguous
            current_end = max(current_end, next_end)
        else:  # No overlap, start a new merged interval
            merged_intervals.append((current_start, current_end))
            current_start, current_end = next_start, next_end

    # Add the last processed interval
    merged_intervals.append((current_start, current_end))
    return merged_intervals


def get_calendar_events(start_date, end_date):
    """Retrieve non-Chewy-managed calendar events within the date range."""
    return (
        CalendarEvent.query.filter(
            CalendarEvent.end >= start_date,
            CalendarEvent.start <= end_date,
            CalendarEvent.is_chewy_managed == False,
        )
        .order_by(CalendarEvent.start)
        .all()
    )


def get_tasks(start_date, end_date):
    """Retrieve incomplete one-off tasks due before or on the end date."""
    return (
        Task.query.filter(
            Task.status != "completed",
            Task.due_by >= start_date,
        )
        .order_by(Task.due_by.asc().nullslast())
        .all()
    )


def reset_recurring_events(start_date, end_date):
    """Reset recurring tasks, expanding them into individual instances within the date range."""
    # get all recurring events
    # log the number of tasks before resetting
    recurring_events = RecurringEvent.query.all()
    for event in recurring_events:
        event.reset_tasks(start_date, end_date)
    # log the number of tasks after resetting


def get_task_dependencies():
    """Get all task dependencies from the database."""
    dependencies = {}
    for dep in db.session.query(TaskDependency).all():
        if dep.task_id not in dependencies:
            dependencies[dep.task_id] = []
        dependencies[dep.task_id].append(dep.dependency_id)
    return dependencies
