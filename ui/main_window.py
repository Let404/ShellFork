import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Vte", "3.91")

from gi.repository import Gtk, GLib, Gio, Vte

from ui.queue_panel import QueuePanel

from core.scheduler import Scheduler
from core.dispatcher import Dispatcher
from core.shell_monitor import ShellMonitor

from core.shell_state import ShellState

from core.workflow import (
    Workflow,
    WorkflowStep,
    StepStatus,
)

from core.workflow_io import (
    save_workflow,
    load_workflow,
)

from ui.workflow_tree import WorkflowTree

from datetime import datetime

from pathlib import Path


class MainWindow(Gtk.ApplicationWindow):

    def __init__(self, app):

        super().__init__(application=app)

        self.set_title("ShellFork")
        self.set_default_size(1200, 800)

        self.scheduler = Scheduler()

        self.current_workflow = Workflow()
        self.current_workflow_path = None

        self.workflow_dirty = False

        self.update_window_title()

        self.shell_state = ShellState.IDLE

        self.workflow_mode = False

        self.workflow_paused = False

        self.selected_workflow_path = None

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        self.set_child(root)

        menubar = self.create_menu_bar()
        root.append(menubar)

        outer_paned = Gtk.Paned.new(
            Gtk.Orientation.HORIZONTAL
        )

        outer_paned.set_vexpand(True)

        root.append(outer_paned)

        inner_paned = Gtk.Paned.new(
            Gtk.Orientation.HORIZONTAL
        )

        self.terminal = Vte.Terminal()

        self.shell_monitor = ShellMonitor()

        rcfile = self.shell_monitor.create_bash_rcfile()

        shell = "/bin/bash"

        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            None,
            [shell, "--rcfile", rcfile],
            [],
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            None,
        )

        self.dispatcher = Dispatcher(self.terminal)

        self.shell_monitor.connect(
            "ready",
            self.on_shell_ready,
        )

        GLib.timeout_add(
            200,
            self.shell_monitor.poll,
        )

        self.workflow_tree = WorkflowTree()
        self.workflow_tree.refresh(self.current_workflow)

        self.workflow_tree.connect(
            "selection-changed",
            self.on_workflow_selection_changed,
        )

        self.workflow_tree.connect(
            "add-command",
            self.on_workflow_add_command,
        )

        self.workflow_tree.connect(
            "add-workflow",
            self.on_workflow_add_workflow,
        )

        self.workflow_tree.connect(
            "move-node-up",
            self.on_workflow_move_node_up,
        )

        self.workflow_tree.connect(
            "move-node-down",
            self.on_workflow_move_node_down,
        )

        outer_paned.set_start_child(
            self.workflow_tree
        )

        self.queue_panel = QueuePanel()

        self.queue_panel.connect(
            "run-next",
            self.on_run_next,
        )

        self.queue_panel.connect(
            "clear-history",
            self.on_clear_history,
        )

        self.queue_panel.connect(
            "cancel-selected",
            self.on_cancel_selected,
        )

        self.queue_panel.connect(
            "pause-workflow",
            self.on_pause_workflow,
        )

        self.queue_panel.connect(
            "resume-workflow",
            self.on_resume_workflow,
        )

        self.workflow_tree.connect(
            "delete-node",
            self.on_workflow_delete_node,
        )

        self.workflow_tree.connect(
            "rename-node",
            self.on_workflow_rename_node,
        )

        self.queue_panel.connect(
            "stop-workflow",
            self.on_stop_workflow,
        )

        outer_paned.set_end_child(
            inner_paned
        )

        inner_paned.set_start_child(
            self.terminal
        )

        inner_paned.set_end_child(
            self.queue_panel
        )

        outer_paned.set_position(280)

        inner_paned.set_position(650)

    def on_shell_ready(self, monitor, exit_code):

        self.set_shell_state(
            ShellState.IDLE
        )

        print("Shell ready:", exit_code)

        if self.dispatcher.running_task is not None:
            if exit_code == 0:
                self.dispatcher.running_task.status = (
                    self.dispatcher.running_task.status.COMPLETED
                )

                self.set_workflow_step_status(
                    self.dispatcher.running_task.workflow_step_id,
                    StepStatus.COMPLETED.value,
                )
                self.dispatcher.running_task.exit_code = exit_code
                self.dispatcher.running_task.finished_at = datetime.now()

                self.scheduler.complete(
                    self.dispatcher.running_task
                )
            else:
                self.dispatcher.running_task.status = (
                    self.dispatcher.running_task.status.FAILED
                )

                self.set_workflow_step_status(
                    self.dispatcher.running_task.workflow_step_id,
                    StepStatus.FAILED.value,
                )

                self.dispatcher.running_task.exit_code = exit_code
                self.dispatcher.running_task.finished_at = datetime.now()

                self.scheduler.complete(
                    self.dispatcher.running_task
                )

                self.dispatcher.running_task = None
                self.workflow_mode = False

                self.refresh_queue_panel()

                return

            self.dispatcher.running_task.exit_code = exit_code
            self.dispatcher.running_task = None

        if self.workflow_paused:
            return

        if self.workflow_mode:
            self.run_next_if_available()
        elif not self.scheduler.is_empty():
            self.workflow_mode = True
            self.run_next_if_available()

    def run_next_if_available(self):
        task = self.scheduler.pop_next()

        if task is None:
            self.workflow_mode = False

            self.queue_panel.set_workflow_running(False)
            self.queue_panel.set_workflow_stoppable(False)

            self.set_shell_state(ShellState.IDLE)

            self.refresh_queue_panel()
            return

        self.set_shell_state(ShellState.RUNNING)

        self.set_workflow_step_status(
            task.workflow_step_id,
            StepStatus.RUNNING.value,
        )

        self.dispatcher.run(task)

        self.refresh_queue_panel()

    def on_run_next(self, panel):
        if not self.workflow_mode:
            self.current_workflow.reset_statuses()
            self.refresh_workflow_tree()

        self.workflow_mode = True
        self.run_next_if_available()

        self.queue_panel.set_workflow_running(True)
        self.queue_panel.set_workflow_stoppable(True)

    def set_shell_state(self, state):

        if self.shell_state == state:
            return

        self.shell_state = state

        print(
            "Shell state:",
            state.name,
        )

        if hasattr(self, "queue_panel"):
            self.queue_panel.set_status(state.name)

    def refresh_queue_panel(self):
        self.queue_panel.refresh(
            self.scheduler.active_tasks(),
            self.scheduler.history_list(),
        )

    def on_clear_history(self, panel):
        self.scheduler.clear_history()
        self.refresh_queue_panel()

    def queue_workflow(self, workflow: Workflow):
        self.scheduler.add_workflow(workflow)

        self.refresh_queue_panel()

        if self.shell_state == ShellState.IDLE:
            self.set_shell_state(ShellState.WAITING)

    def rebuild_workflow_from_queue(self):
        workflow = Workflow()

        for task in self.scheduler.active_tasks():
            workflow.add_command(
                task.command
            )

        self.current_workflow = workflow

    def new_workflow(self):
        self.scheduler.clear()
        self.scheduler.clear_history()

        self.current_workflow = Workflow()
        self.current_workflow_path = None

        self.workflow_mode = False

        self.refresh_queue_panel()

        self.set_shell_state(
            ShellState.IDLE
        )

        self.mark_workflow_clean()

        self.workflow_paused = False
        self.queue_panel.set_workflow_paused(False)

        self.refresh_workflow_tree()


    def load_workflow_file(self, path):
        workflow = load_workflow(path)

        self.scheduler.clear()
        self.scheduler.clear_history()

        self.scheduler.add_workflow(
            workflow
        )

        self.current_workflow = workflow
        self.current_workflow_path = path

        self.refresh_queue_panel()

        if not self.scheduler.is_empty():
            self.set_shell_state(
                ShellState.WAITING
            )
    
        self.mark_workflow_clean()

        self.workflow_paused = False
        self.queue_panel.set_workflow_paused(False)

        self.refresh_workflow_tree()

    def save_current_workflow(self):
        if self.current_workflow_path is None:
            raise RuntimeError(
                "Workflow has no path"
            )

        save_workflow(
            self.current_workflow,
            self.current_workflow_path,
        )

        self.mark_workflow_clean()


    def save_current_workflow_as(self, path):
        save_workflow(
            self.current_workflow,
            path,
        )

        self.current_workflow_path = path

        self.mark_workflow_clean()

    def create_menu_bar(self):
        self.create_actions()

        menu = Gio.Menu()

        file_menu = Gio.Menu()
        file_menu.append("New", "win.new-workflow")
        file_menu.append("Open…", "win.open-workflow")
        file_menu.append("Save", "win.save-workflow")
        file_menu.append("Save As…", "win.save-workflow-as")

        menu.append_submenu("File", file_menu)

        return Gtk.PopoverMenuBar.new_from_model(menu)

    def create_actions(self):
        actions = {
            "new-workflow": self.on_file_new,
            "open-workflow": self.on_file_open,
            "save-workflow": self.on_file_save,
            "save-workflow-as": self.on_file_save_as,
        }

        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def on_file_new(self, action, parameter):
        self.confirm_discard_changes(
            self.new_workflow
        )
        self.update_window_title()

    def on_file_open(self, action, parameter):
        self.confirm_discard_changes(
            self.show_open_workflow_dialog
        )

    def on_open_dialog_response(
        self,
        dialog,
        result,
    ):
        try:
            file = dialog.open_finish(
                result
            )
        except Exception:
            return

        path = file.get_path()

        self.load_workflow_file(
            path
        )

        self.update_window_title()

    def show_open_workflow_dialog(self):
        dialog = Gtk.FileDialog()

        dialog.set_title(
            "Open Workflow"
        )

        dialog.set_default_filter(
            self.create_workflow_file_filter()
        )

        dialog.open(
            self,
            None,
            self.on_open_dialog_response,
        )


    def on_file_save(self, action, parameter):
        if self.current_workflow_path is None:
            self.on_file_save_as(
                action,
                parameter,
            )
            return

        self.save_current_workflow()


    def on_file_save_as(self, action, parameter):
        dialog = Gtk.FileDialog()

        dialog.set_title(
            "Save Workflow"
        )

        dialog.set_default_filter(
            self.create_workflow_file_filter()
        )

        dialog.set_default_filter(
            self.create_workflow_file_filter()
        )

        dialog.save(
            self,
            None,
            self.on_save_dialog_response,
        )

    def on_save_dialog_response(
        self,
        dialog,
        result,
    ):
        try:
            file = dialog.save_finish(
                result
            )
        except Exception:
            return

        path = file.get_path()

        self.save_current_workflow_as(
            path
        )

        self.update_window_title()

    def update_window_title(self):
        if self.current_workflow_path is None:
            name = "Untitled"
        else:
            name = Path(
                self.current_workflow_path
            ).name

        if self.workflow_dirty:
            name += " *"

        self.set_title(
            f"ShellFork — {name}"
        )

    def mark_workflow_dirty(self):
        if self.workflow_dirty:
            return

        self.workflow_dirty = True
        self.update_window_title()


    def mark_workflow_clean(self):
        if not self.workflow_dirty:
            return

        self.workflow_dirty = False
        self.update_window_title()

    def create_workflow_file_filter(self):
        file_filter = Gtk.FileFilter()

        file_filter.set_name(
            "ShellFork Workflow (*.sfw)"
        )

        file_filter.add_pattern("*.sfw")

        return file_filter

    def confirm_discard_changes(self, on_confirm):
        if not self.workflow_dirty:
            on_confirm()
            return

        dialog = Gtk.AlertDialog()
        dialog.set_modal(True)
        dialog.set_message(
            "This workflow has unsaved changes."
        )
        dialog.set_detail(
            "Discard changes and continue?"
        )

        dialog.set_buttons([
            "Cancel",
            "Discard",
        ])

        dialog.set_cancel_button(0)
        dialog.set_default_button(1)

        dialog.choose(
            self,
            None,
            self.on_confirm_discard_response,
            on_confirm,
        )

    def on_confirm_discard_response(
        self,
        dialog,
        result,
        on_confirm,
    ):
        try:
            response = dialog.choose_finish(result)
        except Exception:
            return

        if response == 1:
            on_confirm()

    def on_cancel_selected(self, panel, task_id):
        task = self.scheduler.find_by_id(task_id)

        self.scheduler.cancel_by_id(task_id)

        if task is not None:
            self.set_workflow_step_status(
                task.workflow_step_id,
                StepStatus.CANCELLED.value,
            )

        self.mark_workflow_dirty()
        self.refresh_queue_panel()

        if self.scheduler.is_empty() and not self.workflow_mode:
            self.set_shell_state(ShellState.IDLE)

    def on_pause_workflow(self, panel):
        self.workflow_paused = True
        self.queue_panel.set_workflow_paused(True)


    def on_resume_workflow(self, panel):
        self.workflow_paused = False
        self.queue_panel.set_workflow_paused(False)

        if self.workflow_mode:
            self.run_next_if_available()

    def refresh_workflow_tree(self):
        self.workflow_tree.refresh(
            self.current_workflow
        )

    def on_workflow_selection_changed(
        self,
        tree,
        path,
    ):
        self.selected_workflow_path = path

        print(
            "Workflow selection:",
            path,
        )

    def on_workflow_add_command(self, tree, path):
        self.pending_add_command_path = path

        dialog = Gtk.Dialog(
            title="Add Command",
            transient_for=self,
            modal=True,
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Add",
            Gtk.ResponseType.OK,
        )

        content = dialog.get_content_area()

        entry = Gtk.Entry()
        entry.set_placeholder_text(
            "echo hello"
        )

        content.append(entry)

        dialog.connect(
            "response",
            self.on_add_command_dialog_response,
            entry,
        )

        dialog.present()

    def add_command_to_workflow_at_path(self, path, command):
        if path is None:
            path = []

        target_steps = self.workflow_steps_for_path(path)

        target_steps.append(
            WorkflowStep.command_step(command)
        )

    def workflow_steps_for_path(self, path):
        if path is None or path == []:
            return self.current_workflow.steps

        steps = self.current_workflow.steps

        for index in path:
            step = steps[index]

            if step.type != "workflow":
                return self.current_workflow.steps

            steps = step.steps

        return steps

    def regenerate_queue_from_workflow(self):
        self.scheduler.clear()

        self.scheduler.add_workflow(
            self.current_workflow
        )

        self.refresh_queue_panel()

        if self.scheduler.is_empty():
            self.set_shell_state(ShellState.IDLE)
        elif self.shell_state == ShellState.IDLE:
            self.set_shell_state(ShellState.WAITING)

    def on_add_command_dialog_response(
        self,
        dialog,
        response,
        entry,
    ):
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        command = entry.get_text().strip()

        dialog.destroy()

        if not command:
            return

        self.add_command_to_workflow_at_path(
            self.pending_add_command_path,
            command,
        )

        self.pending_add_command_path = None

        self.mark_workflow_dirty()
        self.refresh_workflow_tree()
        self.regenerate_queue_from_workflow()

    def on_workflow_add_workflow(
        self,
        tree,
        path,
    ):
        self.pending_add_workflow_path = path

        dialog = Gtk.Dialog(
            title="Add Workflow",
            transient_for=self,
            modal=True,
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Add",
            Gtk.ResponseType.OK,
        )

        content = dialog.get_content_area()

        entry = Gtk.Entry()
        entry.set_placeholder_text(
            "Workflow Name"
        )

        content.append(entry)

        dialog.connect(
            "response",
            self.on_add_workflow_dialog_response,
            entry,
        )

        dialog.present()

    def on_add_workflow_dialog_response(
        self,
        dialog,
        response,
        entry,
    ):
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        name = entry.get_text().strip()

        dialog.destroy()

        if not name:
            return

        self.add_workflow_to_workflow_at_path(
            self.pending_add_workflow_path,
            name,
        )

        self.pending_add_workflow_path = None

        self.mark_workflow_dirty()
        self.refresh_workflow_tree()
        self.regenerate_queue_from_workflow()

    def add_workflow_to_workflow_at_path(
        self,
        path,
        name,
    ):
        if path is None:
            path = []

        target_steps = self.workflow_steps_for_path(
            path
        )

        target_steps.append(
            WorkflowStep.workflow_step(
                name,
                [],
            )
        )

    def on_workflow_delete_node(
        self,
        tree,
        path,
    ):
        if path is None:
            return

        if path == []:
            return

        self.delete_workflow_node(path)

        self.selected_workflow_path = None
        self.workflow_tree.selected_path = None

        self.mark_workflow_dirty()
        self.refresh_workflow_tree()
        self.regenerate_queue_from_workflow()

    def delete_workflow_node(self, path):
        parent_path = path[:-1]

        index = path[-1]

        if parent_path == []:
            steps = self.current_workflow.steps
        else:
            steps = self.workflow_steps_for_path(
                parent_path
            )

        if 0 <= index < len(steps):
            del steps[index]

    def on_workflow_rename_node(
        self,
        tree,
        path,
    ):
        if path is None:
            return

        current_value = self.workflow_node_display_name(
            path
        )

        dialog = Gtk.Dialog(
            title="Rename / Edit",
            transient_for=self,
            modal=True,
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Save",
            Gtk.ResponseType.OK,
        )

        content = dialog.get_content_area()

        entry = Gtk.Entry()
        entry.set_text(current_value)

        content.append(entry)

        dialog.connect(
            "response",
            self.on_rename_dialog_response,
            path,
            entry,
        )

        dialog.present()

    def on_rename_dialog_response(
        self,
        dialog,
        response,
        path,
        entry,
    ):
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        value = entry.get_text().strip()

        dialog.destroy()

        if not value:
            return

        self.rename_workflow_node(
            path,
            value,
        )

        self.mark_workflow_dirty()
        self.refresh_workflow_tree()
        self.regenerate_queue_from_workflow()

    def workflow_node_display_name(
        self,
        path,
    ):
        if path == []:
            return self.current_workflow.name

        node = self.workflow_node_at_path(
            path
        )

        if node.type == "workflow":
            return node.name

        return node.command

    def workflow_node_at_path(
        self,
        path,
    ):
        steps = self.current_workflow.steps

        node = None

        for index in path:
            node = steps[index]

            if node.type == "workflow":
                steps = node.steps

        return node

    def rename_workflow_node(
        self,
        path,
        value,
    ):
        if path == []:
            self.current_workflow.name = value
            return

        node = self.workflow_node_at_path(
            path
        )

        if node.type == "workflow":
            node.name = value
        else:
            node.command = value

    def on_workflow_move_node_up(self, tree, path):
        self.move_workflow_node(path, direction=-1)


    def on_workflow_move_node_down(self, tree, path):
        self.move_workflow_node(path, direction=1)

    def move_workflow_node(self, path, direction):
        if path is None or path == []:
            return

        parent_path = path[:-1]
        index = path[-1]

        if parent_path == []:
            steps = self.current_workflow.steps
        else:
            steps = self.workflow_steps_for_path(parent_path)

        new_index = index + direction

        if new_index < 0 or new_index >= len(steps):
            return

        steps[index], steps[new_index] = steps[new_index], steps[index]

        new_path = parent_path + [new_index]

        self.selected_workflow_path = new_path
        self.workflow_tree.selected_path = new_path

        self.mark_workflow_dirty()
        self.refresh_workflow_tree()
        self.regenerate_queue_from_workflow()

    def set_workflow_step_status(
        self,
        step_id,
        status,
    ):
        if step_id is None:
            return

        self.current_workflow.set_step_status(
            step_id,
            status,
        )

        self.current_workflow.propagate_statuses()

        self.refresh_workflow_tree()

    def on_stop_workflow(self, panel):
        self.workflow_mode = False
        self.workflow_paused = False

        self.queue_panel.set_workflow_paused(False)
        self.queue_panel.set_workflow_running(False)
        self.queue_panel.set_workflow_stoppable(False)

        self.scheduler.clear()

        self.current_workflow.reset_statuses()

        self.refresh_queue_panel()
        self.refresh_workflow_tree()

        self.set_shell_state(
            ShellState.IDLE
        )