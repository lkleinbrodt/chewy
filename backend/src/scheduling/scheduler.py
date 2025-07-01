import uuid
from datetime import datetime, time, timedelta
from typing import Optional

from flask import current_app
from ortools.sat.python import cp_model

from backend.extensions import create_logger, db
from backend.models.calendar import CalendarEvent
from backend.models.task import RecurringEvent, Task, TaskDependency
from backend.src.scheduling.failure_analyzer import (
    analyze_unscheduled_tasks,
    pre_schedule_validation,
)
from backend.src.scheduling.objectives import SchedulerObjectives
from backend.src.scheduling.or_task_wrapper import ORTaskWrapper
from backend.src.scheduling.utils import (
    force_infeasibility,
    get_calendar_events,
    get_task_dependencies,
    get_tasks,
    merge_overlapping_intervals,
    reset_recurring_events,
)

logger = create_logger(__name__, level="INFO")


def _validate_scheduling_period(period_start_dt, period_end_dt):
    """Validate the scheduling period and return the horizon end in minutes."""
    if period_start_dt >= period_end_dt:
        raise ValueError(
            f"Error: Period start must be before period end. Got start: {period_start_dt} and end: {period_end_dt}"
        )

    logger.debug(f"Period Start: {period_start_dt}")
    logger.debug(f"Period End: {period_end_dt}")

    # Calculate horizon length in minutes (all times will be relative to period_start_dt)
    horizon_end_min = int((period_end_dt - period_start_dt).total_seconds() / 60)
    logger.debug(f"Schedule horizon: {horizon_end_min} minutes")

    if horizon_end_min <= 0:
        raise ValueError(
            f"Error: Scheduling period has zero or negative duration. Got start: {period_start_dt} and end: {period_end_dt}"
        )

    return horizon_end_min


def _create_task_variables(model, tasks_to_schedule, period_start_dt, horizon_end_min):
    """Create OR-Tools variables for all tasks and return the mapping."""
    or_tasks_map = {}  # Maps task_id -> ORTaskWrapper
    for task_db_obj in tasks_to_schedule:
        or_task = ORTaskWrapper(task_db_obj, model, period_start_dt, horizon_end_min)
        or_tasks_map[task_db_obj.id] = or_task

    logger.debug(f"Created variables for {len(or_tasks_map)} tasks")
    return or_tasks_map


def _build_calendar_event_segments(calendar_events, period_start_dt, period_end_dt):
    """Create time segments for calendar events."""
    raw_fixed_segments = []  # List of (start_min_rel, end_min_rel) tuples

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

    return raw_fixed_segments


def _build_non_work_hour_segments(
    period_start_dt, period_end_dt, work_start_hour, work_end_hour
):
    """Create time segments for non-working hours and weekends."""
    raw_fixed_segments = []
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

    return raw_fixed_segments


def _create_forbidden_intervals(model, merged_segments):
    """Create interval variables for forbidden time segments."""
    forbidden_zone_intervals = []
    for i, (start_seg, end_seg) in enumerate(merged_segments):
        duration_seg = end_seg - start_seg
        if duration_seg > 0:
            interval = model.NewFixedSizeIntervalVar(
                start_seg, duration_seg, f"forbidden_zone_{i}"
            )
            forbidden_zone_intervals.append(interval)

    logger.debug(f"Created {len(forbidden_zone_intervals)} forbidden zone intervals")
    return forbidden_zone_intervals


def _add_no_overlap_constraint(model, all_intervals):
    """Add constraint that tasks cannot overlap with each other or forbidden zones."""
    if all_intervals:  # Avoid error if list is empty
        model.AddNoOverlap(all_intervals)
        logger.debug(f"Added NoOverlap constraint with {len(all_intervals)} intervals")


def _add_due_date_constraints(model, or_tasks_map):
    """Add constraints for task due dates."""
    for or_task in or_tasks_map.values():
        if or_task.due_by_min is not None:
            # This constraint is only active if the task is performed.
            model.Add(or_task.end_var <= or_task.due_by_min).OnlyEnforceIf(
                or_task.is_performed_bool
            )


