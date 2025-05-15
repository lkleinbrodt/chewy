import uuid
from datetime import datetime, time, timedelta

from ortools.sat.python import cp_model

from backend.config import Config
from backend.extensions import create_logger, db
from backend.models import CalendarEvent, Task, TaskDependency

logger = create_logger(__name__, level="DEBUG")


def force_infeasibility(model, message):
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
    logger.debug(f"Forcing model infeasibility: {message}")
    false_literal = model.NewBoolVar("false_literal_for_infeasibility")
    model.Add(false_literal == 1)  # Assert it's true
    model.Add(false_literal == 0)  # Assert it's false - creates contradiction
    return false_literal


class ORTaskWrapper:
    """
    Wrapper for Task objects to integrate with OR-Tools constraint solver.

    Converts task properties into constraint variables with appropriate domains,
    handling task start/end times, durations, due dates, and time windows.
    """

    def __init__(self, task_obj, model, period_start_dt, period_end_dt_minutes):
        """
        Initialize task variables for the constraint solver.

        Args:
            task_obj: The Task DB object
            model: OR-Tools CP model
            period_start_dt: Start datetime of scheduling period
            period_end_dt_minutes: End of scheduling horizon in minutes relative to period_start_dt
        """
        self.task_obj = task_obj
        self.id = task_obj.id
        self.duration_min = task_obj.duration
        if hasattr(task_obj, "original_master_task_id"):
            self.original_master_task_id = task_obj.original_master_task_id
        else:
            self.original_master_task_id = None

        logger.debug(f"Creating task variables for '{task_obj.content}' ({self.id})")
        logger.debug(f"  Duration: {self.duration_min} minutes")
        logger.debug(f"  Horizon: {period_end_dt_minutes} minutes")

        # Define domains for start and end variables relative to period_start_dt
        min_s = 0  # Earliest possible start: beginning of period
        max_s = (
            period_end_dt_minutes - self.duration_min
        )  # Latest possible start: end - duration

        # Handle case where task is longer than scheduling window
        if min_s > max_s:
            logger.warning(
                f"Task {self.id} is longer than scheduling window. Infeasible."
            )
            # Create unsatisfiable variable domain (min > max)
            self.start_var = model.NewIntVar(1, 0, f"start_{self.id}")
            self.end_var = model.NewIntVar(1, 0, f"end_{self.id}")
        else:
            self.start_var = model.NewIntVar(min_s, max_s, f"start_{self.id}")
            self.end_var = model.NewIntVar(
                min_s + self.duration_min, period_end_dt_minutes, f"end_{self.id}"
            )

        # Create interval variable (implicitly ensures end = start + duration)
        self.interval_var = model.NewIntervalVar(
            self.start_var, self.duration_min, self.end_var, f"interval_{self.id}"
        )

        # Process due date constraints
        self.due_by_min = None
        if task_obj.due_by:
            if task_obj.due_by < period_start_dt:
                # Task is due before period starts - mark as infeasible
                logger.warning(
                    f"Task {self.id} is due before scheduling period. Infeasible."
                )
                self.due_by_min = (
                    -1
                )  # Will conflict with end_var >= 0 domain constraint
            else:
                # Convert due date to minutes from period start
                self.due_by_min = int(
                    (task_obj.due_by - period_start_dt).total_seconds() / 60
                )
                logger.debug(f"  Due by: {self.due_by_min} minutes")

                if self.due_by_min < self.duration_min:
                    logger.debug("  Warning: Due time is earlier than task duration")
        else:
            logger.debug("  No due date constraint")

        # Store time window constraints (if any)
        self.time_window_start_time = task_obj.time_window_start  # datetime.time
        self.time_window_end_time = task_obj.time_window_end  # datetime.time
        self.instance_date = getattr(task_obj, "instance_date", None)  # datetime.date


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


