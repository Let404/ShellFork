import json
from pathlib import Path

from core.workflow import (
    Workflow,
    WORKFLOW_EXTENSION,
)


def save_workflow(
    workflow: Workflow,
    path: str,
):
    path = Path(path)

    if path.suffix != WORKFLOW_EXTENSION:
        path = path.with_suffix(
            WORKFLOW_EXTENSION
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            workflow.to_dict(),
            file,
            indent=4,
        )


def load_workflow(
    path: str,
):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return Workflow.from_dict(data)