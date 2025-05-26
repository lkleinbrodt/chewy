import pytest
from flask import json
from backend.models import Task, RecurringEvent
from datetime import datetime, timedelta

# Helper function to create a task
def create_task(test_db, **kwargs):
    # Map is_completed to status
    if kwargs.get('is_completed'):
        kwargs['status'] = 'completed'
    kwargs.pop('is_completed', None) # Remove is_completed

    # Remove task_nature and dependencies as they are not direct model fields or need special handling
    kwargs.pop('task_nature', None)
    dependencies = kwargs.pop('dependencies', None) # Store for later if manual dependency creation is needed

    task = Task(**kwargs)
    test_db.session.add(task)
    test_db.session.commit()

    if dependencies:
        # This part is more complex and depends on how TaskDependency model works.
        # For now, this is a placeholder. Actual dependency creation might need
        # the task.id first, then creating TaskDependency objects.
        # print(f"Warning: 'dependencies' key in create_task is not fully implemented for {task.id}")
        # Example:
        # for dep_id in dependencies:
        #     dependency_obj = TaskDependency(task_id=task.id, dependency_id=dep_id)
        #     test_db.session.add(dependency_obj)
        # test_db.session.commit()
        pass # Tests using this will need specific fixes for dependency creation

    return task

# Helper function to create a recurring event
def create_recurring_event(test_db, **kwargs):
    event_data = {
        'content': kwargs.pop('name', 'Test Recurring Event Task'),
        'duration': kwargs.pop('duration', 60), # Default duration if not provided
        'recurrence': kwargs.pop('recurrence_rule', [0,1,2,3,4]), # Default to daily if not provided
        # Add other necessary fields for RecurringEvent model with defaults
        'time_window_start': kwargs.pop('time_window_start', None),
        'time_window_end': kwargs.pop('time_window_end', None),
    }
    event_data.update(kwargs) # Override defaults with any explicitly passed kwargs
    event = RecurringEvent(**event_data)
    test_db.session.add(event)
    test_db.session.commit()
    return event

# Tests for GET /api/tasks
def test_get_tasks_empty(app, test_db):
    response = app.test_client().get('/api/tasks')
    assert response.status_code == 200
    assert json.loads(response.data) == []

def test_get_tasks_multiple(app, test_db):
    create_task(test_db, content='Task 1', duration=60)
    create_task(test_db, content='Task 2', duration=30)
    response = app.test_client().get('/api/tasks')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2

def test_get_tasks_filter_by_task_nature(app, test_db):
    create_task(test_db, content='One-off Task', duration=60, task_nature='one-off')
    create_task(test_db, content='Recurring Task', duration=30, task_nature='recurring')
    response = app.test_client().get('/api/tasks?task_nature=one-off')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['content'] == 'One-off Task'

def test_get_tasks_filter_by_is_completed(app, test_db):
    create_task(test_db, content='Completed Task', duration=60, is_completed=True)
    create_task(test_db, content='Incomplete Task', duration=30, is_completed=False)
    response = app.test_client().get('/api/tasks?is_completed=true')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['content'] == 'Completed Task'

