
from datetime import datetime, timedelta


PRIORITY_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _read_deadline(value):
    deadline = datetime.fromisoformat(str(value))

    # Compare timezone-aware deadlines using the computer's local time.
    if deadline.tzinfo is not None:
        deadline = deadline.astimezone().replace(tzinfo=None)

    return deadline


def audit_workload(tasks, now=None):
    """
    Audit real tasks and return the Commander's state,
    next directive, and supporting evidence.

    This function does not modify the database.
    """
    now = now or datetime.now()

    if now.tzinfo is not None:
        now = now.astimezone().replace(tzinfo=None)

    outstanding = []

    for task in tasks:
        if task["status"] == "completed":
            continue

        item = dict(task)
        deadline = _read_deadline(item["deadline"])
        hours_remaining = (deadline - now).total_seconds() / 3600

        item["parsed_deadline"] = deadline
        item["hours_remaining"] = hours_remaining
        item["is_overdue"] = hours_remaining < 0

        outstanding.append(item)

    # Deadline urgency comes before the user's priority label.
    # Priority breaks ties within the same urgency category.
    def rank_task(task):
        hours = task["hours_remaining"]

        if hours < 0:
            urgency = 0
        elif hours <= 24:
            urgency = 1
        elif hours <= 72:
            urgency = 2
        elif hours <= 168:
            urgency = 3
        else:
            urgency = 4

        return (
            urgency,
            -PRIORITY_RANK.get(task["priority"], 2),
            task["parsed_deadline"],
            task["task_id"],
        )

    outstanding.sort(key=rank_task)

    overdue = [
        task for task in outstanding
        if task["is_overdue"]
    ]

    approaching = [
        task for task in outstanding
        if 0 <= task["hours_remaining"] <= 72
    ]

    estimated_minutes = sum(
        task["estimated_minutes"] for task in outstanding
    )

    # State precedence: imminent danger first, then deadline clusters.
    if overdue or any(
        task["hours_remaining"] <= 24 for task in outstanding
    ):
        state = "ENRAGED"
    elif len(approaching) >= 3:
        state = "STRATEGIZING"
    elif outstanding:
        state = "COMMANDING"
    else:
        state = "MONITORING"

    next_task = outstanding[0] if outstanding else None

    if state == "ENRAGED":
        if overdue:
            message = (
                f"{len(overdue)} overdue task(s). "
                "The original timeline has been compromised. "
                "We address the most urgent outstanding task first."
            )
        else:
            message = (
                "A deadline is less than 24 hours away. "
                "Stop expanding the plan. Execute the next directive."
            )

    elif state == "STRATEGIZING":
        message = (
            f"{len(approaching)} deadlines fall within the next "
            "72 hours. We are reorganizing the board before "
            "these deadlines organize us."
        )

    elif next_task:
        message = (
            "I've reviewed the outstanding workload. "
            "We have a next move. Do try to keep up."
        )

    else:
        message = (
            "No outstanding tasks. "
            "An unexpectedly orderly situation. "
            "Enjoy it; we will review the next campaign soon."
        )

    return {
        "state": state,
        "message": message,
        "next_task": next_task,
        "outstanding_count": len(outstanding),
        "overdue_count": len(overdue),
        "approaching_count": len(approaching),
        "estimated_minutes": estimated_minutes,
        "outstanding_tasks": outstanding,
    }
