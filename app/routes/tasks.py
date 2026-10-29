import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.database import get_db
from app.schemas import Priority, TaskCreate, TaskOut, TaskStatus, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])
DB = Annotated[sqlite3.Connection, Depends(get_db)]

def task_or_404(db: sqlite3.Connection, task_id: int) -> dict:
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(task)

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DB):
    cursor = db.execute(
        """INSERT INTO tasks (title, description, priority, status)
           VALUES (?, ?, ?, ?)""",
        (payload.title, payload.description, payload.priority.value, payload.status.value),
    )
    db.commit()
    return task_or_404(db, cursor.lastrowid)

@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: DB,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: Priority | None = None,
):
    sql = "SELECT * FROM tasks"
    conditions, values = [], []
    if task_status is not None:
        conditions.append("status = ?")
        values.append(task_status.value)
    if priority is not None:
        conditions.append("priority = ?")
        values.append(priority.value)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC"
    return [dict(row) for row in db.execute(sql, values).fetchall()]

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: DB):
    return task_or_404(db, task_id)

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: DB):
    task_or_404(db, task_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Provide at least one field to update")
    allowed = {"title", "description", "priority", "status"}
    assignments, values = [], []
    for key, value in changes.items():
        if key not in allowed:
            continue
        assignments.append(f"{key} = ?")
        values.append(value.value if hasattr(value, "value") else value)
    values.append(task_id)
    db.execute(f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?", values)
    db.commit()
    return task_or_404(db, task_id)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DB):
    task_or_404(db, task_id)
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
