import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import Task, TaskCreate, SystemMetrics
from events import broadcaster, start_metrics_task


# In-memory task storage
tasks: Dict[int, Task] = {}
next_task_id = 1

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting metrics task...")
    metrics_task = asyncio.create_task(start_metrics_task())
    print("Metrics task started")
    
    # Store the task in app state so we can cancel it later
    app.state.metrics_task = metrics_task
    
    yield
    
    # Shutdown
    print("Shutting down metrics task...")
    metrics_task.cancel()
    try:
        await metrics_task
    except asyncio.CancelledError:
        pass
    print("Metrics task stopped")

app = FastAPI(title="Real-Time Task Monitor", lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tasks": list(tasks.values())
    })


@app.post("/tasks")
async def add_task(request: Request, title: str = Form(...)):
    global next_task_id
    
    task = Task(id=next_task_id, title=title)
    tasks[next_task_id] = task
    next_task_id += 1
    
    # Broadcast task creation event
    await broadcaster.broadcast_task_event("task_added", task.model_dump(mode='json'))
    

    
    # Return updated task list
    return templates.TemplateResponse("task_list.html", {
        "request": request,
        "tasks": list(tasks.values())
    })


@app.put("/tasks/{task_id}/complete")
async def complete_task(task_id: int, request: Request):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    task.completed = True
    
    # Broadcast task completion event
    await broadcaster.broadcast_task_event("task_completed", task.model_dump(mode='json'))
    

    
    # Return updated task list
    return templates.TemplateResponse("task_list.html", {
        "request": request,
        "tasks": list(tasks.values())
    })


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, request: Request):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks.pop(task_id)
    
    # Broadcast task deletion event
    await broadcaster.broadcast_task_event("task_deleted", task.model_dump(mode='json'))
    

    
    # Return updated task list
    return templates.TemplateResponse("task_list.html", {
        "request": request,
        "tasks": list(tasks.values())
    })


@app.get("/tasks")
async def get_tasks(request: Request):
    return templates.TemplateResponse("task_list.html", {
        "request": request,
        "tasks": list(tasks.values())
    })


@app.get("/events/activity")
async def stream_activity_events(request: Request):
    async def event_publisher():
        client_queue = broadcaster.add_activity_client()
        try:
            while True:
                try:
                    event_data = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield event_data
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            broadcaster.remove_activity_client(client_queue)
            raise
        finally:
            broadcaster.remove_activity_client(client_queue)
    
    return StreamingResponse(
        event_publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/events/metrics")
async def stream_metrics_events(request: Request):
    async def event_publisher():
        client_queue = broadcaster.add_metrics_client()
        try:
            while True:
                try:
                    event_data = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield event_data
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            broadcaster.remove_metrics_client(client_queue)
            raise
        finally:
            broadcaster.remove_metrics_client(client_queue)
    
    return StreamingResponse(
        event_publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )













@app.get("/test-sse")
async def test_sse_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SSE Test - HTMX 2.x</title>
        <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.7/dist/htmx.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.2"></script>
    </head>
    <body>
        <h1>SSE Test - HTMX 2.x</h1>

        <h2>Metrics Test</h2>
        <div id="metrics-test" hx-ext="sse" sse-connect="/events/metrics" sse-swap="message">
            Waiting for metrics...
        </div>

        <h2>Activity Test</h2>
        <div id="activity-test" hx-ext="sse" sse-connect="/events/activity" sse-swap="message" hx-swap="afterbegin">
            Waiting for activity...
        </div>

        <h2>Test Controls</h2>
        <button onclick="createTestTask()">Create Test Task</button>

        <div id="console" style="margin-top: 20px; padding: 10px; background: #f0f0f0;">
            Console will show events here...<br>
        </div>

        <script>
            function createTestTask() {
                fetch('/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'title=Test from debug page'
                }).then(() => {
                    document.getElementById('console').innerHTML += '<div>Task created via fetch</div>';
                });
            }

            // Add debugging for HTMX 2.x SSE
            document.addEventListener('htmx:sseOpen', function(e) {
                console.log('SSE Connected', e);
                document.getElementById('console').innerHTML += '<div>SSE Connected to: ' + e.detail.elt.getAttribute('sse-connect') + '</div>';
            });
            document.addEventListener('htmx:sseMessage', function(e) {
                console.log('SSE Message', e);
                document.getElementById('console').innerHTML += '<div>SSE Message received on ' + e.detail.elt.id + ': ' + e.detail.message.substring(0, 50) + '...</div>';
            });
            document.addEventListener('htmx:sseError', function(e) {
                console.log('SSE Error', e);
                document.getElementById('console').innerHTML += '<div>SSE Error on ' + e.detail.elt.id + ': ' + JSON.stringify(e.detail.error) + '</div>';
            });
            document.addEventListener('htmx:sseClose', function(e) {
                console.log('SSE Closed', e);
                document.getElementById('console').innerHTML += '<div>SSE Closed on ' + e.detail.elt.id + '</div>';
            });

            // Debug HTMX extension loading
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('console').innerHTML += '<div>Page loaded, HTMX version: ' + htmx.version + '</div>';

                // Test direct EventSource for comparison
                document.getElementById('console').innerHTML += '<div>Testing direct EventSource to /events/metrics...</div>';
                const eventSource = new EventSource('/events/metrics');
                eventSource.onopen = function() {
                    document.getElementById('console').innerHTML += '<div>Direct EventSource: Connected to /events/metrics</div>';
                };
                eventSource.onmessage = function(event) {
                    document.getElementById('console').innerHTML += '<div>Direct EventSource Message: ' + event.data.substring(0, 50) + '...</div>';
                };
                eventSource.onerror = function(error) {
                    document.getElementById('console').innerHTML += '<div>Direct EventSource Error: ' + error + '</div>';
                };
            });
        </script>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
