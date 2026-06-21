from enum import Enum, auto


class ShellState(Enum):
    IDLE = auto()
    WAITING = auto()
    RUNNING = auto()