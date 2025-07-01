import uuid
from datetime import datetime, timedelta

from backend.extensions import create_logger, db

logger = create_logger(__name__, level="INFO")


def generate_uuid():
    return str(uuid.uuid4())


class RecurringEvent(db.Model):
    __tablename__ = "recurring_events"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    content = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    time_window_start = db.Column(db.Time, nullable=True)
    time_window_end = db.Column(db.Time, nullable=True)

    recurrence = db.Column(db.JSON, nullable=True)
    # recurrence is a list with days in it.
    # so a task that recurs on MWF would be [0,2,4]

    # Tasks generated from this recurring event
    tasks = db.relationship(
        "Task", backref=db.backref("recurring_event", lazy=True), lazy=True
    )

    def __repr__(self):
        return (
            f"<RecurringEvent {self.id}: {self.content}, Recurrence: {self.recurrence}>"
        )

    def to_dict(self):
        """Convert recurring event to a dictionary for API serialization"""
        return {
            "id": self.id,
            "content": self.content,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "time_window_start": (
                self.time_window_start.strftime("%H:%M")
                if self.time_window_start
                else None
            ),
            "time_window_end": (
                self.time_window_end.strftime("%H:%M") if self.time_window_end else None
            ),
            "recurrence": self.recurrence,
            "tasks": [task.id for task in self.tasks] if self.tasks else [],
        }

    def _is_task_feasible_today(self, current_time: datetime) -> bool:
        """
        Check if a task can feasibly be completed today given the current time.

        Args:
            current_time: Current datetime to check against

        Returns:
            True if the task can be completed today, False otherwise
        """
        # If no time window is set, task is always feasible
        if not self.time_window_start or not self.time_window_end:
            return True

        # Get current time as time object for comparison
        current_time_only = current_time.time()

        # Calculate the latest possible start time for the task
        # Task duration is in minutes, so we need to subtract that from the end time
        duration_timedelta = timedelta(minutes=self.duration)

        # Convert time_window_end to datetime for calculation
        today = current_time.date()
        window_end_datetime = datetime.combine(today, self.time_window_end)

        # Calculate the latest possible start time
        latest_start_datetime = window_end_datetime - duration_timedelta
        latest_start_time = latest_start_datetime.time()

        # Check if current time is before the latest possible start time
        # and after the time window start
        if current_time_only < self.time_window_start:
            # Current time is before the time window starts, so task is feasible
            return True
        elif current_time_only > latest_start_time:
            # Current time is after the latest possible start time, task is not feasible
            return False
        else:
            # Current time is within the feasible window
            return True

    def create_tasks(self, start_date: datetime, end_date: datetime):
        logger.debug(f"Creating tasks for recurring event {self.id}")
        # for each day in the recurrence, create a task
        # do this by setting the instance_date to the day
        n_tasks_created = 0

        # Get current datetime to check both date and time feasibility
        current_datetime = datetime.utcnow()

        # Start from the later of start_date or today
        effective_start = max(start_date.date(), current_datetime.date())
        day_iterator = effective_start

        while day_iterator < end_date.date():
            if day_iterator.weekday() in self.recurrence:
                # Check if this is today and if the task is feasible given current time
                if day_iterator == current_datetime.date():
                    if not self._is_task_feasible_today(current_datetime):
                        logger.debug(
                            f"Skipping task creation for today - task not feasible at current time {current_datetime.time()}"
                        )
                        day_iterator += timedelta(days=1)
                        continue

                task = Task(
                    content=self.content,
                    duration=self.duration,
                    due_by=datetime.combine(day_iterator, time=datetime.max.time()),
                    recurring_event_id=self.id,
                    time_window_start=self.time_window_start,
                    time_window_end=self.time_window_end,
                    instance_date=day_iterator,
                )
                db.session.add(task)
                n_tasks_created += 1
            day_iterator += timedelta(days=1)
        db.session.commit()
        logger.debug(f"Created {n_tasks_created} tasks for recurring event {self.id}")

    def reset_tasks(self, start_date, end_date):
        logger.debug(f"Resetting tasks for recurring event {self.id}")
        # delete all tasks for this recurring event
        Task.query.filter_by(recurring_event_id=self.id).delete()
        # re-create the tasks
        self.create_tasks(start_date, end_date)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    content = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    # Time window for scheduling
    time_window_start = db.Column(db.Time, nullable=True)
    time_window_end = db.Column(db.Time, nullable=True)

    # One-off task specific fields
    due_by = db.Column(db.DateTime, nullable=True)

    # For tasks generated from recurring events
    recurring_event_id = db.Column(
        db.String(36), db.ForeignKey("recurring_events.id"), nullable=True
    )

    start = db.Column(db.DateTime, nullable=True)
    end = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.String(20), default="unscheduled"
    )  # "unscheduled", "scheduled", "completed", "unschedulable"
    priority = db.Column(db.Integer, nullable=False, default=1)  # NEW COLUMN

    # TODO: I dont love this solution but it does work to keep track of when a task is coming from a recurrence and so must be scheduled to a specific date
    instance_date = db.Column(db.Date, nullable=True)

    # is_active is for backwards compatibility with the old task model
    @property
    def is_active(self):
        return self.status not in ["completed", "unschedulable"]

    # is_completed is for backwards compatibility with the old task model
    @property
    def is_completed(self):
        return self.status == "completed"

    @property
    def task_type(self):
        return "recurring" if self.recurring_event_id else "one-off"

    def __repr__(self):
        s = f"<Task {self.id}: {self.content}."
        if self.due_by:
            s += f" Due by: {self.due_by}"
        if self.recurring_event_id:
            s += f" From recurring event: {self.recurring_event_id}"
        if self.time_window_start:
            s += f" Time window: {self.time_window_start} - {self.time_window_end}"
        if self.start:
            s += f" Start: {self.start}"
        if self.end:
            s += f" End: {self.end}"
        if self.status:
            s += f" Status: {self.status}"

        return s

    def complete(self):
        self.status = "completed"

    def to_dict(self):
        result = {
            "id": self.id,
            "content": self.content,
            "start": (
                self.start.isoformat() + "Z" if self.start else None
            ),  # Add Z to indicate UTC time
            "end": (
                self.end.isoformat() + "Z" if self.end else None
            ),  # Add Z to indicate UTC time
            "status": self.status,
            "duration": self.duration,
            "task_type": self.task_type,
            "recurring_event_id": self.recurring_event_id,
            "instance_date": (
                self.instance_date.isoformat() if self.instance_date else None
            ),
            "due_by": self.due_by.isoformat() + "Z" if self.due_by else None,
            "time_window_start": (
                self.time_window_start.isoformat() if self.time_window_start else None
            ),
            "time_window_end": (
                self.time_window_end.isoformat() if self.time_window_end else None
            ),
            "is_active": self.is_active,
            "is_completed": self.is_completed,
            "dependencies": (
                [assoc.dependency_id for assoc in self.dependencies_assoc]
                if hasattr(self, "dependencies_assoc")
                else []
            ),
        }

        # Include recurring event information if this is a recurring task
        if self.recurring_event_id and self.recurring_event:
            result["recurring_event"] = {
                "id": self.recurring_event.id,
                "content": self.recurring_event.content,
                "recurrence": self.recurring_event.recurrence,
                "time_window_start": (
                    self.recurring_event.time_window_start.isoformat()
                    if self.recurring_event.time_window_start
                    else None
                ),
                "time_window_end": (
                    self.recurring_event.time_window_end.isoformat()
                    if self.recurring_event.time_window_end
                    else None
                ),
            }

        return result


class TaskDependency(db.Model):
    __tablename__ = "task_dependencies"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.String(36), db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    dependency_id = db.Column(
        db.String(36), db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )

    task = db.relationship(
        "Task",
        foreign_keys=[task_id],
        backref=db.backref("dependencies_assoc", cascade="all, delete-orphan"),
    )
    dependency = db.relationship("Task", foreign_keys=[dependency_id])

    __table_args__ = (
        db.UniqueConstraint("task_id", "dependency_id", name="_task_dependency_uc"),
    )
