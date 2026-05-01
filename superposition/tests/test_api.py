import os
import time
from fastapi.testclient import TestClient
from main import app

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


def test_artifact_create_and_list():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Artifact Test"})
        pid = r.json()["id"]

        r = client.post("/artifacts", json={
            "project_id": pid,
            "kind": "code",
            "title": "Cell output capture",
            "content_text": "some captured output",
            "source_ref": "cell:abc123",
            "tags": ["shell", "capture"],
        })
        assert r.status_code == 200
        aid = r.json()["id"]
        assert r.json()["kind"] == "code"
        assert r.json()["source_ref"] == "cell:abc123"

        r = client.get(f"/artifacts?project_id={pid}")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["id"] == aid


def test_create_task_from_message():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Msg Task"})
        pid = r.json()["id"]

        r = client.post("/chatbooks", json={"project_id": pid, "title": "Chat"})
        cid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/messages", json={"role": "user", "content": "Write a parser for CSV files"})
        mid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/messages/{mid}/create-task")
        assert r.status_code == 200
        json = r.json()
        assert json["title"] == "Write a parser for CSV files"
        assert json["status"] == "todo"
        assert json["project_id"] == pid
        assert json["created_from_ref"] == f"chatbook:{cid}/message:{mid}"


def test_create_task_from_missing_message():
    """create-task with non-existent message returns 404."""
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "P"})
        pid = r.json()["id"]
        r = client.post("/chatbooks", json={"project_id": pid})
        cid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/messages/doesnotexist/create-task")
        assert r.status_code == 404


def test_get_tasks():
    """GET /tasks lists all tasks; filterable by project_id and status."""
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Tasks Test"})
        pid = r.json()["id"]

        r = client.post("/tasks", json={"project_id": pid, "title": "Task A", "status": "todo"})
        tid_a = r.json()["id"]
        r = client.post("/tasks", json={"project_id": pid, "title": "Task B", "status": "done"})
        tid_b = r.json()["id"]

        r = client.get("/tasks")
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()]
        assert tid_a in ids and tid_b in ids

        r = client.get(f"/tasks?project_id={pid}")
        assert all(t["project_id"] == pid for t in r.json())

        r = client.get("/tasks?status=done")
        assert all(t["status"] == "done" for t in r.json())


def test_get_chatbook():
    """GET /chatbooks/{id} returns a single chatbook."""
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Single CB Test"})
        pid = r.json()["id"]
        r = client.post("/chatbooks", json={"project_id": pid, "title": "My Chat"})
        cid = r.json()["id"]

        r = client.get(f"/chatbooks/{cid}")
        assert r.status_code == 200
        assert r.json()["title"] == "My Chat"
        assert r.json()["id"] == cid


def test_get_chatbook_not_found():
    with TestClient(app) as client:
        r = client.get("/chatbooks/doesnotexist")
        assert r.status_code == 404


def test_chatbook_put_delete():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "CB Update Test"})
        pid = r.json()["id"]
        r = client.post("/chatbooks", json={"project_id": pid, "title": "Old Title"})
        cid = r.json()["id"]

        r = client.put(f"/chatbooks/{cid}", json={"title": "New Title"})
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"

        r = client.get(f"/chatbooks/{cid}")
        assert r.json()["title"] == "New Title"

        r = client.delete(f"/chatbooks/{cid}")
        assert r.json()["status"] == "deleted"

        r = client.get(f"/chatbooks/{cid}")
        assert r.status_code == 404


def test_cell_execution_unknown_language():
    """Unknown language returns error output, not a crash."""
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Unknown Lang"})
        pid = r.json()["id"]
        r = client.post("/chatbooks", json={"project_id": pid})
        cid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/cells", json={"language": "cobol", "source": "DISPLAY 'HELLO'."})
        assert r.status_code == 200
        json = r.json()
        assert json["status"] == "error"
        assert "Unsupported language" in json["output"]


def test_cell_execution_unknown_language_still_creates_run():
    """Even failed cell execution creates a Run record."""
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Run Provenance"})
        pid = r.json()["id"]
        r = client.post("/chatbooks", json={"project_id": pid})
        cid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/cells", json={"language": "unsupported", "source": "boom"})
        assert r.status_code == 200
        assert "run_id" in r.json()
        assert r.json()["run_id"] is not None


def test_cell_put_delete():
    """PUT /cells/{id} and DELETE /cells/{id} work correctly."""
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Cell CRUD"})
        pid = r.json()["id"]
        r = client.post("/chatbooks", json={"project_id": pid})
        cid = r.json()["id"]

        r = client.post(f"/chatbooks/{cid}/cells", json={"language": "shell", "source": "echo hi"})
        cell_id = r.json()["id"]

        r = client.put(f"/chatbooks/{cid}/cells/{cell_id}", json={"source": "echo updated"})
        assert r.status_code == 200
        assert r.json()["source"] == "echo updated"

        r = client.delete(f"/chatbooks/{cid}/cells/{cell_id}")
        assert r.json()["status"] == "deleted"

        r = client.get(f"/chatbooks/{cid}/cells")
        assert all(c["id"] != cell_id for c in r.json())


