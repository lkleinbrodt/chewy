import pytest
from flask import json
from unittest.mock import patch
from backend.models import RecurringEvent, Task
from datetime import datetime, timedelta, time

# Helper function to create a recurring event
def create_recurring_event_db(test_db, **kwargs):
    event_data = {
        'content': kwargs.pop('name', 'Test Recurring Event'), # name -> content
        'duration': 60, # minutes
        'recurrence': kwargs.pop('recurrence_rule', [0,1,2,3,4]), # FREQ=DAILY equivalent for model if it expects list
        'time_window_start': time(9, 0),
        'time_window_end': time(17, 0)
    }
    # Pop description if it exists in kwargs, as it's not in the model
    kwargs.pop('description', None)
    event_data.update(kwargs)
    event = RecurringEvent(**event_data)
    test_db.session.add(event)
    test_db.session.commit()
    return event

# Helper to format time for API calls if needed (though models might handle strings)
def format_time_for_api(t_obj):
    return t_obj.strftime('%H:%M:%S')

# 1. Tests for GET /api/recurring-events
def test_get_recurring_events_empty(client, test_db):
    response = client.get('/api/recurring-events')
    assert response.status_code == 200
    assert json.loads(response.data) == []

def test_get_recurring_events_multiple(client, test_db):
    create_recurring_event_db(test_db, name='Event 1')
    create_recurring_event_db(test_db, name='Event 2')
    response = client.get('/api/recurring-events')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    names = {item['name'] for item in data}
    assert 'Event 1' in names
    assert 'Event 2' in names

# 2. Tests for POST /api/recurring-events
def test_create_recurring_event_successful(client, test_db):
    payload = {
        'name': 'Weekly Meeting',
        'description': 'Team sync meeting',
        'duration': 45,
        'recurrence_rule': 'FREQ=WEEKLY;BYDAY=MO',
        'time_window_start': '10:00',
        'time_window_end': '11:00'
    }
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'id' in data
    assert data['name'] == 'Weekly Meeting'
    assert data['message'] == 'Recurring event created successfully.'

    event_id = data['id']
    event_db = RecurringEvent.query.get(event_id)
    assert event_db is not None
    assert event_db.name == 'Weekly Meeting'
    assert event_db.time_window_start == time(10, 0)
    assert event_db.time_window_end == time(11, 0)

    # Verify associated tasks (default next 7 days)
    tasks = Task.query.filter_by(recurring_event_id=event_id).all()
    assert len(tasks) > 0 # Exact number depends on FREQ and today

def test_create_recurring_event_minimal_fields(client, test_db):
    payload = {
        'name': 'Quick Task',
        'duration': 30
    }
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'id' in data
    assert data['name'] == 'Quick Task'
    event_db = RecurringEvent.query.get(data['id'])
    assert event_db is not None
    assert event_db.recurrence_rule == 'FREQ=DAILY' # Default
    assert Task.query.filter_by(recurring_event_id=data['id']).count() > 0


def test_create_recurring_event_invalid_input_missing_name(client, test_db):
    payload = {'duration': 30}
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 400
    assert 'name' in json.loads(response.data)['error'] # field name in error

def test_create_recurring_event_invalid_input_missing_duration(client, test_db):
    payload = {'name': 'No Duration Event'}
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 400
    assert 'duration' in json.loads(response.data)['error']

def test_create_recurring_event_invalid_recurrence_format(client, test_db):
    payload = {
        'name': 'Bad Recurrence',
        'duration': 60,
        'recurrence_rule': 'INVALID_RULE'
    }
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 400
    assert 'Invalid recurrence_rule format' in json.loads(response.data)['error']

def test_create_recurring_event_invalid_time_format(client, test_db):
    payload = {
        'name': 'Bad Time',
        'duration': 60,
        'time_window_start': '25:00' # Invalid time
    }
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 400
    assert 'Invalid time_window_start format' in json.loads(response.data)['error']

def test_create_recurring_event_different_time_formats(client, test_db):
    payload = {
        'name': 'Time Format Test',
        'duration': 60,
        'time_window_start': '09:30', # HH:MM
        'time_window_end': '17:45:30' # HH:MM:SS
    }
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 201
    data = json.loads(response.data)
    event_db = RecurringEvent.query.get(data['id'])
    assert event_db.time_window_start == time(9, 30)
    assert event_db.time_window_end == time(17, 45, 30)

