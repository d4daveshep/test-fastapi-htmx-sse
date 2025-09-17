import asyncio
import json
from datetime import datetime
from typing import List
import psutil
from models import SSEEvent, SystemMetrics, ActivityEvent


class EventBroadcaster:
    def __init__(self):
        self._activity_clients: List[asyncio.Queue] = []
        self._metrics_clients: List[asyncio.Queue] = []
    
    def add_activity_client(self) -> asyncio.Queue:
        client_queue = asyncio.Queue()
        self._activity_clients.append(client_queue)
        return client_queue
    
    def remove_activity_client(self, client_queue: asyncio.Queue):
        if client_queue in self._activity_clients:
            self._activity_clients.remove(client_queue)
    
    def add_metrics_client(self) -> asyncio.Queue:
        client_queue = asyncio.Queue()
        self._metrics_clients.append(client_queue)
        return client_queue
    
    def remove_metrics_client(self, client_queue: asyncio.Queue):
        if client_queue in self._metrics_clients:
            self._metrics_clients.remove(client_queue)
    
    async def broadcast_activity(self, message: str, timestamp: str):
        if not self._activity_clients:
            return
        
        # Create activity HTML for HTMX
        activity_html = f'<div class="activity-item"><div>{message}</div><div class="timestamp">{timestamp}</div></div>'
        
        event_data = f"data: {activity_html}\n\n"
        
        # Send to all connected activity clients
        disconnected_clients = []
        for client_queue in self._activity_clients:
            try:
                await client_queue.put(event_data)
            except:
                disconnected_clients.append(client_queue)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.remove_activity_client(client)
    
    async def broadcast_metrics(self, cpu_percent: float, memory_percent: float):
        if not self._metrics_clients:
            return
        
        # Create metrics HTML for HTMX
        cpu_class = 'text-danger' if cpu_percent > 80 else 'text-primary'
        memory_class = 'text-danger' if memory_percent > 80 else 'text-success'
        metrics_html = f'<div class="row text-center"><div class="col-6"><div class="metric"><div class="h4 {cpu_class} mb-0">{cpu_percent:.1f}%</div><small class="text-muted">CPU %</small></div></div><div class="col-6"><div class="metric"><div class="h4 {memory_class} mb-0">{memory_percent:.1f}%</div><small class="text-muted">Memory %</small></div></div></div>'
        
        event_data = f"data: {metrics_html}\n\n"
        
        # Send to all connected metrics clients
        disconnected_clients = []
        for client_queue in self._metrics_clients:
            try:
                await client_queue.put(event_data)
            except:
                disconnected_clients.append(client_queue)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.remove_metrics_client(client)
    
    async def broadcast_task_event(self, event_type: str, task_data: dict):
        activity_message = self._create_activity_message(event_type, task_data)
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Broadcast activity event
        await self.broadcast_activity(activity_message, timestamp)
    
    async def broadcast_system_metrics(self):
        try:
            # Get CPU percentage (non-blocking call)
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            await self.broadcast_metrics(cpu_percent, memory.percent)
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