def schedule_tasks_with_or_tools(
    tasks_to_schedule: list,  # List of Task DB objects (pre-expanded)
    calendar_events: list,  # List of CalendarEvent DB objects
    task_dependencies_map: dict,  # task_id -> list of dependency_ids (strings)
    period_start_dt: datetime,
    period_end_dt: datetime,
    work_start_hour: int,
    work_end_hour: int,
):
    """
    Schedule tasks using Google OR-Tools constraint solver.

    Creates an optimal schedule that respects:
    - Task time windows and durations
    - Calendar events (no scheduling during events)
    - Task dependencies (one task must complete before another starts)
    - Work hours (only schedule during work hours on weekdays)
    - Due dates (tasks must complete before their due date)

    All times are converted to minutes relative to period_start_dt for the solver.
    """
    model = cp_model.CpModel()

    # --- 1. Setup Time Horizon ---
    if period_start_dt >= period_end_dt:
        raise ValueError(
            f"Error: Period start must be before period end. Got start: {period_start_dt} and end: {period_end_dt}"
        )

    logger.debug(f"Period Start: {period_start_dt}")
    logger.debug(f"Period End: {period_end_dt}")
    logger.debug(f"Work Hours: {work_start_hour}:00 - {work_end_hour}:00")

    # Calculate horizon length in minutes (all times will be relative to period_start_dt)
    horizon_end_min = int((period_end_dt - period_start_dt).total_seconds() / 60)
    logger.debug(f"Schedule horizon: {horizon_end_min} minutes")

    if horizon_end_min <= 0:
        raise ValueError(
            f"Error: Scheduling period has zero or negative duration. Got start: {period_start_dt} and end: {period_end_dt}"
        )

    # --- 2. Create Task Variables ---
    or_tasks_map = {}  # Maps task_id -> ORTaskWrapper
    for task_db_obj in tasks_to_schedule:
        or_task = ORTaskWrapper(task_db_obj, model, period_start_dt, horizon_end_min)
        or_tasks_map[task_db_obj.id] = or_task

    # Extract interval variables for all tasks
    all_task_interval_vars = [t.interval_var for t in or_tasks_map.values()]

    # --- 3. Build Forbidden Time Segments ---
    # These represent times when tasks cannot be scheduled (events, non-work hours, weekends)
    raw_fixed_segments = []  # List of (start_min_rel, end_min_rel) tuples

    # Add calendar events as forbidden segments
    logger.debug(f"Processing {len(calendar_events)} calendar events")
    for event in calendar_events:
        # Ensure event times are naive or consistent with period_start_dt
        event_s_abs = (
            event.start.replace(tzinfo=None) if event.start.tzinfo else event.start
        )
        event_e_abs = event.end.replace(tzinfo=None) if event.end.tzinfo else event.end

        # Clip event to the scheduling period
        event_s_clipped = max(event_s_abs, period_start_dt)
        event_e_clipped = min(event_e_abs, period_end_dt)

        if event_s_clipped < event_e_clipped:  # Event overlaps with the period
            event_start_min_rel = int(
                (event_s_clipped - period_start_dt).total_seconds() / 60
            )
            event_end_min_rel = int(
                (event_e_clipped - period_start_dt).total_seconds() / 60
            )
            event_duration_min = event_end_min_rel - event_start_min_rel

            if event_duration_min > 0:
                raw_fixed_segments.append((event_start_min_rel, event_end_min_rel))
                logger.debug(
                    f"Added calendar segment: {event.subject} ({event_start_min_rel}-{event_end_min_rel})"
                )

    # Add non-working hours and weekends as forbidden segments
    current_iter_dt = period_start_dt
    logger.debug("Processing non-working hours and weekends")

    while current_iter_dt.date() <= period_end_dt.date():
        day_start_abs = datetime.combine(current_iter_dt.date(), time.min)
        day_end_abs = datetime.combine(current_iter_dt.date(), time.max)

        # Clip this day to the scheduling period
        iter_day_actual_start = max(day_start_abs, period_start_dt)
        iter_day_actual_end = min(day_end_abs, period_end_dt)

        if iter_day_actual_start >= iter_day_actual_end:
            current_iter_dt += timedelta(days=1)
            continue

        # Handle weekend days (entire day is forbidden)
        if current_iter_dt.weekday() >= 5:  # Saturday or Sunday (0=Mon, 6=Sun)
            start_m = int(
                (iter_day_actual_start - period_start_dt).total_seconds() / 60
            )
            end_m = int((iter_day_actual_end - period_start_dt).total_seconds() / 60)
            if end_m > start_m:
                raw_fixed_segments.append((start_m, end_m))
                logger.debug(
                    f"Added weekend segment: {current_iter_dt.strftime('%Y-%m-%d')}"
                )
        else:  # Weekday - add before and after work hours
            # Time before work starts
            work_starts_dt_on_day = datetime.combine(
                current_iter_dt.date(), time(work_start_hour, 0)
            )
            non_work_s1 = iter_day_actual_start
            non_work_e1 = min(work_starts_dt_on_day, iter_day_actual_end)
            if non_work_e1 > non_work_s1:
                start_m = int((non_work_s1 - period_start_dt).total_seconds() / 60)
                end_m = int((non_work_e1 - period_start_dt).total_seconds() / 60)
                if end_m > start_m:
                    raw_fixed_segments.append((start_m, end_m))

            # Time after work ends
            work_ends_dt_on_day = datetime.combine(
                current_iter_dt.date(), time(work_end_hour, 0)
            )
            non_work_s2 = max(work_ends_dt_on_day, iter_day_actual_start)
            non_work_e2 = iter_day_actual_end
            if non_work_e2 > non_work_s2:
                start_m = int((non_work_s2 - period_start_dt).total_seconds() / 60)
                end_m = int((non_work_e2 - period_start_dt).total_seconds() / 60)
                if end_m > start_m:
                    raw_fixed_segments.append((start_m, end_m))

        current_iter_dt += timedelta(days=1)

    # Merge overlapping segments for efficiency
    merged_forbidden_segments = merge_overlapping_intervals(raw_fixed_segments)
    logger.debug(
        f"Created {len(merged_forbidden_segments)} merged forbidden time segments"
    )

    # Create OR-Tools interval variables for forbidden zones
    forbidden_zone_intervals = []
    for i, (start_seg, end_seg) in enumerate(merged_forbidden_segments):
        duration_seg = end_seg - start_seg
        if duration_seg > 0:
            interval = model.NewFixedSizeIntervalVar(
                start_seg, duration_seg, f"forbidden_zone_{i}"
            )
            forbidden_zone_intervals.append(interval)

    # --- 4. Add NoOverlap Constraint ---
    # Tasks cannot overlap with each other OR with any forbidden zone
    all_intervals_to_check = all_task_interval_vars + forbidden_zone_intervals
    if all_intervals_to_check:  # Avoid error if list is empty
        model.AddNoOverlap(all_intervals_to_check)
        logger.debug(
            f"Added NoOverlap constraint with {len(all_intervals_to_check)} intervals"
        )

    # --- 5. Due Date Constraints ---
    for or_task in or_tasks_map.values():
        if or_task.due_by_min is not None:
            if or_task.due_by_min < 0:  # Due before period starts
                logger.warning(
                    f"Task {or_task.id} is due before the scheduling period. Infeasible."
                )
                force_infeasibility(model, "Task is due before the scheduling period.")
            elif (
                or_task.due_by_min < or_task.duration_min
            ):  # Due too early for task duration
                logger.warning(
                    f"Task {or_task.id} due date {or_task.task_obj.due_by} is too early for its duration {or_task.duration_min}. Infeasible."
                )
                force_infeasibility(
                    model, "Task due date is too early for its duration."
                )
            else:
                model.Add(or_task.end_var <= or_task.due_by_min)

    # --- 6. Dependency Constraints ---
    # If task A depends on task B, A can only start after B ends
    for task_id, dep_ids in task_dependencies_map.items():
        if task_id not in or_tasks_map:
            continue
        task_A_or_obj = or_tasks_map[task_id]
        for dep_id in dep_ids:
            if dep_id not in or_tasks_map:
                continue  # Dependency might be completed or not in this batch
            task_B_or_obj = or_tasks_map[dep_id]
            model.Add(task_A_or_obj.start_var >= task_B_or_obj.end_var)

    # --- 7. Task-Specific Time Window Constraints ---
    for or_task in or_tasks_map.values():
        if or_task.time_window_start_time and or_task.time_window_end_time:
            tw_start_t = or_task.time_window_start_time
            tw_end_t = or_task.time_window_end_time
            possible_windows_for_task = []  # (start_min_rel, end_min_rel) tuples

            # Determine which days to check for this task
            days_to_check = []
            if (
                or_task.instance_date
            ):  # Task tied to a specific date (recurring instance)
                # Check if this instance_date is within the scheduling period and is a weekday
                if (
                    or_task.instance_date >= period_start_dt.date()
                    and or_task.instance_date <= period_end_dt.date()
                    and or_task.instance_date.weekday() < 5
                ):
                    days_to_check.append(or_task.instance_date)
                else:
                    # This specific instance date is invalid (weekend, outside period)
                    logger.warning(
                        f"Task {or_task.id} instance_date {or_task.instance_date} invalid for time window. Infeasible."
                    )
                    force_infeasibility(
                        model, "Task instance date is invalid for time window."
                    )
                    continue  # Next task
            else:  # Generic task with a daily repeating time window
                # Check all weekdays in the period
                d_iter = period_start_dt.date()
                while d_iter <= period_end_dt.date():
                    if d_iter.weekday() < 5:  # Weekdays only
                        days_to_check.append(d_iter)
                    d_iter += timedelta(days=1)

            # Handle edge cases with days_to_check
            if not days_to_check and or_task.instance_date:
                # Specific instance date was invalid - already handled above
                pass
            elif not days_to_check:  # No weekdays in period for generic windowed task
                logger.warning(
                    f"Task {or_task.id} has time window, but no weekdays in scheduling period. Infeasible."
                )
                force_infeasibility(
                    model, "Task has time window, but no weekdays in scheduling period."
                )
                continue

            # For each valid day, calculate possible time windows
            for day_date in days_to_check:
                # Calculate absolute start/end of the window on this specific day
                abs_win_s_dt = datetime.combine(day_date, tw_start_t)
                abs_win_e_dt = datetime.combine(day_date, tw_end_t)

                # Handle overnight windows (e.g., 10 PM to 2 AM)
                if abs_win_e_dt < abs_win_s_dt:
                    abs_win_e_dt += timedelta(days=1)

                # Clip window to scheduling period
                win_s_clipped_abs = max(abs_win_s_dt, period_start_dt)
                win_e_clipped_abs = min(abs_win_e_dt, period_end_dt)

                # Ensure window is within working hours
                day_work_s_abs = datetime.combine(day_date, time(work_start_hour, 0))
                day_work_e_abs = datetime.combine(day_date, time(work_end_hour, 0))
                win_s_final_abs = max(win_s_clipped_abs, day_work_s_abs)

                # Handle windows crossing midnight
                if abs_win_e_dt.date() > day_date:
                    next_day_date = abs_win_e_dt.date()
                    if next_day_date.weekday() < 5:  # If next day is a weekday
                        next_day_work_s_abs = datetime.combine(
                            next_day_date, time(work_start_hour, 0)
                        )
                        next_day_work_e_abs = datetime.combine(
                            next_day_date, time(work_end_hour, 0)
                        )
                        win_e_final_abs = min(win_e_clipped_abs, next_day_work_e_abs)
                        # Ensure start time is respected if window starts on next day
                        win_s_final_abs = max(
                            win_s_final_abs,
                            (
                                next_day_work_s_abs
                                if win_s_final_abs.date() > day_date
                                else win_s_final_abs
                            ),
                        )
                    else:  # Ends on weekend, clip to end of current day's work hours
                        win_e_final_abs = min(win_e_clipped_abs, day_work_e_abs)
                else:  # Window ends on the same day
                    win_e_final_abs = min(win_e_clipped_abs, day_work_e_abs)

                # Add window if it's valid and long enough for the task
                if win_e_final_abs > win_s_final_abs:
                    duration_of_this_window_slot = (
                        win_e_final_abs - win_s_final_abs
                    ).total_seconds() / 60
                    if duration_of_this_window_slot >= or_task.duration_min:
                        start_min_rel = int(
                            (win_s_final_abs - period_start_dt).total_seconds() / 60
                        )
                        end_min_rel = int(
                            (win_e_final_abs - period_start_dt).total_seconds() / 60
                        )
                        possible_windows_for_task.append((start_min_rel, end_min_rel))

            # Handle case where no valid windows were found
            if not possible_windows_for_task:
                logger.warning(
                    f"Task {or_task.id} ({or_task.task_obj.content}) has a time window but no valid slots found. Infeasible."
                )
                force_infeasibility(
                    model, "Task has a time window but no valid slots found."
                )
                continue

            # Task must be scheduled in ONE of these valid windows
            bool_vars_for_windows = []
            for i, (w_start, w_end) in enumerate(possible_windows_for_task):
                b = model.NewBoolVar(f"b_{or_task.id}_in_win_{i}")
                bool_vars_for_windows.append(b)
                # If this window is chosen (b is true):
                # task_start >= w_start AND task_end <= w_end
                model.Add(or_task.start_var >= w_start).OnlyEnforceIf(b)
                model.Add(or_task.end_var <= w_end).OnlyEnforceIf(b)

            # Ensure task is scheduled in exactly one window
            if bool_vars_for_windows:
                model.Add(sum(bool_vars_for_windows) == 1)

    # --- 8. Solve the Model ---
    logger.debug("Solving scheduling model...")
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False  # Enable progress logging
    solver.parameters.max_time_in_seconds = 30.0  # Set timeout limit

    status = solver.Solve(model)

    # --- 9. Process Results ---
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        scheduled_tasks_result = []
        for task_id, or_task in or_tasks_map.items():
            start_val_min = solver.Value(or_task.start_var)
            scheduled_start_dt = period_start_dt + timedelta(minutes=start_val_min)
            scheduled_end_dt = scheduled_start_dt + timedelta(
                minutes=or_task.duration_min
            )

            scheduled_tasks_result.append(
                {
                    "task_id": task_id,
                    "content": or_task.task_obj.content,
                    "start": scheduled_start_dt,
                    "end": scheduled_end_dt,
                    "task_type": or_task.task_obj.task_type,
                    "original_master_task_id": or_task.original_master_task_id,
                }
            )

        # Sort by start time for readability
        scheduled_tasks_result.sort(key=lambda x: x["start"])
        logger.debug(f"Successfully scheduled {len(scheduled_tasks_result)} tasks")
        return scheduled_tasks_result, "Feasible"
    elif status == cp_model.INFEASIBLE:
        logger.warning("Solver found the problem to be INFEASIBLE.")
        return None, "Infeasible"
    else:
        logger.warning(f"Solver finished with status: {solver.StatusName(status)}")
        return None, f"Solver status: {solver.StatusName(status)}"


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


