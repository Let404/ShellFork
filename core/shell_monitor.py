import os
import tempfile

import shlex

from gi.repository import GObject


class ShellMonitor(GObject.Object):

    __gsignals__ = {
        "ready": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (int,),
        ),
    }

    def __init__(self):
        super().__init__()

        self.path = os.path.join(
            tempfile.gettempdir(),
            f"shellfork-ready-{os.getpid()}.log",
        )

        open(self.path, "w").close()

        self.offset = 0

    def build_prompt_command(self):
        return (
            "PROMPT_COMMAND='"
            f"printf \"%s\\n\" \"$?\" >> {self.path}"
            "'"
        )

    def poll(self):
        with open(self.path, "r") as file:
            file.seek(self.offset)

            for line in file:
                line = line.strip()

                if not line:
                    continue

                try:
                    exit_code = int(line)
                except ValueError:
                    continue

                self.emit("ready", exit_code)

            self.offset = file.tell()

        return True

    def create_bash_rcfile(self):
        rcfile_path = os.path.join(
            tempfile.gettempdir(),
            f"shellfork-bashrc-{os.getpid()}",
        )

        with open(rcfile_path, "w") as file:
            file.write(
                "export SHELLFORK=1\n"
                f"PROMPT_COMMAND='printf \"%s\\n\" \"$?\" >> {shlex.quote(self.path)}'\n"
            )

        return rcfile_path