import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db

@pytest.fixture
def client(tmp_path):
    test_path = tmp_path / "test_tasks.db"

    def override_get_db():
        import sqlite3
        connection = sqlite3.connect(test_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 100),
                    description TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL CHECK(priority IN ('low','medium','high')),
                    status TEXT NOT NULL CHECK(status IN ('pending','in_progress','completed')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
            yield connection
        finally:
            connection.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def sample_task(**overrides):
    data = {"title": "Write tests", "description": "Test the API",
            "priority": "high", "status": "pending"}
    return {**data, **overrides}

def test_create_and_get_task(client):
    created = client.post("/tasks", json=sample_task())
    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Write tests"
    assert client.get(f"/tasks/{task['id']}").json()["id"] == task["id"]

def test_list_and_filter_tasks(client):
    client.post("/tasks", json=sample_task())
    client.post("/tasks", json=sample_task(title="Finish report", priority="low", status="completed"))
    assert len(client.get("/tasks").json()) == 2
    assert len(client.get("/tasks", params={"status": "completed"}).json()) == 1
    assert len(client.get("/tasks", params={"priority": "high"}).json()) == 1

def test_update_and_delete_task(client):
    task_id = client.post("/tasks", json=sample_task()).json()["id"]
    updated = client.patch(f"/tasks/{task_id}", json={"status": "completed"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404

def test_validation_and_missing_task(client):
    assert client.post("/tasks", json=sample_task(title="   ")).status_code == 422
    assert client.post("/tasks", json=sample_task(priority="urgent")).status_code == 422
    assert client.get("/tasks/999").status_code == 404
    assert client.patch("/tasks/999", json={"status": "completed"}).status_code == 404
    assert client.delete("/tasks/999").status_code == 404

def test_empty_update_rejected(client):
    task_id = client.post("/tasks", json=sample_task()).json()["id"]
    assert client.patch(f"/tasks/{task_id}", json={}).status_code == 400