def get_one_off_tasks(start_date):
    """Retrieve incomplete one-off tasks due before or on the end date."""
    return (
        Task.query.filter(
            Task.task_type == "one-off",
            Task.is_completed == False,
            # db.or_(Task.due_by >= start_date, Task.due_by == None),
        )
        .order_by(Task.due_by.asc().nullslast())
        .all()
    )


def get_recurring_tasks():
    """Retrieve active recurring tasks."""
    return Task.query.filter(
        Task.task_type == "recurring", Task.is_active == True
    ).all()


def expand_daily_recurring_task(task, start_date, end_date):
    """Convert a daily recurring task into individual task instances within the date range."""
    day_iterator = start_date.date()
    daily_tasks = []
    while day_iterator < end_date.date():
        # skip weekends
        if day_iterator.weekday() < 5:
            effective_due_date_for_window = day_iterator
            if task.time_window_end < task.time_window_start:
                # overnight task
                effective_due_date_for_window += timedelta(days=1)
            instance_due_by = datetime.combine(
                effective_due_date_for_window, task.time_window_end
            )

            instance_task = Task(
                id=str(uuid.uuid4()),
                content=task.content,
                duration=task.duration,
                task_type="recurring_instance",
                due_by=instance_due_by,
                time_window_start=task.time_window_start,
                time_window_end=task.time_window_end,
                is_active=True,
            )
            # Monkey-patch attributes needed for scheduling logic
            # Ideally, these would be part of the Task model if you persist instances
            # or use a dedicated scheduler-internal class.
            instance_task.instance_date = (
                day_iterator  # The specific date this instance is for
            )
            instance_task.original_master_task_id = (
                task.id
            )  # ID of the original Task template

            daily_tasks.append(instance_task)
        day_iterator += timedelta(days=1)
    return daily_tasks


