# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run application**: `uv run python main.py`
- **Install dependencies**: `uv add <package>`
- **Sync environment**: `uv sync`
- **Run single test**: `uv run python -m pytest tests/test_specific.py::test_function`
- **Run all tests**: `uv run python -m pytest`

## Application Architecture

This is a proof of concept application using real-time task monitoring application built with FastAPI, HTMX, and Server-Sent Events (SSE). The goal is to prove that FastAPI, HTMX and SSE can be used without custom javascript to achieve real-time updates to a web page. The architecture follows a simple three-layer pattern:

### Core Components

- **main.py**: FastAPI application with REST endpoints for task CRUD operations and SSE streaming endpoints (`/events/activity`, `/events/metrics`)
- **events.py**: EventBroadcaster class that manages SSE client connections and broadcasts real-time updates to connected clients
- **models.py**: Pydantic models for Task, SystemMetrics, ActivityEvent, and SSE events

### Real-Time Communication

The application uses two separate SSE streams:

- **Activity Stream** (`/events/activity`): Broadcasts task operations (add, complete, delete) with HTML content for HTMX
- **Metrics Stream** (`/events/metrics`): Broadcasts system CPU/memory usage every 2 seconds

### Frontend Integration

- Uses HTMX 2.0 with SSE extension for real-time UI updates
- Bootstrap 5 for styling with custom CSS in `static/style.css`
- Templates use Jinja2 with base template inheritance
- HTMX handles both form submissions and SSE updates seamlessly

### Key Implementation Details

- In-memory task storage with global `tasks` dictionary and `next_task_id` counter
- Background asyncio task for system metrics collection using psutil
- Event broadcaster maintains separate client queues for activity and metrics streams
- SSE events send pre-rendered HTML for direct DOM insertion via HTMX
- Application lifecycle management handles startup/shutdown of metrics task

### Development Notes

- Python 3.13+ required (see pyproject.toml)
- Uses `uv` for dependency management
- All HTML templates extend `base.html` and use Bootstrap components
- System metrics use color coding (red for >80% usage)
- SSE connections include heartbeat mechanism for connection reliability

