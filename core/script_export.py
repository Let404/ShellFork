from core.workflow import WorkflowStep


def workflow_to_bash_script(workflow):
    lines = [
        "#!/usr/bin/env bash",
        "set -e",
        "",
        f"# {workflow.name}",
    ]

    for step in workflow.steps:
        export_step(step, lines)

    lines.append("")

    return "\n".join(lines)


def export_step(step: WorkflowStep, lines):
    if step.type == "command":
        lines.append(step.command)
        return

    if step.type == "workflow":
        lines.append("")
        lines.append(f"# {step.name}")

        for child in step.steps:
            export_step(child, lines)