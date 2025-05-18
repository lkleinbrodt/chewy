import uuid
from datetime import datetime, time, timedelta

from flask import current_app
from ortools.sat.python import cp_model

from backend.extensions import create_logger, db
from backend.models import CalendarEvent, RecurringEvent, Task, TaskDependency
from backend.src.scheduling.or_task_wrapper import ORTaskWrapper
from backend.src.scheduling.utils import (
    force_infeasibility,
    get_calendar_events,
    get_task_dependencies,
    get_tasks,
    merge_overlapping_intervals,
    reset_recurring_events,
)

logger = create_logger(__name__, level="DEBUG")


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
                force_infeasibility(model)
            elif (
                or_task.due_by_min < or_task.duration_min
            ):  # Due too early for task duration
                logger.warning(
                    f"Task {or_task.id} due date {or_task.task_obj.due_by} is too early for its duration {or_task.duration_min}. Infeasible."
                )
                force_infeasibility(model)
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
                    force_infeasibility(model)
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
                force_infeasibility(model)
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
                force_infeasibility(model)
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
                    "start": scheduled_start_dt,
                    "end": scheduled_end_dt,
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

    # reset recurring tasks, expanding them into individual instances
    reset_recurring_events(start_date, end_date)
    tasks = get_tasks(start_date, end_date)
    # Get task dependencies
    task_dependencies = get_task_dependencies()

    # Run the scheduler with appropriate working hours from config
    result_schedule, status_message = schedule_tasks_with_or_tools(
        tasks,
        calendar_events,
        task_dependencies,
        start_date,
        end_date,
        current_app.config["WORK_START_HOUR"],
        current_app.config["WORK_END_HOUR"],
    )

    return result_schedule, status_message