def _add_dependency_constraints(model, or_tasks_map, task_dependencies_map):
    """Add constraints for task dependencies."""
    for task_id, dep_ids in task_dependencies_map.items():
        if task_id not in or_tasks_map:
            continue
        task_A_or_obj = or_tasks_map[task_id]
        for dep_id in dep_ids:
            if dep_id not in or_tasks_map:
                continue

            task_B_or_obj = or_tasks_map[dep_id]

            # If task A is performed, its dependency B must also be performed.
            model.AddImplication(
                task_A_or_obj.is_performed_bool, task_B_or_obj.is_performed_bool
            )

            # And task A must start after B ends.
            model.Add(task_A_or_obj.start_var >= task_B_or_obj.end_var).OnlyEnforceIf(
                [task_A_or_obj.is_performed_bool, task_B_or_obj.is_performed_bool]
            )


def _add_instance_date_constraints(
    model,
    or_tasks_map,
    period_start_dt,
    period_end_dt,
    work_start_hour,
    work_end_hour,
    horizon_end_min,
):
    """Add constraints for tasks tied to specific dates."""
    for or_task in or_tasks_map.values():
        if or_task.instance_date:
            # Check if instance_date is within scheduling period and is a weekday
            if (
                or_task.instance_date >= period_start_dt.date()
                and or_task.instance_date <= period_end_dt.date()
                and or_task.instance_date.weekday() < 5
            ):
                # Calculate the start and end of work hours on this specific day
                day_work_s_abs = datetime.combine(
                    or_task.instance_date, time(work_start_hour, 0)
                )
                day_work_e_abs = datetime.combine(
                    or_task.instance_date, time(work_end_hour, 0)
                )

                # Convert to minutes relative to period_start
                day_start_min = max(
                    0, int((day_work_s_abs - period_start_dt).total_seconds() / 60)
                )
                day_end_min = min(
                    horizon_end_min,
                    int((day_work_e_abs - period_start_dt).total_seconds() / 60),
                )

                # Check if there's enough time in this day for the task
                if day_end_min - day_start_min >= or_task.duration_min:
                    # The constraints for start/end time only apply IF the task is performed.
                    model.Add(or_task.start_var >= day_start_min).OnlyEnforceIf(
                        or_task.is_performed_bool
                    )
                    model.Add(or_task.end_var <= day_end_min).OnlyEnforceIf(
                        or_task.is_performed_bool
                    )
                else:
                    # If no valid window exists, this task can NEVER be performed.
                    model.Add(or_task.is_performed_bool == 0)
                    continue
            else:
                # Instance date is invalid (weekend or outside scheduling period)
                # This task can NEVER be performed.
                model.Add(or_task.is_performed_bool == 0)
                continue


def _get_days_to_check_for_task(or_task, period_start_dt, period_end_dt):
    """Determine which days to check for a task's time window."""
    days_to_check = []
    if or_task.instance_date:
        # We already enforced instance_date constraints above,
        # just reuse the instance_date here for time windows
        days_to_check.append(or_task.instance_date)
    else:
        # Generic task with a daily repeating time window
        # Check all weekdays in the period
        d_iter = period_start_dt.date()
        while d_iter <= period_end_dt.date():
            if d_iter.weekday() < 5:  # Weekdays only
                days_to_check.append(d_iter)
            d_iter += timedelta(days=1)

    return days_to_check


def _calculate_possible_windows(
    or_task,
    days_to_check,
    period_start_dt,
    period_end_dt,
    work_start_hour,
    work_end_hour,
):
    """Calculate possible time windows for a task on each valid day."""
    possible_windows_for_task = []  # (start_min_rel, end_min_rel) tuples
    tw_start_t = or_task.time_window_start_time
    tw_end_t = or_task.time_window_end_time

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

    return possible_windows_for_task


