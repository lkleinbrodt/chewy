"""
Reward components for the scheduler optimization.

This module contains the reward component interface and implementations of various
reward functions that can be used to optimize the schedule according to different criteria.
"""

from abc import ABC, abstractmethod
from datetime import datetime, time, timedelta
from typing import List, Optional, Tuple

from ortools.sat.python import cp_model

from backend.extensions import create_logger

logger = create_logger(__name__, level="INFO")


class RewardComponent(ABC):
    """Abstract base class for reward components.

    Each reward component represents a specific optimization criterion for the scheduler.
    Components can be enabled/disabled and weighted according to their importance.
    """

    def __init__(self, weight: int = 1):
        """Initialize the reward component.

        Args:
            weight: Integer weight for this component's contribution to the total objective.
                   Must be an integer as CP-SAT requires integer arithmetic.
        """
        self.weight = weight
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Whether this reward component is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Set whether this reward component is enabled."""
        self._enabled = value

    @abstractmethod
    def calculate_reward(
        self,
        model: cp_model.CpModel,
        or_tasks_map: dict,
        period_start_dt: datetime,
        period_end_dt: datetime,
        work_start_hour: int,
        work_end_hour: int,
        horizon_end_min: int,
    ) -> Optional[cp_model.IntVar]:
        """Calculate the reward value for this component.

        This is the main method that each reward component must implement. It should create
        any necessary variables and constraints in the model and return an IntVar representing
        the reward value.

        Args:
            model: The CP-SAT model to add variables and constraints to
            or_tasks_map: Dictionary mapping task IDs to ORTaskWrapper objects
            period_start_dt: Start of scheduling period
            period_end_dt: End of scheduling period
            work_start_hour: Hour when work day starts (e.g., 9 for 9 AM)
            work_end_hour: Hour when work day ends (e.g., 17 for 5 PM)
            horizon_end_min: Length of scheduling period in minutes

        Returns:
            An IntVar representing this component's contribution to the objective,
            or None if the component is disabled or not applicable.
        """
        pass


def get_workday_boundaries(
    day_date: datetime.date,
    period_start_dt: datetime,
    period_end_dt: datetime,
    work_start_hour: int,
    work_end_hour: int,
) -> Tuple[datetime, datetime]:
    """Helper function to get the effective work hours for a given day.

    Args:
        day_date: The date to get work hours for
        period_start_dt: Start of scheduling period
        period_end_dt: End of scheduling period
        work_start_hour: Hour when work day starts (e.g., 9 for 9 AM)
        work_end_hour: Hour when work day ends (e.g., 17 for 5 PM)

    Returns:
        Tuple of (work_start_dt, work_end_dt) for the given day, clipped to the period
    """
    day_work_start = datetime.combine(day_date, time(work_start_hour, 0))
    day_work_end = datetime.combine(day_date, time(work_end_hour, 0))

    # Clip to scheduling period
    effective_start = max(day_work_start, period_start_dt)
    effective_end = min(day_work_end, period_end_dt)

    return effective_start, effective_end


def get_workdays_in_period(
    period_start_dt: datetime,
    period_end_dt: datetime,
) -> List[datetime.date]:
    """Helper function to get all workdays (Mon-Fri) in the scheduling period.

    Args:
        period_start_dt: Start of scheduling period
        period_end_dt: End of scheduling period

    Returns:
        List of dates that are workdays in the period
    """
    workdays = []
    current_date = period_start_dt.date()
    while current_date <= period_end_dt.date():
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            workdays.append(current_date)
        current_date += timedelta(days=1)
    return workdays


class FreeAfternoonReward(RewardComponent):
    """Reward component that maximizes free time at the end of each workday.

    This component encourages the scheduler to complete tasks earlier in the day,
    leaving afternoons free when possible. For each workday, it calculates:
    reward = work_day_end - last_task_end_time

    The total reward is the sum across all workdays in the period.
    """

    def calculate_reward(
        self,
        model: cp_model.CpModel,
        or_tasks_map: dict,
        period_start_dt: datetime,
        period_end_dt: datetime,
        work_start_hour: int,
        work_end_hour: int,
        horizon_end_min: int,
    ) -> Optional[cp_model.IntVar]:
        """Calculate the free afternoon reward.

        For each workday, finds the end time of the last scheduled task and
        maximizes the gap between that and the end of the workday.

        Returns:
            An IntVar representing the total free afternoon time across all days,
            or None if there are no tasks to schedule.
        """
        if not or_tasks_map:  # No tasks to schedule
            logger.debug("No tasks to schedule, returning maximum possible free time")
            # Calculate total possible free time (all afternoons completely free)
            total_free_time = 0
            workdays = get_workdays_in_period(period_start_dt, period_end_dt)
            for day in workdays:
                day_start, day_end = get_workday_boundaries(
                    day, period_start_dt, period_end_dt, work_start_hour, work_end_hour
                )
                total_free_time += int((day_end - day_start).total_seconds() / 60)
            return model.NewConstant(total_free_time)

        daily_rewards = []  # Reward for each workday
        workdays = get_workdays_in_period(period_start_dt, period_end_dt)

        for day in workdays:
            # Get effective work hours for this day
            day_start, day_end = get_workday_boundaries(
                day, period_start_dt, period_end_dt, work_start_hour, work_end_hour
            )

            # Convert to minutes relative to period start
            day_start_min = int((day_start - period_start_dt).total_seconds() / 60)
            day_end_min = int((day_end - period_start_dt).total_seconds() / 60)

            if day_end_min <= day_start_min:  # No work hours on this day
                continue

            # This variable will store the end time of the last task on this day
            last_task_end = model.NewIntVar(
                day_start_min, day_end_min, f"last_task_end_day_{day.toordinal()}"
            )

            # For each task, determine if it ends on this day
            task_end_times_today = []
            # Add baseline: if no tasks end today, last_task_end should be day_start_min
            task_end_times_today.append(model.NewConstant(day_start_min))

            for or_task in or_tasks_map.values():
                # A task ends on this day if:
                # 1. It ends after day start
                # 2. It ends before or at day end
                # 3. It starts before day end (to ensure it's relevant to this day)
                task_ends_today = model.NewBoolVar(
                    f"task_{or_task.id}_ends_on_{day.toordinal()}"
                )

                # Condition 1: Task ends after day start
                c1 = model.NewBoolVar(f"c1_{or_task.id}_{day.toordinal()}")
                model.Add(or_task.end_var > day_start_min).OnlyEnforceIf(c1)
                model.Add(or_task.end_var <= day_start_min).OnlyEnforceIf(c1.Not())

                # Condition 2: Task ends before or at day end
                c2 = model.NewBoolVar(f"c2_{or_task.id}_{day.toordinal()}")
                model.Add(or_task.end_var <= day_end_min).OnlyEnforceIf(c2)
                model.Add(or_task.end_var > day_end_min).OnlyEnforceIf(c2.Not())

                # Condition 3: Task starts before day end
                c3 = model.NewBoolVar(f"c3_{or_task.id}_{day.toordinal()}")
                model.Add(or_task.start_var < day_end_min).OnlyEnforceIf(c3)
                model.Add(or_task.start_var >= day_end_min).OnlyEnforceIf(c3.Not())

                # Task ends today if all conditions are true
                model.AddBoolAnd([c1, c2, c3]).OnlyEnforceIf(task_ends_today)
                model.AddBoolOr([c1.Not(), c2.Not(), c3.Not()]).OnlyEnforceIf(
                    task_ends_today.Not()
                )

                # If task ends today, consider its end time
                task_effective_end = model.NewIntVar(
                    day_start_min,
                    day_end_min,
                    f"task_{or_task.id}_eff_end_{day.toordinal()}",
                )
                model.Add(task_effective_end == or_task.end_var).OnlyEnforceIf(
                    task_ends_today
                )
                model.Add(task_effective_end == day_start_min).OnlyEnforceIf(
                    task_ends_today.Not()
                )
                task_end_times_today.append(task_effective_end)

            # Last task end time is the maximum of all task end times
            model.AddMaxEquality(last_task_end, task_end_times_today)

            # Reward for this day is (day_end - last_task_end)
            day_reward = model.NewIntVar(
                0, day_end_min - day_start_min, f"reward_day_{day.toordinal()}"
            )
            model.Add(day_reward == day_end_min - last_task_end)
            daily_rewards.append(day_reward)

        if not daily_rewards:  # No workdays in period
            logger.debug("No workdays in period")
            return None

        # Total reward is sum of daily rewards
        total_reward = model.NewIntVar(
            0, horizon_end_min, "total_free_afternoon_reward"
        )
        model.Add(total_reward == sum(daily_rewards))

        logger.debug(f"Built free afternoon reward for {len(daily_rewards)} workdays")
        return total_reward


class FreeMorningReward(RewardComponent):
    """Reward component that maximizes free time at the start of each workday.

    This component encourages the scheduler to delay tasks until later in the day,
    leaving mornings free when possible. For each workday, it calculates:
    reward = first_task_start_time - work_day_start

    The total reward is the sum across all workdays in the period.
    """

    def calculate_reward(
        self,
        model: cp_model.CpModel,
        or_tasks_map: dict,
        period_start_dt: datetime,
        period_end_dt: datetime,
        work_start_hour: int,
        work_end_hour: int,
        horizon_end_min: int,
    ) -> Optional[cp_model.IntVar]:
        """Calculate the free morning reward.

        For each workday, finds the start time of the first scheduled task and
        maximizes the gap between work start time and that first task.

        Returns:
            An IntVar representing the total free morning time across all days,
            or None if there are no tasks to schedule.
        """
        if not or_tasks_map:  # No tasks to schedule
            logger.debug("No tasks to schedule, returning maximum possible free time")
            # Calculate total possible free time (all mornings completely free)
            total_free_time = 0
            workdays = get_workdays_in_period(period_start_dt, period_end_dt)
            for day in workdays:
                day_start, day_end = get_workday_boundaries(
                    day, period_start_dt, period_end_dt, work_start_hour, work_end_hour
                )
                total_free_time += int((day_end - day_start).total_seconds() / 60)
            return model.NewConstant(total_free_time)

        daily_rewards = []  # Reward for each workday
        workdays = get_workdays_in_period(period_start_dt, period_end_dt)

        for day in workdays:
            # Get effective work hours for this day
            day_start, day_end = get_workday_boundaries(
                day, period_start_dt, period_end_dt, work_start_hour, work_end_hour
            )

            # Convert to minutes relative to period start
            day_start_min = int((day_start - period_start_dt).total_seconds() / 60)
            day_end_min = int((day_end - period_start_dt).total_seconds() / 60)

            if day_end_min <= day_start_min:  # No work hours on this day
                continue

            # This variable will store the start time of the first task on this day
            first_task_start = model.NewIntVar(
                day_start_min, day_end_min, f"first_task_start_day_{day.toordinal()}"
            )

            # For each task, determine if it starts on this day
            task_start_times_today = []
            # Add baseline: if no tasks start today, first_task_start should be day_end_min
            task_start_times_today.append(model.NewConstant(day_end_min))

            for or_task in or_tasks_map.values():
                # A task starts on this day if:
                # 1. It starts after or at day start
                # 2. It starts before day end
                # 3. It ends after day start (to ensure it's relevant to this day)
                task_starts_today = model.NewBoolVar(
                    f"task_{or_task.id}_starts_on_{day.toordinal()}"
                )

                # Condition 1: Task starts after or at day start
                c1 = model.NewBoolVar(f"c1_{or_task.id}_{day.toordinal()}")
                model.Add(or_task.start_var >= day_start_min).OnlyEnforceIf(c1)
                model.Add(or_task.start_var < day_start_min).OnlyEnforceIf(c1.Not())

                # Condition 2: Task starts before day end
                c2 = model.NewBoolVar(f"c2_{or_task.id}_{day.toordinal()}")
                model.Add(or_task.start_var < day_end_min).OnlyEnforceIf(c2)
                model.Add(or_task.start_var >= day_end_min).OnlyEnforceIf(c2.Not())

                # Condition 3: Task ends after day start
                c3 = model.NewBoolVar(f"c3_{or_task.id}_{day.toordinal()}")
                model.Add(or_task.end_var > day_start_min).OnlyEnforceIf(c3)
                model.Add(or_task.end_var <= day_start_min).OnlyEnforceIf(c3.Not())

                # Task starts today if all conditions are true
                model.AddBoolAnd([c1, c2, c3]).OnlyEnforceIf(task_starts_today)
                model.AddBoolOr([c1.Not(), c2.Not(), c3.Not()]).OnlyEnforceIf(
                    task_starts_today.Not()
                )

                # If task starts today, consider its start time
                task_effective_start = model.NewIntVar(
                    day_start_min,
                    day_end_min,
                    f"task_{or_task.id}_eff_start_{day.toordinal()}",
                )
                model.Add(task_effective_start == or_task.start_var).OnlyEnforceIf(
                    task_starts_today
                )
                model.Add(task_effective_start == day_end_min).OnlyEnforceIf(
                    task_starts_today.Not()
                )
                task_start_times_today.append(task_effective_start)

            # First task start time is the minimum of all task start times
            model.AddMinEquality(first_task_start, task_start_times_today)

            # Reward for this day is (first_task_start - day_start)
            day_reward = model.NewIntVar(
                0, day_end_min - day_start_min, f"reward_day_{day.toordinal()}"
            )
            model.Add(day_reward == first_task_start - day_start_min)
            daily_rewards.append(day_reward)

        if not daily_rewards:  # No workdays in period
            logger.debug("No workdays in period")
            return None

        # Total reward is sum of daily rewards
        total_reward = model.NewIntVar(0, horizon_end_min, "total_free_morning_reward")
        model.Add(total_reward == sum(daily_rewards))

        logger.debug(f"Built free morning reward for {len(daily_rewards)} workdays")
        return total_reward


class EvenWorkloadReward(RewardComponent):
    """Reward component that encourages even distribution of workload across days.

    It tries to minimize the difference between the day with the most work
    and the day with the least work. Workload for a day is approximated
    as the sum of durations of tasks starting on that day.
    """

    def calculate_reward(
        self,
        model: cp_model.CpModel,
        or_tasks_map: dict,
        period_start_dt: datetime,
        period_end_dt: datetime,
        work_start_hour: int,
        work_end_hour: int,
        horizon_end_min: int,
    ) -> Optional[cp_model.IntVar]:
        """Calculate the even workload reward.

        Returns:
            An IntVar representing the reward, or None if not applicable.
            The reward is higher when the workload is more evenly distributed.
        """
        if not or_tasks_map:
            logger.debug(
                "EvenWorkloadReward: No tasks to schedule, returning max possible reward."
            )
            return model.NewConstant(horizon_end_min)  # Max reward for perfect evenness

        workdays = get_workdays_in_period(period_start_dt, period_end_dt)
        if not workdays:
            logger.debug("EvenWorkloadReward: No workdays in period, returning None.")
            return None

        daily_workload_vars = []

        for day_idx, day_date in enumerate(workdays):
            day_effective_start, day_effective_end = get_workday_boundaries(
                day_date, period_start_dt, period_end_dt, work_start_hour, work_end_hour
            )

            day_start_min_rel = int(
                (day_effective_start - period_start_dt).total_seconds() / 60
            )
            day_end_min_rel = int(
                (day_effective_end - period_start_dt).total_seconds() / 60
            )

            if day_end_min_rel <= day_start_min_rel:  # No effective work time this day
                # Add a zero workload for this day to keep the list length consistent
                # This ensures days with no work (e.g. period starts/ends mid-day) are counted.
                daily_workload_vars.append(model.NewConstant(0))
                continue

            tasks_starting_this_day_durations = []
            for or_task in or_tasks_map.values():
                # Boolean variable: True if or_task starts on this day
                b_starts_this_day = model.NewBoolVar(
                    f"task_{or_task.id}_starts_on_day_{day_idx}"
                )

                # Task starts on this day if:
                # day_start_min_rel <= or_task.start_var < day_end_min_rel
                # Using strict inequality for end of day to assign task to one day only.

                # Condition 1: task_start >= day_start_min_rel
                c1 = model.NewBoolVar(f"c1_starts_day_{day_idx}_{or_task.id}")
                model.Add(or_task.start_var >= day_start_min_rel).OnlyEnforceIf(c1)
                model.Add(or_task.start_var < day_start_min_rel).OnlyEnforceIf(c1.Not())

                # Condition 2: task_start < day_end_min_rel
                c2 = model.NewBoolVar(f"c2_starts_day_{day_idx}_{or_task.id}")
                model.Add(or_task.start_var < day_end_min_rel).OnlyEnforceIf(c2)
                model.Add(or_task.start_var >= day_end_min_rel).OnlyEnforceIf(c2.Not())

                model.AddBoolAnd([c1, c2]).OnlyEnforceIf(b_starts_this_day)
                model.AddBoolOr([c1.Not(), c2.Not()]).OnlyEnforceIf(
                    b_starts_this_day.Not()
                )

                # Task's duration if it starts on this day, 0 otherwise
                task_duration_if_starts_this_day = model.NewIntVar(
                    0, or_task.duration_min, f"task_{or_task.id}_dur_day_{day_idx}"
                )
                model.Add(
                    task_duration_if_starts_this_day == or_task.duration_min
                ).OnlyEnforceIf(b_starts_this_day)
                model.Add(task_duration_if_starts_this_day == 0).OnlyEnforceIf(
                    b_starts_this_day.Not()
                )
                tasks_starting_this_day_durations.append(
                    task_duration_if_starts_this_day
                )

            current_day_workload = model.NewIntVar(
                0,
                horizon_end_min,
                f"workload_day_{day_idx}",  # Max possible workload is total horizon
            )
            if (
                tasks_starting_this_day_durations
            ):  # Ensure sum is not called on empty list
                model.Add(
                    current_day_workload == sum(tasks_starting_this_day_durations)
                )
            else:  # Should not happen if or_tasks_map is not empty, but as a safe guard
                model.Add(current_day_workload == 0)

            daily_workload_vars.append(current_day_workload)

        if not daily_workload_vars:
            # Should be caught by earlier checks, but as a safeguard
            logger.debug(
                "EvenWorkloadReward: No daily workload variables created, returning max reward."
            )
            return model.NewConstant(horizon_end_min)

        if len(daily_workload_vars) == 1:
            # Only one day, so workload is perfectly "even" (range is 0)
            logger.debug(
                "EvenWorkloadReward: Only one workday, workload is perfectly even."
            )
            return model.NewConstant(horizon_end_min)

        min_daily_workload = model.NewIntVar(0, horizon_end_min, "min_daily_workload")
        max_daily_workload = model.NewIntVar(0, horizon_end_min, "max_daily_workload")

        model.AddMinEquality(min_daily_workload, daily_workload_vars)
        model.AddMaxEquality(max_daily_workload, daily_workload_vars)

        workload_range = model.NewIntVar(0, horizon_end_min, "workload_range")
        model.Add(workload_range == max_daily_workload - min_daily_workload)

        # We want to MAXIMIZE (horizon_end_min - workload_range)
        # This means the reward is higher when workload_range is smaller.
        reward = model.NewIntVar(0, horizon_end_min, "even_workload_reward")
        model.Add(reward == horizon_end_min - workload_range)

        logger.debug(
            f"Built EvenWorkloadReward for {len(daily_workload_vars)} workdays."
        )
        return reward
