from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
import uuid


class TaskStatus(Enum):
    QUEUED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class Task:
    id: str
    command: str
    status: TaskStatus = TaskStatus.QUEUED
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    workflow_step_id: str | None = None

    @classmethod
    def create(cls, command: str, workflow_step_id: str | None = None):
        return cls(
            id=str(uuid.uuid4()),
            command=command.strip(),
            workflow_step_id=workflow_step_id,
        )

    def duration_seconds(self):
        if self.started_at is None or self.finished_at is None:
            return None

        return (self.finished_at - self.started_at).total_seconds()