# 3. Tests for GET /api/recurring-events/<recurring_event_id>
def test_get_recurring_event_by_id_existing(client, test_db):
    event = create_recurring_event_db(test_db, name='Specific Event')
    response = client.get(f'/api/recurring-events/{event.id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == 'Specific Event'
    assert data['id'] == event.id

def test_get_recurring_event_by_id_non_existent(client, test_db):
    response = client.get('/api/recurring-events/9999')
    assert response.status_code == 404

# 4. Tests for PUT /api/recurring-events/<recurring_event_id>
def test_update_recurring_event_successful(client, test_db):
    event = create_recurring_event_db(test_db, name='Old Name', duration=30)
    payload = {
        'name': 'New Name',
        'duration': 75,
        'recurrence_rule': 'FREQ=MONTHLY',
        'time_window_start': '08:00',
        'time_window_end': '18:00'
    }
    response = client.put(f'/api/recurring-events/{event.id}', json=payload)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == 'New Name'
    assert data['duration'] == 75
    assert data['recurrence_rule'] == 'FREQ=MONTHLY'

    event_db = RecurringEvent.query.get(event.id)
    assert event_db.name == 'New Name'
    assert event_db.duration == 75
    assert event_db.recurrence_rule == 'FREQ=MONTHLY'
    assert event_db.time_window_start == time(8, 0)
    assert event_db.time_window_end == time(18, 0)

def test_update_recurring_event_non_existent(client, test_db):
    payload = {'name': 'Attempt Update'}
    response = client.put('/api/recurring-events/9999', json=payload)
    assert response.status_code == 404

def test_update_recurring_event_invalid_recurrence(client, test_db):
    event = create_recurring_event_db(test_db)
    payload = {'recurrence_rule': 'INVALID'}
    response = client.put(f'/api/recurring-events/{event.id}', json=payload)
    assert response.status_code == 400
    assert 'Invalid recurrence_rule format' in json.loads(response.data)['error']

def test_update_recurring_event_invalid_time(client, test_db):
    event = create_recurring_event_db(test_db)
    payload = {'time_window_end': 'bad-time'}
    response = client.put(f'/api/recurring-events/{event.id}', json=payload)
    assert response.status_code == 400
    assert 'Invalid time_window_end format' in json.loads(response.data)['error']


# 5. Tests for DELETE /api/recurring-events/<recurring_event_id>
def test_delete_recurring_event_successful(client, test_db):
    event = create_recurring_event_db(test_db, name='To Be Deleted')
    # Create some tasks for this event
    task1 = Task(content='Task for deletion 1', duration=30, recurring_event_id=event.id, due_by=datetime.utcnow())
    task2 = Task(content='Task for deletion 2', duration=30, recurring_event_id=event.id, due_by=datetime.utcnow() + timedelta(days=1))
    test_db.session.add_all([task1, task2])
    test_db.session.commit()

    assert RecurringEvent.query.get(event.id) is not None
    assert Task.query.filter_by(recurring_event_id=event.id).count() == 2

    response = client.delete(f'/api/recurring-events/{event.id}')
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == 'Recurring event and associated tasks deleted successfully.'

    assert RecurringEvent.query.get(event.id) is None
    assert Task.query.filter_by(recurring_event_id=event.id).count() == 0

def test_delete_recurring_event_non_existent(client, test_db):
    response = client.delete('/api/recurring-events/9999')
    assert response.status_code == 404

# 6. Tests for POST /api/recurring-events/<recurring_event_id>/reset-tasks
@patch('backend.models.RecurringEvent.reset_tasks')
def test_reset_tasks_successful(mock_reset_tasks, client, test_db):
    event = create_recurring_event_db(test_db)
    mock_reset_tasks.return_value = (5, 0) # (tasks_created, tasks_deleted)

    start_date_str = (datetime.utcnow() - timedelta(days=1)).isoformat()
    end_date_str = (datetime.utcnow() + timedelta(days=6)).isoformat()
    payload = {'start_date': start_date_str, 'end_date': end_date_str}

    response = client.post(f'/api/recurring-events/{event.id}/reset-tasks', json=payload)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Tasks reset successfully.'
    assert data['tasks_created'] == 5
    assert data['tasks_deleted'] == 0 # This might vary based on actual old tasks

    start_date_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
    end_date_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))

    mock_reset_tasks.assert_called_once()
    args, _ = mock_reset_tasks.call_args
    # args[0] is db.session, args[1] is start_date, args[2] is end_date
    assert args[1].date() == start_date_dt.date()
    assert args[2].date() == end_date_dt.date()


def test_reset_tasks_non_existent_event(client, test_db):
    start_date_str = datetime.utcnow().isoformat()
    end_date_str = (datetime.utcnow() + timedelta(days=7)).isoformat()
    payload = {'start_date': start_date_str, 'end_date': end_date_str}
    response = client.post('/api/recurring-events/9999/reset-tasks', json=payload)
    assert response.status_code == 404

def test_reset_tasks_missing_dates(client, test_db):
    event = create_recurring_event_db(test_db)
    payload = {} # Missing dates
    response = client.post(f'/api/recurring-events/{event.id}/reset-tasks', json=payload)
    assert response.status_code == 400
    assert 'start_date and end_date are required' in json.loads(response.data)['error']