def expand_weekly_recurring_task(task, start_date: datetime, end_date: datetime):
    days = task.recurrence["days"]
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    # no weekends
    days_of_week = [weekdays.index(day) for day in days]
    days_of_week = [day for day in days_of_week if day < 5]

    weekly_tasks = []
    day_iterator = start_date.date()
    while day_iterator < end_date.date():
        if day_iterator.weekday() in days_of_week:
            effective_due_date_for_window = day_iterator
            if task.time_window_end < task.time_window_start:
                # overnight task
                effective_due_date_for_window += timedelta(days=1)
            instance_due_by = datetime.combine(
                effective_due_date_for_window, task.time_window_end
            )
            instance_task = Task(
                id=str(uuid.uuid4()),
                content=task.content,
                duration=task.duration,
                task_type="recurring_instance",
                due_by=instance_due_by,
                time_window_start=task.time_window_start,
                time_window_end=task.time_window_end,
                is_active=True,
            )
            instance_task.instance_date = day_iterator
            instance_task.original_master_task_id = task.id
            weekly_tasks.append(instance_task)
        day_iterator += timedelta(days=1)
    return weekly_tasks


def expand_recurring_tasks(recurring_tasks, start_date, end_date):
    """Convert recurring tasks into individual task instances within the date range."""
    individual_recurring_tasks = []

    for task in recurring_tasks:
        assert task.due_by is None, "Recurring tasks must not have a due date"
        assert (
            task.time_window_start is not None
        ), "Recurring tasks must have a time window"

        if task.recurrence["type"] == "daily":
            individual_recurring_tasks.extend(
                expand_daily_recurring_task(task, start_date, end_date)
            )
        elif task.recurrence["type"] == "weekly":
            individual_recurring_tasks.extend(
                expand_weekly_recurring_task(task, start_date, end_date)
            )
        else:
            raise ValueError(f"Unsupported recurrence pattern: {task.recurrence}")

    return individual_recurring_tasks


