from fastapi.testclient import TestClient
from main import app
import time

def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        json = response.json()
        assert json["status"] == "ok"

def test_test_event():
    with TestClient(app) as client:
        response = client.post("/test-event")
        assert response.status_code == 200
        json = response.json()
        assert json["status"] == "notified"
        assert "event" in json

def test_create_project():
    with TestClient(app) as client:
        response = client.post("/projects", json={"title": "Test Project"})
        assert response.status_code == 200
        json = response.json()
        assert json["id"] is not None
        assert json["title"] == "Test Project"

def test_list_projects():
    with TestClient(app) as client:
        client.post("/projects", json={"title": "P1"})
        client.post("/projects", json={"title": "P2"})
        response = client.get("/projects")
        assert response.status_code == 200
        assert len(response.json()) >= 2

def test_create_task():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "P"})
        pid = r.json()["id"]
        r = client.post("/tasks", json={"project_id": pid, "title": "T1"})
        assert r.status_code == 200
        assert r.json()["title"] == "T1"

def test_chatbook_crud():
    with TestClient(app) as client:
        # Create project
        r = client.post("/projects", json={"title": "Chat Test"})
        pid = r.json()["id"]

        # Create chatbook
        r = client.post("/chatbooks", json={"project_id": pid, "title": "Main Chat"})
        assert r.status_code == 200
        cid = r.json()["id"]
        assert cid is not None

        # List chatbooks
        r = client.get(f"/chatbooks?project_id={pid}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

        # Send message
        r = client.post(f"/chatbooks/{cid}/messages", json={"role": "user", "content": "hello"})
        assert r.status_code == 200
        assert r.json()["role"] == "user"
        assert r.json()["content"] == "hello"

        # List messages
        r = client.get(f"/chatbooks/{cid}/messages")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["content"] == "hello"

def test_terminal_spawn_and_close():
    with TestClient(app) as client:
        r = client.post("/terminal/spawn", json={"command": "/bin/bash"})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        assert r.json()["status"] == "running"

        r = client.post(f"/terminal/{sid}/close")
        assert r.status_code == 200
        assert r.json()["status"] == "closed"


def test_cell_execution_shell():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Cell Test"})
        pid = r.json()["id"]

        r = client.post("/chatbooks", json={"project_id": pid, "title": "Cell Chat"})
        cid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/cells", json={"language": "shell", "source": "echo hello_from_cell"})
        assert r.status_code == 200
        json = r.json()
        assert json["status"] in ("success", "error")
        assert "hello_from_cell" in (json.get("output") or "")

        # List cells
        r = client.get(f"/chatbooks/{cid}/cells")
        assert r.status_code == 200
        assert len(r.json()) == 1


def test_cell_execution_python():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Python Cell"})
        pid = r.json()["id"]

        r = client.post("/chatbooks", json={"project_id": pid})
        cid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/cells", json={"language": "python", "source": "print('py_cell_ok')"})
        assert r.status_code == 200
        json = r.json()
        assert json["status"] == "success"
        assert "py_cell_ok" in json.get("output", "")