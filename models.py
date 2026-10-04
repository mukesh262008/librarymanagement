from __future__ import annotations

from datetime import date


def is_overdue(due_on: str, status: str) -> bool:
    return status == "active" and date.fromisoformat(due_on) < date.today()


def loan_status(due_on: str, status: str) -> str:
    if status == "returned":
        return "Returned"
    return "Overdue" if is_overdue(due_on, status) else "On loan"