def _add_time_window_constraints(
    model, or_tasks_map, period_start_dt, period_end_dt, work_start_hour, work_end_hour
):
    """Add constraints for task-specific time windows."""
    for or_task in or_tasks_map.values():
        if or_task.time_window_start_time and or_task.time_window_end_time:
            # Determine which days to check for this task
            days_to_check = _get_days_to_check_for_task(
                or_task, period_start_dt, period_end_dt
            )

            # Handle edge cases with days_to_check
            if not days_to_check:  # No weekdays in period for generic windowed task
                logger.warning(
                    f"Task {or_task.id} has time window, but no weekdays in scheduling period. Infeasible."
                )
                force_infeasibility(model)
                continue

            # For each valid day, calculate possible time windows
            possible_windows_for_task = _calculate_possible_windows(
                or_task,
                days_to_check,
                period_start_dt,
                period_end_dt,
                work_start_hour,
                work_end_hour,
            )

            # Handle case where no valid windows were found
            if not possible_windows_for_task:
                # If no valid window exists, this task can NEVER be performed.
                model.Add(or_task.is_performed_bool == 0)
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

            # If the task is performed, it must be in exactly one of its valid windows.
            model.Add(sum(bool_vars_for_windows) == 1).OnlyEnforceIf(
                or_task.is_performed_bool
            )


def _build_objective_function(
    model: cp_model.CpModel,
    or_tasks_map: dict,
    period_start_dt: datetime,
    period_end_dt: datetime,
    work_start_hour: int,
    work_end_hour: int,
    horizon_end_min: int,
    objectives: SchedulerObjectives,
) -> Optional[cp_model.IntVar]:
    """Build the overall objective function to MINIMIZE total cost/penalty."""

    UNSCHEDULED_PENALTY_BASE = 1000000
    penalties = []
    for or_task in or_tasks_map.values():
        # Penalty is (base * priority) if the task is NOT performed.
        # .Not() is the negation of the boolean variable.
        penalty = or_task.priority * UNSCHEDULED_PENALTY_BASE
        penalties.append(or_task.is_performed_bool.Not() * penalty)

    total_penalty = sum(penalties)

    # Convert custom rewards (which we maximize) to costs (which we minimize)
    custom_reward_components = objectives.get_enabled_components()
    custom_costs = []
    for component in custom_reward_components:
        if not component.enabled:
            continue

        reward_var = component.calculate_reward(
            model,
            or_tasks_map,
            period_start_dt,
            period_end_dt,
            work_start_hour,
            work_end_hour,
            horizon_end_min,
        )

        if reward_var is not None:
            max_reward = horizon_end_min * component.weight
            cost_var = model.NewIntVar(
                0, max_reward, f"cost_{component.__class__.__name__}"
            )
            model.Add(cost_var == max_reward - reward_var)
            custom_costs.append(cost_var)

    total_custom_cost = sum(custom_costs) if custom_costs else model.NewConstant(0)

    # Combine all costs into a single objective to MINIMIZE
    # Use a large enough upper bound that covers all possible costs
    max_possible_cost = (
        len(or_tasks_map) * UNSCHEDULED_PENALTY_BASE + horizon_end_min * 100
    )
    objective_var = model.NewIntVar(0, max_possible_cost, "total_objective_cost")
    model.Add(objective_var == total_penalty + total_custom_cost)

    logger.info("Built objective function to MINIMIZE total penalties and costs.")
    return objective_var


def _solve_model(model, objective_expr=None):
    """Solve the scheduling model by MINIMIZING the objective."""
    logger.debug("Solving scheduling model...")
    if objective_expr is not None:
        model.Minimize(objective_expr)  # We now always MINIMIZE
        logger.debug("Minimizing objective function.")
    else:
        logger.debug("Solving as a feasibility problem.")

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False
    solver.parameters.max_time_in_seconds = 30.0

    status = solver.Solve(model)
    return solver, status


def _round_to_nearest_5_minutes(dt: datetime) -> datetime:
    """Round a datetime to the nearest 5 minutes."""
    minutes = dt.minute
    rounded_minutes = round(minutes / 5) * 5
    if rounded_minutes == 60:
        return dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return dt.replace(minute=rounded_minutes, second=0, microsecond=0)


def _update_task_statuses(scheduled_tasks_result, unscheduled_task_objects):
    """Update task statuses in the database based on scheduling results."""
    # Update scheduled tasks
    for scheduled_task in scheduled_tasks_result:
        task_id = scheduled_task["task_id"]
        task = db.session.get(Task, task_id)
        if task:
            task.status = "scheduled"
            task.start = scheduled_task["start"]
            task.end = scheduled_task["end"]

    # Update unscheduled tasks
    for task in unscheduled_task_objects:
        task.status = "unschedulable"

    # Commit all changes
    db.session.commit()


