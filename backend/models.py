import uuid
from datetime import datetime, timedelta

from .extensions import create_logger, db, jwt

logger = create_logger(__name__, level="DEBUG")


def generate_uuid():
    return str(uuid.uuid4())


class RecurringEvent(db.Model):
    __tablename__ = "recurring_tasks"

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

    def create_tasks(self, start_date, end_date):
        logger.debug(f"Creating tasks for recurring event {self.id}")
        # for each day in the recurrence, create a task
        # do this by making the due_by 11:59pm of the day
        n_tasks_created = 0
        day_iterator = start_date.date()
        while day_iterator < end_date.date():
            if day_iterator.weekday() in self.recurrence:
                # TODO: this is flawed, because it will be in UTC
                # so it will say, hey finish this by midnight utc, but that might be 3 PM for someone in California
                due_by = datetime.combine(day_iterator, datetime.max.time())
                task = Task(
                    content=self.content,
                    duration=self.duration,
                    due_by=due_by,
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
        db.String(36), db.ForeignKey("recurring_tasks.id"), nullable=True
    )

    start = db.Column(db.DateTime, nullable=True)
    end = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.String(20), default="unscheduled"
    )  # "unscheduled", "scheduled", "completed",

    # TODO: I dont love this solution but it does work to keep track of when a task is coming from a recurrence and so must be scheduled to a specific date
    instance_date = db.Column(db.Date, nullable=True)

    # is_active is for backwards compatibility with the old task model
    @property
    def is_active(self):
        return self.status != "completed"

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


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    subject = db.Column(db.String(255), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    is_chewy_managed = db.Column(db.Boolean, default=False)
    source_file = db.Column(db.String(255), nullable=True)  # Original JSON file path
    categories = db.Column(db.JSON, nullable=True)  # List of categories
    raw_data = db.Column(
        db.JSON, nullable=True
    )  # Additional fields from JSON as needed

    def __repr__(self):
        return f"<CalendarEvent {self.id}: {self.subject}>"


# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     google_id = db.Column(db.String(255), nullable=True)
#     apple_id = db.Column(db.String(255), nullable=True)
#     stripe_customer_id = db.Column(db.String(255), nullable=True)

#     name = db.Column(db.String(255), nullable=True)
#     image = db.Column(db.String(255), nullable=True)
#     email = db.Column(db.String(255), nullable=True, unique=True)
#     email_verified = db.Column("emailVerified", db.DateTime, nullable=True)

#     created_at = db.Column(
#         "createdAt", db.DateTime, nullable=False, default=db.func.now()
#     )
#     updated_at = db.Column(
#         "updatedAt", db.DateTime, nullable=False, default=db.func.now()
#     )

#     def __repr__(self):
#         return f"<User {self.id}>"

#     def __str__(self) -> str:
#         return f"<User {self.id}>"


# @jwt.user_lookup_loader
# def user_lookup_callback(_jwt_header, jwt_data):
#     # decode the jwt_data
#     identity = jwt_data["sub"]
#     return User.query.filter_by(id=identity).one_or_none()
