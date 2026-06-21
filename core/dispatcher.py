from core.models import Task, TaskStatus
from datetime import datetime


class Dispatcher:

    def __init__(self, terminal):
        self.terminal = terminal
        self.running_task = None

    def install_shell_integration(self, command: str):
        self.terminal.feed_child(
            (command + "\n").encode("utf-8")
        )

    def run(self, task: Task):
        self.running_task = task

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        command = task.command

        if not command.endswith("\n"):
            command += "\n"

        self.terminal.feed_child(
            command.encode("utf-8")
        )