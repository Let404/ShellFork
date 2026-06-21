from dataclasses import dataclass, field
from typing import Any

from uuid import uuid4

from enum import Enum


WORKFLOW_FILE_TYPE = "shellfork.workflow"
WORKFLOW_VERSION = 1
WORKFLOW_EXTENSION = ".sfw"


class StepStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    type: str
    id: str = field(default_factory=lambda: str(uuid4()))
    status: str = StepStatus.QUEUED.value

    command: str | None = None
    name: str | None = None
    steps: list["WorkflowStep"] = field(default_factory=list)

    @classmethod
    def command_step(
        cls,
        command: str,
        step_id: str | None = None,
        status: str = StepStatus.QUEUED.value,
    ):
        return cls(
            id=step_id or str(uuid4()),
            type="command",
            status=status,
            command=command,
        )

    @classmethod
    def workflow_step(
        cls,
        name: str,
        steps: list["WorkflowStep"],
        step_id: str | None = None,
        status: str = StepStatus.QUEUED.value,
    ):
        return cls(
            id=step_id or str(uuid4()),
            type="workflow",
            status=status,
            name=name,
            steps=steps,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        step_type = data.get("type")
        step_id = data.get("id")
        status = data.get(
            "status",
            StepStatus.QUEUED.value,
        )

        if step_type == "command":
            return cls.command_step(
                data.get("command", ""),
                step_id=step_id,
                status=status,
            )

        if step_type == "workflow":
            return cls.workflow_step(
                data.get("name", "Untitled Workflow"),
                [
                    cls.from_dict(step)
                    for step in data.get("steps", [])
                ],
                step_id=step_id,
                status=status,
            )

        raise ValueError(f"Unknown workflow step type: {step_type}")

    def to_dict(self):
        if self.type == "command":
            return {
                "id": self.id,
                "type": "command",
                "status": self.status,
                "command": self.command,
            }

        if self.type == "workflow":
            return {
                "id": self.id,
                "type": "workflow",
                "status": self.status,
                "name": self.name,
                "steps": [
                    step.to_dict()
                    for step in self.steps
                ],
            }

        raise ValueError(f"Unknown workflow step type: {self.type}")


@dataclass
class Workflow:
    name: str = "Untitled Workflow"
    status: str = StepStatus.QUEUED.value
    steps: list[WorkflowStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        if data.get("type") != WORKFLOW_FILE_TYPE:
            raise ValueError("Not a ShellFork workflow file")

        if data.get("version") != WORKFLOW_VERSION:
            raise ValueError(
                f"Unsupported workflow version: {data.get('version')}"
            )

        return cls(
            name=data.get("name", "Untitled Workflow"),
            status=data.get(
                "status",
                StepStatus.QUEUED.value,
            ),
            steps=[
                WorkflowStep.from_dict(step)
                for step in data.get("steps", [])
            ],
        )

    def to_dict(self):
        return {
            "type": WORKFLOW_FILE_TYPE,
            "version": WORKFLOW_VERSION,
            "name": self.name,
            "status": self.status,
            "steps": [
                step.to_dict()
                for step in self.steps
            ],
        }

    def add_command(self, command: str):
        self.steps.append(
            WorkflowStep.command_step(command)
        )

    def add_workflow(self, workflow: "Workflow"):
        self.steps.append(
            WorkflowStep.workflow_step(
                workflow.name,
                workflow.steps,
            )
        )

    def flatten_commands(self):
        commands = []

        for step in self.steps:
            self._flatten_step(step, commands)

        return commands

    def _flatten_step(self, step: WorkflowStep, commands: list[str]):
        if step.type == "command":
            commands.append(step.command)
            return

        if step.type == "workflow":
            for child in step.steps:
                self._flatten_step(child, commands)
            return

        raise ValueError(f"Unknown workflow step type: {step.type}")

    def find_step_by_id(
        self,
        step_id: str,
    ):
        for step in self.steps:
            result = self._find_step_by_id(
                step,
                step_id,
            )

            if result is not None:
                return result

        return None

    def _find_step_by_id(
        self,
        step,
        step_id,
    ):
        if step.id == step_id:
            return step

        if step.type == "workflow":
            for child in step.steps:
                result = self._find_step_by_id(
                    child,
                    step_id,
                )

                if result is not None:
                    return result

        return None

    def set_step_status(
        self,
        step_id,
        status,
    ):
        step = self.find_step_by_id(
            step_id
        )

        if step is None:
            return False

        step.status = status

        return True

    def flatten_command_steps(self):
        command_steps = []

        for step in self.steps:
            self._flatten_command_step(
                step,
                command_steps,
            )

        return command_steps


    def _flatten_command_step(self, step, command_steps):
        if step.type == "command":
            command_steps.append(step)
            return

        if step.type == "workflow":
            for child in step.steps:
                self._flatten_command_step(
                    child,
                    command_steps,
                )
            return

        raise ValueError(f"Unknown workflow step type: {step.type}")

    def propagate_statuses(self):
        child_statuses = [
            self._propagate_step_status(step)
            for step in self.steps
        ]

        if not child_statuses:
            self.status = StepStatus.QUEUED.value
        elif StepStatus.FAILED.value in child_statuses:
            self.status = StepStatus.FAILED.value
        elif StepStatus.RUNNING.value in child_statuses:
            self.status = StepStatus.RUNNING.value
        elif all(
            status == StepStatus.COMPLETED.value
            for status in child_statuses
        ):
            self.status = StepStatus.COMPLETED.value
        elif StepStatus.CANCELLED.value in child_statuses:
            self.status = StepStatus.CANCELLED.value
        else:
            self.status = StepStatus.QUEUED.value

        return self.status

    def _propagate_step_status(self, step):
        if step.type == "command":
            return step.status

        child_statuses = [
            self._propagate_step_status(child)
            for child in step.steps
        ]

        if not child_statuses:
            step.status = StepStatus.QUEUED.value
            return step.status

        if StepStatus.FAILED.value in child_statuses:
            step.status = StepStatus.FAILED.value
        elif StepStatus.RUNNING.value in child_statuses:
            step.status = StepStatus.RUNNING.value
        elif all(
            status == StepStatus.COMPLETED.value
            for status in child_statuses
        ):
            step.status = StepStatus.COMPLETED.value
        elif StepStatus.CANCELLED.value in child_statuses:
            step.status = StepStatus.CANCELLED.value
        else:
            step.status = StepStatus.QUEUED.value

        return step.status

    def reset_statuses(self):
        self.status = StepStatus.QUEUED.value

        for step in self.steps:
            self._reset_step_status(step)

    def _reset_step_status(self, step):
        step.status = StepStatus.QUEUED.value

        if step.type == "workflow":
            for child in step.steps:
                self._reset_step_status(child)