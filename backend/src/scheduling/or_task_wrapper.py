from backend.extensions import create_logger

logger = create_logger(__name__, level="DEBUG")


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
        self.instance_date = task_obj.instance_date  # datetime.date
