from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: int
    title: str
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class ActivityEvent(BaseModel):
    timestamp: datetime
    message: str
    event_type: str  # task_added, task_completed, task_deleted, system_metrics


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    timestamp: datetime = Field(default_factory=datetime.now)


class TaskCreate(BaseModel):
    title: str


class SSEEvent(BaseModel):
    type: str
    data: dict
    target: Optional[str] = None