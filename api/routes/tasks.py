"""Staff task board endpoints — the Manager Action Tracker."""

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import df_records, get_store

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    appointment_id: int
    task_type: str = "Call Patient"
    priority: str = "Medium"
    assigned_to: str = "Monica Reyes"
    due_date: str | None = None


def _task_view(store) -> pd.DataFrame:
    tasks = store.tasks.copy()
    today = pd.Timestamp.now().normalize()
    tasks["is_overdue"] = (
        (tasks["task_status"] != "Completed")
        & (pd.to_datetime(tasks["due_date"]) < today)
    )
    risk = store.worklist[["appointment_id", "risk_category", "patient_name",
                           "appointment_datetime", "clinic_name"]]
    tasks = tasks.merge(risk, on="appointment_id", how="left")
    return tasks


@router.get("")
def list_tasks(
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    task_type: str | None = None,
    overdue_only: bool = False,
    limit: int = Query(200, le=1000),
):
    store = get_store()
    tasks = _task_view(store)

    if status:
        tasks = tasks[tasks["task_status"] == status]
    if priority:
        tasks = tasks[tasks["priority"] == priority]
    if assigned_to:
        tasks = tasks[tasks["assigned_to"] == assigned_to]
    if task_type:
        tasks = tasks[tasks["task_type"] == task_type]
    if overdue_only:
        tasks = tasks[tasks["is_overdue"]]

    total = len(store.tasks)
    completed = int((store.tasks["task_status"] == "Completed").sum())
    all_tasks = _task_view(store)
    summary = {
        "total_tasks": total,
        "pending": int((store.tasks["task_status"] == "Pending").sum()),
        "in_progress": int((store.tasks["task_status"] == "In Progress").sum()),
        "completed": completed,
        "overdue": int(all_tasks["is_overdue"].sum()),
        "completion_rate": round(completed / total, 4) if total else 0,
        "by_staff": df_records(
            all_tasks.groupby("assigned_to")["task_status"]
            .agg(total="count",
                 completed=lambda s: int((s == "Completed").sum()))
            .reset_index()),
    }

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    tasks = tasks.assign(
        _o=~tasks["is_overdue"], _p=tasks["priority"].map(priority_rank).fillna(3)
    ).sort_values(["_o", "_p", "due_date"]).drop(columns=["_o", "_p"])

    return {"summary": summary, "count": len(tasks),
            "tasks": df_records(tasks.head(limit))}


@router.post("")
def create_task(body: TaskCreate):
    store = get_store()
    match = store.worklist[store.worklist["appointment_id"] == body.appointment_id]
    if match.empty:
        raise HTTPException(404, f"Appointment {body.appointment_id} not found.")

    due = body.due_date or (
        min(pd.to_datetime(match.iloc[0]["appointment_datetime"])
            - pd.Timedelta(days=1),
            pd.Timestamp.now() + pd.Timedelta(days=2)).date().isoformat())
    task = {
        "task_id": store.next_task_id(),
        "appointment_id": body.appointment_id,
        "assigned_to": body.assigned_to,
        "task_type": body.task_type,
        "priority": body.priority,
        "due_date": due,
        "task_status": "Pending",
        "completed_date": "",
        "context": "",
    }
    store.tasks = pd.concat([store.tasks, pd.DataFrame([task])], ignore_index=True)
    store.tasks["appointment_id"] = pd.to_numeric(
        store.tasks["appointment_id"], errors="coerce").astype("Int64")
    idx = store.worklist["appointment_id"] == body.appointment_id
    store.worklist.loc[idx, ["task_id", "task_status", "assigned_to"]] = [
        task["task_id"], "Pending", body.assigned_to]
    return {"status": "created", "task": task}


@router.post("/{task_id}/complete")
def complete_task(task_id: int):
    store = get_store()
    idx = store.tasks["task_id"] == task_id
    if not idx.any():
        raise HTTPException(404, f"Task {task_id} not found.")

    today = datetime.now().date().isoformat()
    store.tasks.loc[idx, ["task_status", "completed_date"]] = ["Completed", today]
    appt_id = store.tasks.loc[idx, "appointment_id"].iloc[0]
    if pd.notna(appt_id):
        w_idx = store.worklist["task_id"] == task_id
        store.worklist.loc[w_idx, "task_status"] = "Completed"
    return {"task_id": task_id, "task_status": "Completed",
            "completed_date": today}


@router.post("/{task_id}/status")
def update_task_status(task_id: int, status: str = Query(
        ..., pattern="^(Pending|In Progress|Completed)$")):
    store = get_store()
    idx = store.tasks["task_id"] == task_id
    if not idx.any():
        raise HTTPException(404, f"Task {task_id} not found.")
    completed = datetime.now().date().isoformat() if status == "Completed" else ""
    store.tasks.loc[idx, ["task_status", "completed_date"]] = [status, completed]
    w_idx = store.worklist["task_id"] == task_id
    store.worklist.loc[w_idx, "task_status"] = status
    return {"task_id": task_id, "task_status": status}