def test_reset_tasks_invalid_date_range(client, test_db):
    event = create_recurring_event_db(test_db)
    start_date_str = (datetime.utcnow() + timedelta(days=7)).isoformat() # End before start
    end_date_str = datetime.utcnow().isoformat()
    payload = {'start_date': start_date_str, 'end_date': end_date_str}
    response = client.post(f'/api/recurring-events/{event.id}/reset-tasks', json=payload)
    assert response.status_code == 400
    assert 'end_date must be after start_date' in json.loads(response.data)['error']

def test_reset_tasks_invalid_date_format(client, test_db):
    event = create_recurring_event_db(test_db)
    payload = {'start_date': 'not-a-date', 'end_date': 'also-not-a-date'}
    response = client.post(f'/api/recurring-events/{event.id}/reset-tasks', json=payload)
    assert response.status_code == 400
    assert 'Invalid date format for start_date or end_date' in json.loads(response.data)['error']

# Test that task creation on POST actually creates tasks
def test_create_recurring_event_actually_creates_tasks(client, test_db):
    payload = {
        'name': 'Daily Standup',
        'duration': 15,
        'recurrence_rule': 'FREQ=DAILY;BYHOUR=9', # Specific enough for count
        'time_window_start': '09:00',
        'time_window_end': '09:30'
    }
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 201
    event_id = json.loads(response.data)['id']

    # Default creation period is 7 days. A daily event should create approx 7 tasks.
    # This can be tricky if the event's first occurrence is today but time_window_start is already past.
    # For simplicity, check for a reasonable number.
    tasks_created = Task.query.filter_by(recurring_event_id=event_id).count()
    assert tasks_created >= 0 # Should be around 7, but depends on exact time of day and first occurrence.
                               # A more robust test would mock 'datetime.now()' or calculate expected tasks precisely.
                               # For now, just ensuring it's not failing to create any.
    # If the `create_tasks` is called with default 7 days.
    # A FREQ=DAILY event should have 7 tasks unless some are in the past relative to time_window.
    # Let's assume at least one task is created for a valid daily event.
    assert tasks_created > 0, "Expected at least one task to be created for a new daily recurring event"


@patch('backend.models.RecurringEvent.create_tasks')
def test_create_recurring_event_calls_create_tasks(mock_create_tasks, client, test_db):
    mock_create_tasks.return_value = [] # Simulate it returns a list of tasks (even if empty)
    payload = {
        'name': 'Test Create Tasks Call',
        'duration': 30
    }
    response = client.post('/api/recurring-events', json=payload)
    assert response.status_code == 201
    mock_create_tasks.assert_called_once()
    # Check arguments of the call (session, start_date, end_date)
    args, _ = mock_create_tasks.call_args
    assert args[0] == test_db.session # db.session
    # args[1] is start_date (today), args[2] is end_date (today + 7 days)
    assert args[1].date() == datetime.utcnow().date()
    assert args[2].date() == (datetime.utcnow() + timedelta(days=7)).date()

@patch('backend.recurring_routes.db.session.commit')
def test_delete_recurring_event_commit_failure(mock_commit, client, test_db):
    event = create_recurring_event_db(test_db, name='Commit Fail Delete')
    mock_commit.side_effect = Exception("Simulated DB commit error")

    response = client.delete(f'/api/recurring-events/{event.id}')
    assert response.status_code == 500
    assert 'Failed to delete recurring event' in json.loads(response.data)['error']
    # Verify event still exists (due to rollback)
    assert RecurringEvent.query.get(event.id) is not None

@patch('backend.recurring_routes.db.session.commit')
def test_reset_tasks_commit_failure(mock_commit, client, test_db):
    event = create_recurring_event_db(test_db)
    # We need to mock reset_tasks_for_period if it does its own commit,
    # or ensure the commit we are mocking is the one in the route.
    # Assuming the route's commit is the one to mock here.
    start_date_str = datetime.utcnow().isoformat()
    end_date_str = (datetime.utcnow() + timedelta(days=6)).isoformat()
    payload = {'start_date': start_date_str, 'end_date': end_date_str}

    # Mock the method that would do the work and potentially be followed by a commit
    with patch('backend.models.RecurringEvent.reset_tasks', return_value=(1,1)) as mock_reset: # Patched the correct model method
        mock_commit.side_effect = Exception("Simulated DB commit error")
        response = client.post(f'/api/recurring-events/{event.id}/reset-tasks', json=payload)

    assert response.status_code == 500
    assert 'Failed to reset tasks' in json.loads(response.data)['error']
    mock_reset.assert_called_once() # Ensure the model method was called
    mock_commit.assert_called_once() # Ensure commit was attempted