def get_task_dependencies():
    """Get all task dependencies from the database."""
    dependencies = {}
    for dep in db.session.query(TaskDependency).all():
        if dep.task_id not in dependencies:
            dependencies[dep.task_id] = []
        dependencies[dep.task_id].append(dep.dependency_id)
    return dependencies


def generate_schedule(start_date, end_date):
    """
    Generate an optimal schedule for tasks within the given time period.

    This is the main entry point for the scheduling system. It fetches relevant
    calendar events and tasks from the database, expands recurring tasks into
    individual instances, and then uses the OR-Tools solver to create an optimal
    schedule respecting all constraints.

    Args:
        start_date: Datetime defining the start of the scheduling period
        end_date: Datetime defining the end of the scheduling period

    Returns:
        tuple: (scheduled_tasks, status_message)
            - scheduled_tasks: List of scheduled task objects with start/end times,
              or None if scheduling was infeasible
            - status_message: String indicating success or reason for failure
    """
    # Fetch relevant data from database
    calendar_events = get_calendar_events(start_date, end_date)
    one_off_tasks = get_one_off_tasks(start_date)
    recurring_tasks = get_recurring_tasks()

    # Expand recurring tasks into individual instances
    individual_recurring_tasks = expand_recurring_tasks(
        recurring_tasks, start_date, end_date
    )

    # Combine one-off and recurring tasks
    tasks = one_off_tasks + individual_recurring_tasks

    # Get task dependencies
    task_dependencies = get_task_dependencies()

    # Run the scheduler with appropriate working hours from config
    result_schedule, status_message = schedule_tasks_with_or_tools(
        tasks,
        calendar_events,
        task_dependencies,
        start_date,
        end_date,
        Config.WORK_START_HOUR,
        Config.WORK_END_HOUR,
    )

    return result_schedule, status_message
