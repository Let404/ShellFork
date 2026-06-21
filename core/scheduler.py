from collections import deque

from core.models import Task


class Scheduler:

    def __init__(self):
        self.running_task = None
        self.queue = deque()
        self.history = []

    def add(self, command: str, workflow_step_id: str | None = None):
        task = Task.create(
            command,
            workflow_step_id=workflow_step_id,
        )

        self.queue.append(task)

        return task

    def pop_next(self):
        if not self.queue:
            return None

        self.running_task = self.queue.popleft()

        return self.running_task

    def peek(self):
        if not self.queue:
            return None

        return self.queue[0]

    def is_empty(self):
        return len(self.queue) == 0

    def clear(self):
        self.queue.clear()

    def list(self):
        return list(self.queue)

    def complete(self, task):
        self.history.append(task)

        if self.running_task is task:
            self.running_task = None

    def history_list(self):
        return list(self.history)

    def all_tasks(self):
        tasks = self.history_list()

        if self.running_task is not None:
            tasks.append(self.running_task)

        tasks.extend(self.list())

        return tasks

    def remove_by_id(self, task_id: str):
        self.queue = deque(
            task for task in self.queue
            if task.id != task_id
        )

    def move_up(self, task_id: str):
        items = list(self.queue)

        for index, task in enumerate(items):
            if task.id == task_id and index > 0:
                items[index - 1], items[index] = items[index], items[index - 1]
                break

        self.queue = deque(items)

    def move_down(self, task_id: str):
        items = list(self.queue)

        for index, task in enumerate(items):
            if task.id == task_id and index < len(items) - 1:
                items[index + 1], items[index] = items[index], items[index + 1]
                break

        self.queue = deque(items)

    def active_tasks(self):
        tasks = []

        if self.running_task is not None:
            tasks.append(self.running_task)

        tasks.extend(self.list())

        return tasks

    def clear_history(self):
       self.history.clear()

    def add_workflow(self, workflow):
        tasks = []

        for step in workflow.flatten_command_steps():
            task = self.add(
                step.command,
                workflow_step_id=step.id,
            )

            tasks.append(task)

        return tasks

    def cancel_by_id(self, task_id: str):
        for task in list(self.queue):
            if task.id == task_id:
                self.queue.remove(task)

                task.status = (
                    task.status.CANCELLED
                )

                self.history.append(task)

                return task

        return None

    def find_by_id(self, task_id):
        for task in self.all_tasks():
            if task.id == task_id:
                return task

        return None