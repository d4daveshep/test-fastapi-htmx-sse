import asyncio
from collections import defaultdict
import random

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette import EventSourceResponse

app = FastAPI(title="Test SSE Events")


# Jinja2 templates
templates = Jinja2Templates(directory="templates")

event_queues: defaultdict[str, asyncio.Queue[str]] = defaultdict(asyncio.Queue)


class EventGenerator:
    def __init__(self) -> None:
        self.started: bool = False

    async def start(self, queues: defaultdict[str, asyncio.Queue[str]]) -> None:
        self.started = True
        while True:
            sleep_time: int = random.randint(5, 10)
            message: str = f"Event: sleeping for {sleep_time} secs"
            print(message)
            for queue in queues.values():
                await queue.put(message)
            await asyncio.sleep(float(sleep_time))


event_generator: EventGenerator = EventGenerator()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Start the event generator
    if not event_generator.started:
        task: asyncio.Task = asyncio.create_task(event_generator.start(event_queues))

    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/events/{name}")
async def async_events(request: Request, name: str) -> EventSourceResponse:
    async def event_publisher():
        # FIXME: try better error handling when terminating the app from the command line
        try:
            while True:
                event_queue: asyncio.Queue[str] = event_queues[name]
                event_data = await event_queue.get()
                event_queue.task_done()
                yield {"data": event_data}
        except asyncio.CancelledError as e:
            print(f"CancelledError: {str(e)}")
            raise
        finally:
            print("Finally!")

    return EventSourceResponse(event_publisher())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
