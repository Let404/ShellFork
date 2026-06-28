import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject, GLib

from core.workflow import Workflow, WorkflowStep


class WorkflowTree(Gtk.Box):

    __gsignals__ = {
        "selection-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
        "add-command": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
        "add-workflow": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
        "delete-node": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
        "rename-node": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
        "move-node-up": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),

        "move-node-down": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
    }

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )

        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        title = Gtk.Label(label="Workflow")
        title.set_xalign(0)

        self.append(title)

        controls = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )

        self.append(controls)

        row1 = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=4,
        )

        row2 = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=4,
        )

        row3 = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=4,
        )

        controls.append(row1)
        controls.append(row2)
        controls.append(row3)

        add_command_button = Gtk.Button(
            label="Add Command"
        )

        add_command_button.connect(
            "clicked",
            self.on_add_command_clicked,
        )

        add_workflow_button = Gtk.Button(
            label="Add Workflow"
        )

        add_workflow_button.connect(
            "clicked",
            self.on_add_workflow_clicked,
        )

        delete_button = Gtk.Button(
            label="Delete"
        )

        delete_button.connect(
            "clicked",
            self.on_delete_clicked,
        )

        rename_button = Gtk.Button(
            label="Rename/Edit"
        )

        rename_button.connect(
            "clicked",
            self.on_rename_clicked,
        )

        move_up_button = Gtk.Button(
            label="Move Up"
        )

        move_up_button.connect(
            "clicked",
            self.on_move_up_clicked,
        )

        move_down_button = Gtk.Button(
            label="Move Down"
        )

        move_down_button.connect(
            "clicked",
            self.on_move_down_clicked,
        )

        row3.append(move_up_button)
        row3.append(move_down_button)

        row2.append(delete_button)
        row2.append(rename_button)

        row1.append(add_workflow_button)
        row1.append(add_command_button)

        self.selected_path = None

        self.collapsed_paths = set()

        self.container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.scroll.set_hexpand(True)
        self.scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC,
        )

        self.scroll.set_child(self.container)

        self.append(self.scroll)

    def refresh(self, workflow: Workflow):
        self.current_workflow = workflow
        self.rebuild_step_paths(workflow)
        self.step_widgets = {}
        self.clear()

        root = self.workflow_node(
            workflow.name,
            workflow.steps,
            depth=0,
            path=[],
            status=workflow.status,
        )

        self.container.append(root)

    def clear(self):
        child = self.container.get_first_child()

        while child:
            next_child = child.get_next_sibling()
            self.container.remove(child)
            child = next_child

    def workflow_node(self, name, steps, depth, path, status="queued"):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
        )

        collapse_icon = "▶" if self.is_collapsed(path) else "▼"
        status_icon = self.status_icon_for_step_status(status)

        button = Gtk.Button(
            label=f"{collapse_icon} {status_icon} {name}"
        )
        button.set_halign(Gtk.Align.FILL)
        button.set_margin_start(
            self.indent_margin(depth)
        )

        if self.is_selected(path):
            button.add_css_class("suggested-action")

        button.connect(
            "clicked",
            self.on_node_clicked,
            path,
            "workflow",
        )

        box.append(button)

        if not self.is_collapsed(path):
            for index, step in enumerate(steps):
                if step.type == "command":
                    box.append(
                        self.command_node(
                            step,
                            depth + 1,
                            path + [index],
                        )
                    )

                elif step.type == "workflow":
                    box.append(
                        self.workflow_node(
                            step.name,
                            step.steps,
                            depth + 1,
                            path + [index],
                            status=step.status,
                        )
                    )

        return box

    def command_node(self, step, depth, path):
        button = Gtk.Button(
            label=f"{self.status_icon(step.status)} {step.command}"
        )

        self.step_widgets[step.id] = button

        button.set_halign(Gtk.Align.FILL)
        button.set_margin_start(
            self.indent_margin(depth)
        )

        if self.is_selected(path):
            button.add_css_class("suggested-action")

        button.connect(
            "clicked",
            self.on_node_clicked,
            path,
            "command",
        )

        return button

    def indent_margin(self, depth):
        return depth * 20

    def on_node_clicked(self, button, path, node_type):
        self.selected_path = path

        if node_type == "workflow":
            key = self.path_key(path)

            if key in self.collapsed_paths:
                self.collapsed_paths.remove(key)
            else:
                self.collapsed_paths.add(key)

        self.emit(
            "selection-changed",
            path,
        )

        self.refresh(
            self.current_workflow
        )

    def on_add_command_clicked(self, button):
        self.emit(
            "add-command",
            self.selected_path,
        )

    def on_add_workflow_clicked(self, button):
        self.emit(
            "add-workflow",
            self.selected_path,
        )

    def is_selected(self, path):
        return self.selected_path == path

    def on_delete_clicked(self, button):
        self.emit(
            "delete-node",
            self.selected_path,
        )

    def on_rename_clicked(self, button):
        self.emit(
            "rename-node",
            self.selected_path,
        )

    def on_move_up_clicked(self, button):
        self.emit(
            "move-node-up",
            self.selected_path,
        )


    def on_move_down_clicked(self, button):
        self.emit(
            "move-node-down",
            self.selected_path,
        )

    def path_key(self, path):
        return tuple(path)

    def is_collapsed(self, path):
        return self.path_key(path) in self.collapsed_paths

    def status_icon(self, status):
        if status == "queued":
            return "○"

        if status == "running":
            return "▶"

        if status == "completed":
            return "✓"

        if status == "failed":
            return "✗"

        if status == "cancelled":
            return "⊘"

        return "?"

    def status_icon_for_step_status(self, status):
        if status == "queued":
            return "○"

        if status == "running":
            return "▶"

        if status == "completed":
            return "✓"

        if status == "failed":
            return "✗"

        if status == "cancelled":
            return "⊘"

        return "?"

    def select_step_by_id(self, step_id):
        path = self.step_paths.get(step_id)

        if path is None:
            return

        self.expand_path_parents(path)

        self.selected_path = path
        self.pending_scroll_step_id = step_id

        self.refresh(
            self.current_workflow
        )

        GLib.timeout_add(
            50,
            self.scroll_to_step,
        )

    def expand_path_parents(self, path):
        root_key = self.path_key([])

        if root_key in self.collapsed_paths:
            self.collapsed_paths.remove(root_key)

        current = []

        for index in path[:-1]:
            current.append(index)

            key = self.path_key(current)

            if key in self.collapsed_paths:
                self.collapsed_paths.remove(key)

    def rebuild_step_paths(self, workflow):
        self.step_paths = {}

        for index, step in enumerate(workflow.steps):
            self.register_step_path(
                step,
                [index],
            )

    def register_step_path(self, step, path):
        self.step_paths[step.id] = path

        if step.type == "workflow":
            for index, child in enumerate(step.steps):
                self.register_step_path(
                    child,
                    path + [index],
                )

    def scroll_to_step(self):
        step_id = getattr(
            self,
            "pending_scroll_step_id",
            None,
        )

        if step_id is None:
            return False

        widget = self.step_widgets.get(step_id)

        if widget is None:
            return False

        adjustment = self.scroll.get_vadjustment()

        widget_y = widget.get_allocation().y
        page_size = adjustment.get_page_size()

        target = max(
            0,
            widget_y - page_size / 2,
        )

        adjustment.set_value(
            min(
                target,
                adjustment.get_upper() - page_size,
            )
        )

        widget.grab_focus()

        return False