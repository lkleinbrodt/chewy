# Scheduler Tests

This directory contains tests for the Chewbacca task scheduler system.

## Overview

The scheduler is responsible for automatically scheduling tasks based on:

- Calendar events (avoiding conflicts)
- Task dependencies (ensuring tasks are done in the correct order)
- Due dates (prioritizing urgent tasks)
- Work hours (scheduling only during configured work hours)
- Recurring tasks (generating instances for recurring events)

## Running Tests

To run all tests:

```bash
cd backend
pytest tests/
```

To run specific test files:

```bash
pytest tests/test_scheduler.py
```

To run specific test cases:

```bash
pytest tests/test_scheduler.py::TestScheduler::test_empty_schedule
```

## Test Structure

The tests are organized into the following files:

- `test_scheduler.py`: Main pytest tests for the scheduler functionality
- `deprecated_scheduler_tests.py`: Old testing functions (kept for reference)

## Test Database

Tests use an in-memory SQLite database configured in `TestingConfig`. This ensures tests don't affect your production database.

## Adding New Tests

When adding new tests:

1. Add them to the appropriate test class in `test_scheduler.py`
2. Follow the pytest fixture pattern used in existing tests
3. Make sure to clean up any created data in the test database

## Debugging Failed Tests

If a test fails, you can run it with the `-v` flag for more verbose output:

```bash
pytest tests/test_scheduler.py -v
```

For even more detailed output, use:

```bash
pytest tests/test_scheduler.py -vv
```
