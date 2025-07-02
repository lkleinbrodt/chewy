from datetime import datetime, timedelta

from backend.models import Task


def pre_schedule_validation(tasks_to_schedule: list[Task], period_start_dt: datetime):
    """Performs initial validation on tasks before sending them to the solver."""
    failed_tasks = []
    valid_tasks = []

    for task in tasks_to_schedule:
        if task.due_by and task.due_by < period_start_dt:
            failed_tasks.append({"task": task, "reason": "Task was due in the past."})
            continue

        if task.time_window_start and task.time_window_end:
            start_dt = datetime.combine(datetime.min, task.time_window_start)
            end_dt = datetime.combine(datetime.min, task.time_window_end)
            if start_dt >= end_dt:
                window_duration = (
                    datetime.combine(
                        datetime.min + timedelta(days=1), task.time_window_end
                    )
                    - start_dt
                ).total_seconds() / 60
            else:
                window_duration = (end_dt - start_dt).total_seconds() / 60

            if task.duration > window_duration:
                failed_tasks.append(
                    {
                        "task": task,
                        "reason": f"Task duration ({task.duration} mins) is longer than its time window ({int(window_duration)} mins).",
                    }
                )
                continue

        valid_tasks.append(task)

    return valid_tasks, failed_tasks


def get_task_dependency_ids(task):
    """Return a list of dependency IDs for a given Task object."""
    if hasattr(task, "dependencies_assoc") and task.dependencies_assoc:
        return [assoc.dependency_id for assoc in task.dependencies_assoc]
    return []


def _format_task_display_name(task: Task) -> str:
    """Format task name for display, including instance date for recurring tasks."""
    if task.recurring_event_id and task.instance_date:
        # For recurring tasks, just include the content - let frontend handle date formatting
        return task.content
    return task.content


def analyze_unscheduled_tasks(
    unscheduled_tasks: list[Task],
    all_db_tasks: list[Task],
    failed_dependency_ids: set[str],
):
    """Analyzes tasks that the solver failed to schedule."""
    analysis_results = []
    tasks_to_check = unscheduled_tasks[:]

    # Iteratively find all dependency-related failures
    while True:
        newly_failed_count = 0
        remaining_tasks = []
        for task in tasks_to_check:
            is_failed = False
            dep_ids = get_task_dependency_ids(task)
            if dep_ids:
                failed_deps = [
                    dep_id for dep_id in dep_ids if dep_id in failed_dependency_ids
                ]
                if failed_deps:
                    dep_tasks = [t for t in all_db_tasks if t.id in failed_deps]
                    dep_names = ", ".join(
                        [f"'{_format_task_display_name(t)}'" for t in dep_tasks]
                    )
                    analysis_results.append(
                        {
                            "task": task,
                            "reason": f"Blocked by an unschedulable dependency: {dep_names}.",
                        }
                    )
                    failed_dependency_ids.add(task.id)
                    newly_failed_count += 1
                    is_failed = True
            if not is_failed:
                remaining_tasks.append(task)

        tasks_to_check = remaining_tasks
        if newly_failed_count == 0:
            break

    # For any remaining tasks, assign a generic resource conflict reason
    for task in remaining_tasks:
        analysis_results.append(
            {
                "task": task,
                "reason": "Could not find an available time slot due to conflicts with other events or tasks.",
            }
        )

    return analysis_results
