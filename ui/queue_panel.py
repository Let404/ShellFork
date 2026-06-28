import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject, GLib


class QueuePanel(Gtk.Box):

    __gsignals__ = {
        "run-next": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
        "clear-history": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
        "cancel-selected": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str,),
        ),

        "pause-workflow": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),

        "resume-workflow": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
        "stop-workflow": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
    }

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )

        title = Gtk.Label(label="Queue")
        title.set_xalign(0)

        self.append(title)

        self.workflow_paused = False

        self.status_label = Gtk.Label(label="Status: IDLE")
        self.status_label.set_xalign(0)

        self.append(self.status_label)

        self.queue_listbox = Gtk.ListBox()

        self.queue_scroll = Gtk.ScrolledWindow()
        self.queue_scroll.set_vexpand(True)
        self.queue_scroll.set_child(self.queue_listbox)

        self.append(self.queue_scroll)

        history_title = Gtk.Label(label="History")
        history_title.set_xalign(0)

        self.append(history_title)

        self.history_listbox = Gtk.ListBox()

        self.history_scroll = Gtk.ScrolledWindow()
        self.history_scroll.set_vexpand(True)
        self.history_scroll.set_child(self.history_listbox)

        self.append(self.history_scroll)

        clear_history_button = Gtk.Button(label="Clear History")
        clear_history_button.connect(
            "clicked",
            self.on_clear_history_clicked,
        )

        self.append(clear_history_button)

        self.append(Gtk.Separator())

        self.run_button = Gtk.Button(label="▶ Run Workflow")
        self.run_button.connect(
            "clicked",
            self.on_run_next_clicked,
        )
        self.append(self.run_button)

        self.pause_resume_button = Gtk.Button(label="⏸ Pause")
        self.pause_resume_button.connect(
            "clicked",
            self.on_pause_resume_clicked,
        )
        self.append(self.pause_resume_button)

        self.stop_button = Gtk.Button(label="⏹ Stop")
        self.stop_button.set_sensitive(False)
        self.stop_button.connect(
            "clicked",
            self.on_stop_workflow_clicked,
        )
        self.append(self.stop_button)

        cancel_button = Gtk.Button(label="Cancel Selected")
        cancel_button.connect(
            "clicked",
            self.on_cancel_selected_clicked,
        )
        self.append(cancel_button)

    def on_run_next_clicked(self, widget):

        self.emit("run-next")

    def on_clear_history_clicked(self, widget):
        self.emit("clear-history")

    def refresh(self, queue_tasks, history_tasks):
        self.refresh_listbox(
            self.queue_listbox,
            queue_tasks,
            selectable=True,
        )

        self.refresh_listbox(
            self.history_listbox,
            history_tasks,
            selectable=False,
        )

        GLib.timeout_add(
            50,
            self.scroll_to_bottom,
        )

    def refresh_listbox(self, listbox, tasks, selectable):
        child = listbox.get_first_child()

        while child:
            next_child = child.get_next_sibling()
            listbox.remove(child)
            child = next_child

        for task in tasks:
            row = Gtk.ListBoxRow()
            row.task_id = task.id

            row.set_selectable(selectable)

            row_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=2,
            )

            command_label = Gtk.Label(
                label=f"{self.status_icon(task.status)} {task.command}"
            )
            command_label.set_xalign(0)

            row_box.append(command_label)

            metadata = self.task_metadata(task)

            if metadata:
                metadata_label = Gtk.Label(label=metadata)
                metadata_label.set_xalign(0)
                metadata_label.add_css_class("dim-label")

                row_box.append(metadata_label)

            row.set_child(row_box)

            listbox.append(row)

    def set_status(self, text):
        self.status_label.set_text(f"Status: {text}")

    def get_selected_task_id(self):
        row = self.queue_listbox.get_selected_row()

        if row is None:
            return None

        return row.task_id

    def on_cancel_selected_clicked(self, widget):
        task_id = self.get_selected_task_id()

        if task_id is None:
            return

        self.emit("cancel-selected", task_id)

    def on_pause_resume_clicked(self, widget):
        if self.workflow_paused:
            self.emit("resume-workflow")
        else:
            self.emit("pause-workflow")


    def set_workflow_paused(self, paused):
        self.workflow_paused = paused

        if paused:
            self.pause_resume_button.set_label("▶ Resume")
        else:
            self.pause_resume_button.set_label("⏸ Pause")

    def status_icon(self, status):
        name = status.name

        if name == "QUEUED":
            return "○"

        if name == "RUNNING":
            return "▶"

        if name == "COMPLETED":
            return "✓"

        if name == "FAILED":
            return "✗"

        if name == "CANCELLED":
            return "⊘"

        return "?"

    def scroll_to_bottom(self):
        for scroll in (
            self.queue_scroll,
            self.history_scroll,
        ):
            adjustment = scroll.get_vadjustment()

            adjustment.set_value(
                adjustment.get_upper() - adjustment.get_page_size()
            )

        return False

    def task_metadata(self, task):
        parts = []

        if task.started_at is not None:
            parts.append(
                f"started {task.started_at.strftime('%H:%M:%S')}"
            )

        if task.finished_at is not None:
            parts.append(
                f"finished {task.finished_at.strftime('%H:%M:%S')}"
            )

        if task.exit_code is not None:
            parts.append(
                f"exit={task.exit_code}"
            )

        duration = task.duration_seconds()

        if duration is not None:
            parts.append(
                f"{duration:.2f}s"
            )

        return " | ".join(parts)

    def set_workflow_running(self, running):
        self.run_button.set_sensitive(
            not running
        )

        if running:
            self.run_button.set_label("▶ Running...")
        else:
            self.run_button.set_label("▶ Run Workflow")

    def on_stop_workflow_clicked(self, widget):
        self.emit("stop-workflow")


    def set_workflow_stoppable(
        self,
        stoppable,
    ):
        self.stop_button.set_sensitive(
            stoppable
        )

    def set_workflow_stopping(
        self,
        stopping,
    ):
        self.run_button.set_sensitive(False)

        if stopping:
            self.run_button.set_label(
                "⏹ Stopping..."
            )
        else:
            self.run_button.set_label(
                "▶ Run Workflow"
            )