import asyncio
import random

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette import EventSourceResponse

app = FastAPI(title="Test SSE Events")


# Jinja2 templates
templates = Jinja2Templates(directory="templates")

event_queue: asyncio.Queue[str] = asyncio.Queue()


class EventGenerator:
    async def start(self, queue: asyncio.Queue) -> None:
        while True:
            sleep_time: int = random.randint(5, 10)
            message: str = f"Event: sleeping for {sleep_time} secs"
            print(message)
            await queue.put(message)
            await asyncio.sleep(float(sleep_time))


event_generator: EventGenerator = EventGenerator()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Start the event generator
    # await event_generator.start(event_queue)

    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/events/{name}")
async def async_events(request: Request, name: str) -> EventSourceResponse:
    async def event_publisher():
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
        except asyncio.CancelledError as e:
            print(f"CancelledError: {str(e)}")
            raise
        finally:
            print("Finally!")

    return EventSourceResponse(event_publisher())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
