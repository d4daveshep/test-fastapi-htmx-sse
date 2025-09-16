import asyncio
import json
from datetime import datetime
from typing import List
import psutil
from models import SSEEvent, SystemMetrics, ActivityEvent


class EventBroadcaster:
    def __init__(self):
        self._clients: List[asyncio.Queue] = []
    
    def add_client(self) -> asyncio.Queue:
        client_queue = asyncio.Queue()
        self._clients.append(client_queue)
        return client_queue
    
    def remove_client(self, client_queue: asyncio.Queue):
        if client_queue in self._clients:
            self._clients.remove(client_queue)
    
    async def broadcast(self, event: SSEEvent):
        if not self._clients:
            return
        
        # Convert event to SSE format
        event_data = f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
        
        # Send to all connected clients
        disconnected_clients = []
        for client_queue in self._clients:
            try:
                await client_queue.put(event_data)
            except:
                disconnected_clients.append(client_queue)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.remove_client(client)
    
    async def broadcast_task_event(self, event_type: str, task_data: dict):
        activity_message = self._create_activity_message(event_type, task_data)
        
        # Broadcast activity event
        activity_event = SSEEvent(
            type="activity",
            data={
                "message": activity_message,
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type
            },
            target="activity-feed"
        )
        await self.broadcast(activity_event)
        
        # Broadcast task list update
        task_event = SSEEvent(
            type="task_update",
            data=task_data,
            target="task-list"
        )
        await self.broadcast(task_event)
    
    async def broadcast_system_metrics(self):
        try:
            # Get CPU percentage (non-blocking call)
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent
            )
            
            event = SSEEvent(
                type="system_metrics",
                data=metrics.model_dump(mode='json'),
                target="system-metrics"
            )
            await self.broadcast(event)
            print(f"Broadcasting metrics: CPU {cpu_percent}%, Memory {memory.percent}%")
        except Exception as e:
            print(f"Error getting system metrics: {e}")
    
    def _create_activity_message(self, event_type: str, task_data: dict) -> str:
        task_title = task_data.get("title", "Unknown Task")
        if event_type == "task_added":
            return f"➕ New task added: '{task_title}'"
        elif event_type == "task_completed":
            return f"✅ Task completed: '{task_title}'"
        elif event_type == "task_deleted":
            return f"🗑️ Task deleted: '{task_title}'"
        return f"Task updated: '{task_title}'"


# Global broadcaster instance
broadcaster = EventBroadcaster()


async def start_metrics_task():
    """Background task to broadcast system metrics every 2 seconds"""
    # Initialize CPU monitoring with a baseline reading
    psutil.cpu_percent()
    await asyncio.sleep(1)
    
    while True:
        await broadcaster.broadcast_system_metrics()
        await asyncio.sleep(2)