def _process_results(solver, status, or_tasks_map, period_start_dt):
    """Process solver results, returning lists of scheduled and unscheduled tasks."""
    scheduled_tasks_result, unscheduled_task_objects = [], []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for or_task in or_tasks_map.values():
            if solver.BooleanValue(or_task.is_performed_bool):
                start_val_min = solver.Value(or_task.start_var)
                scheduled_start_dt = period_start_dt + timedelta(minutes=start_val_min)
                scheduled_end_dt = scheduled_start_dt + timedelta(
                    minutes=or_task.duration_min
                )

                # Round all task times to nearest 5 minutes
                scheduled_start_dt = _round_to_nearest_5_minutes(scheduled_start_dt)
                scheduled_end_dt = _round_to_nearest_5_minutes(scheduled_end_dt)

                scheduled_tasks_result.append(
                    {
                        "task_id": or_task.id,
                        "start": scheduled_start_dt,
                        "end": scheduled_end_dt,
                    }
                )
            else:
                unscheduled_task_objects.append(or_task.task_obj)

        # Sort by start time for readability
        scheduled_tasks_result.sort(key=lambda x: x["start"])
        logger.debug(
            f"Successfully scheduled {len(scheduled_tasks_result)} tasks, {len(unscheduled_task_objects)} unscheduled"
        )

        # Update task statuses in the database
        _update_task_statuses(scheduled_tasks_result, unscheduled_task_objects)

        return scheduled_tasks_result, unscheduled_task_objects, "Feasible"

    all_tasks = [or_task.task_obj for or_task in or_tasks_map.values()]
    return [], all_tasks, f"Infeasible: {solver.StatusName(status)}"


def schedule_tasks_with_or_tools(
    tasks_to_schedule: list,  # List of Task DB objects (pre-expanded)
    calendar_events: list,  # List of CalendarEvent DB objects
    task_dependencies_map: dict,  # task_id -> list of dependency_ids (strings)
    period_start_dt: datetime,
    period_end_dt: datetime,
    work_start_hour: int,
    work_end_hour: int,
    objectives: SchedulerObjectives | None = None,
):
    """
    Schedule tasks using Google OR-Tools constraint solver.

    Creates an optimal schedule that respects:
    - Task time windows and durations
    - Calendar events (no scheduling during events)
    - Task dependencies (one task must complete before another starts)
    - Work hours (only schedule during work hours on weekdays)
    - Due dates (tasks must complete before their due date)
    - Optimization objectives (if provided)

    All times are converted to minutes relative to period_start_dt for the solver.

    Args:
        tasks_to_schedule: List of Task DB objects to schedule
        calendar_events: List of CalendarEvent DB objects to avoid
        task_dependencies_map: Dictionary mapping task IDs to their dependency IDs
        period_start_dt: Start of scheduling period
        period_end_dt: End of scheduling period
        work_start_hour: Hour when work day starts (e.g., 9 for 9 AM)
        work_end_hour: Hour when work day ends (e.g., 17 for 5 PM)
        objectives: Optional SchedulerObjectives instance defining optimization goals.
                   If None, will solve as a feasibility problem.
    """
    model = cp_model.CpModel()

    # --- 1. Setup Time Horizon ---
    logger.debug(f"Work Hours: {work_start_hour}:00 - {work_end_hour}:00")
    horizon_end_min = _validate_scheduling_period(period_start_dt, period_end_dt)

    # --- 2. Create Task Variables ---
    or_tasks_map = _create_task_variables(
        model, tasks_to_schedule, period_start_dt, horizon_end_min
    )

    # Extract interval variables for all tasks
    all_task_interval_vars = [t.interval_var for t in or_tasks_map.values()]

    # --- 3. Build Forbidden Time Segments ---
    # These represent times when tasks cannot be scheduled (events, non-work hours, weekends)
    calendar_segments = _build_calendar_event_segments(
        calendar_events, period_start_dt, period_end_dt
    )
    non_work_segments = _build_non_work_hour_segments(
        period_start_dt, period_end_dt, work_start_hour, work_end_hour
    )

    raw_fixed_segments = calendar_segments + non_work_segments

    # Merge overlapping segments for efficiency
    merged_forbidden_segments = merge_overlapping_intervals(raw_fixed_segments)
    logger.debug(
        f"Created {len(merged_forbidden_segments)} merged forbidden time segments"
    )

    # Create OR-Tools interval variables for forbidden zones
    forbidden_zone_intervals = _create_forbidden_intervals(
        model, merged_forbidden_segments
    )

    # --- 4. Add NoOverlap Constraint ---
    all_intervals_to_check = all_task_interval_vars + forbidden_zone_intervals
    _add_no_overlap_constraint(model, all_intervals_to_check)

    # --- 5. Due Date Constraints ---
    _add_due_date_constraints(model, or_tasks_map)

    # --- 6. Dependency Constraints ---
    _add_dependency_constraints(model, or_tasks_map, task_dependencies_map)

    # --- 7. Instance Date Constraints ---
    _add_instance_date_constraints(
        model,
        or_tasks_map,
        period_start_dt,
        period_end_dt,
        work_start_hour,
        work_end_hour,
        horizon_end_min,
    )

    # --- 8. Task-Specific Time Window Constraints ---
    _add_time_window_constraints(
        model,
        or_tasks_map,
        period_start_dt,
        period_end_dt,
        work_start_hour,
        work_end_hour,
    )

    # --- 9. Define Objective Function ---
    logger.debug("Building objective function...")
    objective_var = None
    if objectives is not None:
        objective_var = _build_objective_function(
            model,
            or_tasks_map,
            period_start_dt,
            period_end_dt,
            work_start_hour,
            work_end_hour,
            horizon_end_min,
            objectives,
        )

    # --- 10. Solve the Model ---
    solver, status = _solve_model(model, objective_var)

    # --- 11. Process Results ---
    return _process_results(solver, status, or_tasks_map, period_start_dt)


