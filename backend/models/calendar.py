import uuid

from backend.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


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
