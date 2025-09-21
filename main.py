import asyncio
from sse_starlette import EventSourceResponse, event
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
    return templates.TemplateResponse(
        "index.html", {"request": request, "tasks": list(tasks.values())}
    )


@app.post("/tasks")
async def add_task(request: Request, title: str = Form(...)):
    global next_task_id

    task = Task(id=next_task_id, title=title)
    tasks[next_task_id] = task
    next_task_id += 1

    # Broadcast task creation event
    await broadcaster.broadcast_task_event("task_added", task.model_dump(mode="json"))

    # Return updated task list
    return templates.TemplateResponse(
        "task_list.html", {"request": request, "tasks": list(tasks.values())}
    )


@app.put("/tasks/{task_id}/complete")
async def complete_task(task_id: int, request: Request):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    task.completed = True

    # Broadcast task completion event
    await broadcaster.broadcast_task_event(
        "task_completed", task.model_dump(mode="json")
    )

    # Return updated task list
    return templates.TemplateResponse(
        "task_list.html", {"request": request, "tasks": list(tasks.values())}
    )


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, request: Request):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks.pop(task_id)

    # Broadcast task deletion event
    await broadcaster.broadcast_task_event("task_deleted", task.model_dump(mode="json"))

    # Return updated task list
    return templates.TemplateResponse(
        "task_list.html", {"request": request, "tasks": list(tasks.values())}
    )


@app.get("/tasks")
async def get_tasks(request: Request):
    return templates.TemplateResponse(
        "task_list.html", {"request": request, "tasks": list(tasks.values())}
    )


@app.get("/events/activity")
async def stream_activity_events(request: Request) -> EventSourceResponse:
    async def event_publisher():
        client_queue = broadcaster.add_activity_client()
        try:
            while True:
                try:
                    event_data = await asyncio.wait_for(
                        client_queue.get(), timeout=30.0
                    )
                    yield event_data
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            broadcaster.remove_activity_client(client_queue)
            raise
        finally:
            broadcaster.remove_activity_client(client_queue)

    return EventSourceResponse(event_publisher())
    # return StreamingResponse(
    #     event_publisher(),
    #     media_type="text/event-stream",
    #     headers={
    #         "Cache-Control": "no-cache",
    #         "Connection": "keep-alive",
    #     },
    # )


@app.get("/events/metrics")
async def stream_metrics_events(request: Request) -> EventSourceResponse:
    async def event_publisher():
        # FIXME: try removing the broadcaster stuff entirely and just get the raw metrics here and return
        client_queue = broadcaster.add_metrics_client()
        try:
            while True:
                try:
                    event_data = await asyncio.wait_for(
                        client_queue.get(), timeout=30.0
                    )
                    yield event_data
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            broadcaster.remove_metrics_client(client_queue)
            raise
        finally:
            broadcaster.remove_metrics_client(client_queue)

    return EventSourceResponse(event_publisher())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