def generate_schedule(
    start_date: datetime,
    end_date: datetime,
    objectives: SchedulerObjectives | None = None,
):
    """
    Generate an optimal schedule for tasks within the given time period.

    This is the main entry point for the scheduling system. It fetches relevant
    calendar events and tasks from the database, expands recurring tasks into
    individual instances, and then uses the OR-Tools solver to create an optimal
    schedule respecting all constraints.

    Args:
        start_date: Datetime defining the start of the scheduling period
        end_date: Datetime defining the end of the scheduling period
        objectives: Optional SchedulerObjectives instance defining optimization goals.
                   If None, will use default objectives.

    Returns:
        tuple: (scheduled_tasks, status_message)
            - scheduled_tasks: List of scheduled task objects with start/end times,
              or None if scheduling was infeasible
            - status_message: String indicating success or reason for failure
    """
    # Use default objectives if none provided
    if objectives is None:
        objectives = SchedulerObjectives.default()

    # Fetch relevant data from database
    calendar_events = get_calendar_events(start_date, end_date)

    # reset recurring tasks, expanding them into individual instances
    reset_recurring_events(start_date, end_date)
    all_tasks_from_db = get_tasks(start_date, end_date)
    # Get task dependencies
    task_dependencies = get_task_dependencies()

    # Pre-validate tasks
    tasks_to_schedule, pre_failed_tasks = pre_schedule_validation(
        all_tasks_from_db, start_date
    )

    # Update status of pre-failed tasks
    for failed_task_info in pre_failed_tasks:
        task = failed_task_info["task"]
        task.status = "unschedulable"
    db.session.commit()

    # Run the scheduler with appropriate working hours from config
    scheduled_data, solver_failed_tasks, status_msg = schedule_tasks_with_or_tools(
        tasks_to_schedule,
        calendar_events,
        task_dependencies,
        start_date,
        end_date,
        current_app.config["WORK_START_HOUR"],
        current_app.config["WORK_END_HOUR"],
        objectives,
    )

    # Combine all failure information
    all_failed_info = pre_failed_tasks
    failed_ids = {f["task"].id for f in pre_failed_tasks}

    if solver_failed_tasks:
        for task in solver_failed_tasks:
            failed_ids.add(task.id)
        solver_failure_analysis = analyze_unscheduled_tasks(
            solver_failed_tasks, all_tasks_from_db, failed_ids
        )
        all_failed_info.extend(solver_failure_analysis)

    return {
        "scheduled_tasks": scheduled_data,
        "unscheduled_tasks": all_failed_info,
        "status_message": status_msg,
    }
