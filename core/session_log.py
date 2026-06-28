from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LogEntry:
    timestamp: datetime
    event: str
    message: str


@dataclass
class SessionLog:
    entries: list[LogEntry] = field(default_factory=list)

    def add(self, event: str, message: str = ""):
        self.entries.append(
            LogEntry(
                timestamp=datetime.now(),
                event=event,
                message=message,
            )
        )

    def text(self):
        lines = []

        for entry in self.entries:
            timestamp = entry.timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            if entry.message:
                lines.append(
                    f"[{timestamp}] {entry.event}: {entry.message}"
                )
            else:
                lines.append(
                    f"[{timestamp}] {entry.event}"
                )

        return "\n".join(lines)