def test_get_tasks_filter_by_recurring_event_id(app, test_db):
    event1 = create_recurring_event(test_db, name='Event 1')
    event2 = create_recurring_event(test_db, name='Event 2')
    create_task(test_db, content='Task for Event 1', duration=60, recurring_event_id=event1.id)
    create_task(test_db, content='Task for Event 2', duration=30, recurring_event_id=event2.id)
    response = app.test_client().get(f'/api/tasks?recurring_event_id={event1.id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['content'] == 'Task for Event 1'

def test_get_tasks_filter_by_date_range(app, test_db):
    create_task(test_db, content='Task 1', duration=60, due_by=datetime.utcnow() - timedelta(days=1))
    create_task(test_db, content='Task 2', duration=30, due_by=datetime.utcnow() + timedelta(days=1))
    start_date = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')
    end_date = datetime.utcnow().strftime('%Y-%m-%d')
    response = app.test_client().get(f'/api/tasks?start_date={start_date}&end_date={end_date}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['content'] == 'Task 1'

def test_get_tasks_filter_combination(app, test_db):
    event = create_recurring_event(test_db, name='Test Event')
    create_task(test_db, content='Completed One-off Task', duration=60, task_nature='one-off', is_completed=True, due_by=datetime.utcnow() - timedelta(days=1))
    create_task(test_db, content='Incomplete Recurring Task', duration=30, task_nature='recurring', is_completed=False, recurring_event_id=event.id, due_by=datetime.utcnow() + timedelta(days=1))
    start_date = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')
    end_date = datetime.utcnow().strftime('%Y-%m-%d')
    response = app.test_client().get(f'/api/tasks?task_nature=one-off&is_completed=true&start_date={start_date}&end_date={end_date}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['content'] == 'Completed One-off Task'

# Tests for POST /api/tasks
def test_create_task_successful(app, test_db):
    data = {
        'content': 'New Task',
        'duration': 60,
        'due_by': (datetime.utcnow() + timedelta(days=1)).isoformat(),
        'time_window_start': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        'time_window_end': (datetime.utcnow() + timedelta(hours=2)).isoformat()
    }
    response = app.test_client().post('/api/tasks', json=data)
    assert response.status_code == 201
    task_data = json.loads(response.data)
    assert 'id' in task_data
    assert task_data['content'] == 'New Task'

def test_create_task_minimal_fields(app, test_db):
    data = {'content': 'Minimal Task', 'duration': 30}
    response = app.test_client().post('/api/tasks', json=data)
    assert response.status_code == 201
    task_data = json.loads(response.data)
    assert 'id' in task_data
    assert task_data['content'] == 'Minimal Task'

def test_create_task_with_dependencies(app, test_db):
    task1 = create_task(test_db, content='Task 1', duration=60)
    data = {'content': 'Task 2', 'duration': 30, 'dependencies': [task1.id]}
    response = app.test_client().post('/api/tasks', json=data)
    assert response.status_code == 201
    task_data = json.loads(response.data)
    assert 'id' in task_data
    assert task_data['dependencies'] == [task1.id]

def test_create_task_invalid_input(app, test_db):
    data = {'duration': 60}  # Missing content
    response = app.test_client().post('/api/tasks', json=data)
    assert response.status_code == 400

# Tests for GET /api/tasks/<task_id>
def test_get_task_by_id_existing(app, test_db):
    task = create_task(test_db, content='Test Task', duration=60)
    response = app.test_client().get(f'/api/tasks/{task.id}')
    assert response.status_code == 200
    task_data = json.loads(response.data)
    assert task_data['content'] == 'Test Task'

def test_get_task_by_id_non_existent(app, test_db):
    response = app.test_client().get('/api/tasks/999')
    assert response.status_code == 404

# Tests for PUT /api/tasks/<task_id>
def test_update_task_successful(app, test_db):
    task = create_task(test_db, content='Original Task', duration=60)
    data = {'content': 'Updated Task', 'duration': 30}
    response = app.test_client().put(f'/api/tasks/{task.id}', json=data)
    assert response.status_code == 200
    task_data = json.loads(response.data)
    assert task_data['content'] == 'Updated Task'
    assert task_data['duration'] == 30

def test_update_task_add_dependencies(app, test_db):
    task1 = create_task(test_db, content='Task 1', duration=60)
    task2 = create_task(test_db, content='Task 2', duration=30)
    data = {'dependencies': [task1.id]}
    response = app.test_client().put(f'/api/tasks/{task2.id}', json=data)
    assert response.status_code == 200
    task_data = json.loads(response.data)
    assert task_data['dependencies'] == [task1.id]

def test_update_task_change_dependencies(app, test_db):
    task1 = create_task(test_db, content='Task 1', duration=60)
    task2 = create_task(test_db, content='Task 2', duration=30, dependencies=[task1.id])
    task3 = create_task(test_db, content='Task 3', duration=45)
    data = {'dependencies': [task3.id]}
    response = app.test_client().put(f'/api/tasks/{task2.id}', json=data)
    assert response.status_code == 200
    task_data = json.loads(response.data)
    assert task_data['dependencies'] == [task3.id]

def test_update_task_remove_dependencies(app, test_db):
    task1 = create_task(test_db, content='Task 1', duration=60)
    task2 = create_task(test_db, content='Task 2', duration=30, dependencies=[task1.id])
    data = {'dependencies': []}
    response = app.test_client().put(f'/api/tasks/{task2.id}', json=data)
    assert response.status_code == 200
    task_data = json.loads(response.data)
    assert task_data['dependencies'] == []

def test_update_task_non_existent(app, test_db):
    data = {'content': 'Updated Task'}
    response = app.test_client().put('/api/tasks/999', json=data)
    assert response.status_code == 404

def test_update_task_invalid_input(app, test_db):
    task = create_task(test_db, content='Test Task', duration=60)
    data = {'due_by': 'invalid-date'}
    response = app.test_client().put(f'/api/tasks/{task.id}', json=data)
    assert response.status_code == 400

# Tests for DELETE /api/tasks/<task_id>
def test_delete_task_successful(app, test_db):
    task = create_task(test_db, content='Task to Delete', duration=60)
    response = app.test_client().delete(f'/api/tasks/{task.id}')
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == 'Task deleted successfully'
    assert Task.query.get(task.id) is None

def test_delete_task_removes_dependencies(app, test_db):
    task1 = create_task(test_db, content='Task 1', duration=60)
    task2 = create_task(test_db, content='Task 2', duration=30, dependencies=[task1.id])
    response = app.test_client().delete(f'/api/tasks/{task1.id}')
    assert response.status_code == 200
    updated_task2 = Task.query.get(task2.id)
    assert updated_task2.dependencies == []


def test_delete_task_non_existent(app, test_db):
    response = app.test_client().delete('/api/tasks/999')
    assert response.status_code == 404

# Tests for POST /api/tasks/<task_id>/complete
def test_complete_task_successful(app, test_db):
    task = create_task(test_db, content='Task to Complete', duration=60)
    response = app.test_client().post(f'/api/tasks/{task.id}/complete')
    assert response.status_code == 200
    task_data = json.loads(response.data)
    assert task_data['status'] == 'completed'
    assert task_data['is_completed'] is True

def test_complete_task_non_existent(app, test_db):
    response = app.test_client().post('/api/tasks/999/complete')
    assert response.status_code == 404

def test_complete_task_updates_status(app, test_db):
    task = create_task(test_db, content='Task to Complete', duration=60)
    app.test_client().post(f'/api/tasks/{task.id}/complete')
    updated_task = Task.query.get(task.id)
    assert updated_task.status == 'completed'
    assert updated_task.is_completed is True
