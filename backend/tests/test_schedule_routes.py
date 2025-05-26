import pytest
from flask import json
from backend.models import Task
from datetime import datetime, timedelta
from unittest.mock import patch

# Helper function to create a task (can be imported or redefined)
def create_task(test_db, **kwargs):
    task_data = {
        'content': 'Test Task',
        'duration': 60, # minutes
        'status': 'unscheduled',
        # 'task_nature': 'one-off', # Not a direct model field
        # 'is_completed': False, # Handled by status
    }
    task_data.update(kwargs) # Apply kwargs first to allow overriding defaults like content/duration

    if task_data.get('is_completed'):
        task_data['status'] = 'completed'
    task_data.pop('is_completed', None)
    task_data.pop('task_nature', None)
    # These are scheduler outputs, not inputs for task creation
    task_data.pop('scheduled_start_time', None)
    task_data.pop('scheduled_end_time', None)

    task = Task(**task_data)
    test_db.session.add(task)
    test_db.session.commit()
    return task

# Tests for POST /api/schedule
def test_generate_schedule_successful(app, test_db):
    # Create some tasks that can be scheduled
    task1_due_date = datetime.utcnow() + timedelta(days=1)
    task1 = create_task(test_db, content='Task 1 for schedule', duration=30, due_by=task1_due_date)
    task2_due_date = datetime.utcnow() + timedelta(days=2)
    task2 = create_task(test_db, content='Task 2 for schedule', duration=45, due_by=task2_due_date)
    # Task that should not be scheduled (due date outside range)
    create_task(test_db, content='Task 3 outside range', duration=60, due_by=datetime.utcnow() + timedelta(days=5))

    start_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end_date = (datetime.utcnow() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    data = {'start_date': start_date, 'end_date': end_date}
    response = app.test_client().post('/api/schedule', json=data)

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['message'] == 'Schedule generated successfully'
    assert len(response_data['scheduled_tasks']) > 0 # Actual scheduling logic is complex

    # Verify tasks are updated in DB (example check, actual scheduling logic is complex)
    updated_task1 = Task.query.get(task1.id)
    updated_task2 = Task.query.get(task2.id)
    assert updated_task1.status == 'scheduled'
    assert updated_task1.scheduled_start_time is not None
    assert updated_task1.scheduled_end_time is not None
    assert updated_task2.status == 'scheduled'
    assert updated_task2.scheduled_start_time is not None
    assert updated_task2.scheduled_end_time is not None


def test_generate_schedule_start_date_in_past(app, test_db):
    task_due_date = datetime.utcnow() + timedelta(hours=5) # Ensure it's schedulable today
    create_task(test_db, content='Task for past start', duration=30, due_by=task_due_date)

    start_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    data = {'start_date': start_date, 'end_date': end_date}
    response = app.test_client().post('/api/schedule', json=data)

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['message'] == 'Schedule generated successfully'
    # Further checks depend on how generate_schedule handles past start_date
    # For now, we just check it doesn't fail and returns success.
    # A more specific test would require knowing the exact adjustment logic.


def test_generate_schedule_invalid_date_range(app, test_db):
    start_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ') # End before start
    data = {'start_date': start_date, 'end_date': end_date}
    response = app.test_client().post('/api/schedule', json=data)
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert response_data['error'] == 'End date must be after start date.'


def test_generate_schedule_no_tasks_to_schedule(app, test_db):
    # Ensure no tasks exist or they are outside the scheduling window
    start_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    data = {'start_date': start_date, 'end_date': end_date}
    response = app.test_client().post('/api/schedule', json=data)
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['message'] == 'No tasks to schedule for the given period.'
    assert len(response_data['scheduled_tasks']) == 0


@patch('backend.routes.generate_schedule')
def test_generate_schedule_scheduler_error(mock_generate_schedule, app, test_db):
    mock_generate_schedule.return_value = (None, "Internal scheduler error")
    start_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    data = {'start_date': start_date, 'end_date': end_date}
    response = app.test_client().post('/api/schedule', json=data)
    assert response.status_code == 500
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert response_data['error'] == 'Internal scheduler error'


def test_generate_schedule_missing_content_type(app, test_db):
    start_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    data_str = f'{{"start_date": "{start_date}", "end_date": "{end_date}"}}'
    response = app.test_client().post('/api/schedule', data=data_str, content_type='text/plain')
    assert response.status_code == 415 # Unsupported Media Type
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Unsupported Media Type' in response_data['error']


def test_generate_schedule_invalid_json(app, test_db):
    response = app.test_client().post('/api/schedule', data='not a json', content_type='application/json')
    assert response.status_code == 400 # Bad Request from Flask's get_json()
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Failed to decode JSON object' in response_data['error'] # Flask's default error

def test_generate_schedule_missing_dates(app, test_db):
    data = {} # Missing start_date and end_date
    response = app.test_client().post('/api/schedule', json=data)
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert response_data['error'] == 'Missing start_date or end_date in request body.'


# Tests for DELETE /api/schedule/clear
def test_clear_schedule_successful(app, test_db):
    # Create some scheduled tasks
    task1 = create_task(test_db, content='Scheduled Task 1', status='scheduled')
    task1.start = datetime.utcnow() # Manually set for test setup
    task1.end = datetime.utcnow() + timedelta(hours=1) # Manually set for test setup
    test_db.session.add(task1)

    task2 = create_task(test_db, content='Scheduled Task 2', status='scheduled')
    task2.start = datetime.utcnow() + timedelta(hours=1) # Manually set
    task2.end = datetime.utcnow() + timedelta(hours=2)   # Manually set
    test_db.session.add(task2)
    # Create an unscheduled task to ensure it's not affected
    task3 = create_task(test_db, content='Unscheduled Task', status='unscheduled')
    test_db.session.commit()


    response = app.test_client().delete('/api/schedule/clear')
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['message'] == 'All tasks set to unscheduled' # Updated expected message
    assert response_data['cleared_tasks_count'] == 2

    # Verify tasks are updated in DB
    updated_task1 = Task.query.get(task1.id)
    updated_task2 = Task.query.get(task2.id)
    unchanged_task3 = Task.query.get(task3.id)

    assert updated_task1.status == 'unscheduled'
    assert updated_task1.start is None # Check model fields 'start' and 'end'
    assert updated_task1.end is None

    assert updated_task2.status == 'unscheduled'
    assert updated_task2.start is None
    assert updated_task2.end is None

    assert unchanged_task3.status == 'unscheduled' # Should remain unchanged


def test_clear_schedule_no_scheduled_tasks(app, test_db):
    # Create only unscheduled tasks
    create_task(test_db, content='Unscheduled Task 1', status='unscheduled')
    create_task(test_db, content='Unscheduled Task 2', status='completed')

    response = app.test_client().delete('/api/schedule/clear')
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['message'] == 'No scheduled tasks to clear.'
    assert response_data['cleared_tasks_count'] == 0


def test_clear_schedule_no_tasks_at_all(app, test_db):
    # Ensure database is empty of tasks
    Task.query.delete()
    test_db.session.commit()

    response = app.test_client().delete('/api/schedule/clear')
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['message'] == 'No scheduled tasks to clear.' # Or 'No tasks found' depending on implementation
    assert response_data['cleared_tasks_count'] == 0
    # The current implementation specifically looks for 'scheduled' tasks to clear.
    # If there are no tasks at all, it means there are no 'scheduled' tasks.
    # So, 'No scheduled tasks to clear.' is the expected message.
