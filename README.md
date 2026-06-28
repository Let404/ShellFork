# ShellFork

**ShellFork** is a GTK 4 desktop application for Linux that lets you build, run, and monitor sequences of shell commands through a visual interface. Instead of chaining commands in a terminal or writing shell scripts, you compose *workflows* — ordered lists of commands — that ShellFork feeds one by one into an embedded terminal, tracking progress and status in real time.

---

## Features

- **Embedded terminal** — A full VTE-powered Bash terminal runs inside the app. Commands execute in your real shell environment, with full output visible as they run.
- **Visual workflow editor** — Build workflows as a tree of steps using the sidebar panel. Steps can be individual commands or named sub-workflows, allowing nested, hierarchical sequencing.
- **Automatic queue management** — When a workflow is launched, ShellFork enqueues all its commands and dispatches them sequentially, waiting for each command to finish (via `PROMPT_COMMAND` shell integration) before running the next.
- **Live status tracking** — Each step in the workflow tree is updated in real time: `queued`, `running`, `completed`, `failed`, or `cancelled`. Status bubbles up from commands to their parent sub-workflows automatically.
- **Queue panel** — A dedicated panel shows the current queue and execution history with per-task status and timing information. Tasks can be reordered (move up / move down), cancelled individually, or the queue can be cleared entirely.
- **Pause & resume** — Running workflows can be paused after the current command finishes, then resumed at any point.
- **Export as script** — Any workflow can be exported to a standalone Bash script via **File → Export as Script…**. The exported `.sh` file preserves the workflow's structure as comments and runs with `set -e`.
- **Session log** — ShellFork records a timestamped log of significant events (workflow start, command completion, failures, cancellations) for the current session, queryable at any time.
- **Workflow files (`.sfw`)** — Workflows are saved as human-readable JSON files with the `.sfw` extension. They can be opened, edited, and shared. The format supports nested sub-workflows with stable UUIDs per step.
- **New / Open / Save / Save As** — Full file management via the menu bar, including unsaved-changes protection before closing or opening another file.

---

## Requirements

- Python 3.13+
- GTK 4
- VTE 3.91 (via `python-gi` / PyGObject)
- A Linux system with Bash

---

## Installation

Clone the repository and run directly — no build step is required:

```bash
git clone https://github.com/let404/shellfork.git
cd shellfork
python main.py
```

Make sure the GTK 4 and VTE GObject introspection libraries are installed. On Debian/Ubuntu:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-vte-3.91
```

---

## Usage

### Running the app

```bash
python main.py
```

### Building a workflow

1. Use the **Workflow** panel on the left to add steps:
   - **Add Command** — adds a single shell command to the workflow.
   - **Add Sub-workflow** — adds a named group that can contain its own commands, allowing logical grouping and nesting.
2. Select any step to edit or reorder it using the up/down controls.
3. Save your workflow via **File → Save** (`.sfw` format).

### Running a workflow

Click **Run Workflow** to enqueue all commands. ShellFork will execute them one by one in the embedded terminal. You can:

- **Pause** — stop dispatching new commands after the current one finishes.
- **Resume** — continue from where you left off.
- **Stop** — cancel all remaining queued commands.

### Exporting a workflow as a Bash script

Use **File → Export as Script…** to save the current workflow as a `.sh` file. The exported script uses `set -e` (exit on first error) and preserves sub-workflow names as comments, making it easy to run outside of ShellFork or share with others.

### Workflow file format

Workflows are stored as plain JSON:

```json
{
    "type": "shellfork.workflow",
    "version": 1,
    "name": "My Workflow",
    "steps": [
        { "type": "command", "command": "echo hello" },
        {
            "type": "workflow",
            "name": "Cleanup",
            "steps": [
                { "type": "command", "command": "rm -rf build/" },
                { "type": "command", "command": "mkdir build" }
            ]
        }
    ]
}
```

Files use the `.sfw` extension and can be opened with **File → Open**.

---

## Project structure

```
shellfork/
├── main.py                  # Entry point
├── app.py                   # Gtk.Application subclass
├── core/
│   ├── models.py            # Task dataclass and TaskStatus enum
│   ├── workflow.py          # Workflow and WorkflowStep dataclasses
│   ├── workflow_io.py       # Save/load workflow files
│   ├── scheduler.py         # Task queue management
│   ├── dispatcher.py        # Sends commands to the terminal
│   ├── shell_monitor.py     # PROMPT_COMMAND-based exit-code detection
│   ├── script_export.py     # Export workflows as Bash scripts
│   └── session_log.py       # Timestamped in-session event log
└── ui/
    ├── main_window.py        # Main application window
    ├── workflow_tree.py      # Workflow sidebar (GTK TreeView)
    └── queue_panel.py        # Queue and history panel
```

---

## License

MIT