def test_artifact_task_filter():
    """GET /artifacts?task_id= filters correctly."""
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Artifact Task Filter"})
        pid = r.json()["id"]
        r = client.post("/tasks", json={"project_id": pid, "title": "A Task"})
        tid = r.json()["id"]

        r = client.post("/artifacts", json={"project_id": pid, "task_id": tid, "kind": "text", "title": "Linked"})
        assert r.json()["task_id"] == tid
        aid = r.json()["id"]

        r = client.post("/artifacts", json={"project_id": pid, "kind": "text", "title": "Unlinked"})
        unlinked_aid = r.json()["id"]

        r = client.get(f"/artifacts?task_id={tid}")
        assert len(r.json()) == 1
        assert r.json()[0]["id"] == aid


def test_artifact_put_delete():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Artifact CRUD"})
        pid = r.json()["id"]
        r = client.post("/artifacts", json={"project_id": pid, "kind": "text", "title": "Old"})
        aid = r.json()["id"]

        r = client.put(f"/artifacts/{aid}", json={"title": "New Title", "tags": ["updated"]})
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"
        assert r.json()["tags"] == ["updated"]

        r = client.delete(f"/artifacts/{aid}")
        assert r.json()["status"] == "deleted"

        r = client.get(f"/artifacts/{aid}")
        assert r.status_code == 404


def test_artifact_delete_not_found():
    with TestClient(app) as client:
        r = client.delete("/artifacts/doesnotexist")
        assert r.status_code == 404


def test_terminal_write_missing_session():
    """Write to non-existent session returns 404."""
    with TestClient(app) as client:
        r = client.post("/terminal/doesnotexist/write", json={"data": "echo hi"})
        assert r.status_code == 404


def test_artifact_missing_project():
    """Create artifact with non-existent project returns 404."""
    with TestClient(app) as client:
        r = client.post("/artifacts", json={"project_id": "doesnotexist", "kind": "text", "title": "Bad"})
        assert r.status_code == 404


def test_project_put():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "To Update"})
        pid = r.json()["id"]

        r = client.put(f"/projects/{pid}", json={"title": "Updated", "status": "archived"})
        assert r.status_code == 200
        assert r.json()["title"] == "Updated"
        assert r.json()["status"] == "archived"


def test_task_put():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Task Update"})
        pid = r.json()["id"]
        r = client.post("/tasks", json={"project_id": pid, "title": "Original", "status": "todo"})
        tid = r.json()["id"]

        r = client.put(f"/tasks/{tid}", json={"title": "Renamed", "status": "done"})
        assert r.status_code == 200
        assert r.json()["title"] == "Renamed"
        assert r.json()["status"] == "done"


def test_artifact_source_ref_invalid():
    """source_ref without cell:/message: prefix is rejected by Pydantic validation."""
    with TestClient(app) as client:
        p = client.post("/projects", json={"title": "Ref Test"}).json()
        r = client.post("/artifacts", json={
            "project_id": p["id"],
            "kind": "text",
            "title": "Bad ref",
            "source_ref": "not-a-prefix-123",
        })
        assert r.status_code == 422, r.text


def test_artifact_source_ref_valid():
    """source_ref with cell:/message: prefix is accepted."""
    with TestClient(app) as client:
        p = client.post("/projects", json={"title": "Ref Test 2"}).json()
        r = client.post("/artifacts", json={
            "project_id": p["id"],
            "kind": "text",
            "title": "Good ref",
            "source_ref": f"cell:{p['id']}",
        })
        assert r.status_code == 200, r.text
        assert r.json()["source_ref"] == f"cell:{p['id']}"


def test_auth_required_without_key_env():
    """Without API_KEY set, all endpoints are open."""
    os.environ.pop("API_KEY", None)
    import importlib
    import main as main_mod
    importlib.reload(main_mod)
    app = main_mod.app
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/projects", json={"title": "Auth Test"})
        assert r.status_code == 200  # open when no key


def test_auth_rejects_missing_key():
    """With API_KEY set, requests without X-API-Key get 401."""
    import os
    os.environ["API_KEY"] = "testkey"
    import importlib
    import main as main_mod
    importlib.reload(main_mod)
    app = main_mod.app
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/projects", json={"title": "Should Fail"})
        assert r.status_code == 401
        assert "X-API-Key" in r.json()["detail"]


def test_auth_rejects_wrong_key():
    """With API_KEY set, wrong key gets 403."""
    import os
    os.environ["API_KEY"] = "testkey"
    import importlib
    import main as main_mod
    importlib.reload(main_mod)
    app = main_mod.app
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/projects", json={"title": "Should Fail"},
                        headers={"X-API-Key": "wrongkey"})
        assert r.status_code == 403
        assert "Invalid" in r.json()["detail"]


def test_auth_accepts_correct_key():
    """With API_KEY set, correct key grants access."""
    import os
    os.environ["API_KEY"] = "testkey"
    import importlib
    import main as main_mod
    importlib.reload(main_mod)
    app = main_mod.app
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/projects", json={"title": "Should Pass"},
                        headers={"X-API-Key": "testkey"})
        assert r.status_code == 200
        assert r.json()["title"] == "Should Pass"


def test_health_always_open():
    """Health endpoint never requires auth, even with API_KEY set."""
    import os
    os.environ["API_KEY"] = "testkey"
    import importlib
    import main as main_mod
    importlib.reload(main_mod)
    app = main_mod.app
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
