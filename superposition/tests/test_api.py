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


def test_lane_crud():
    with TestClient(app) as client:
        # Create project (to assign to lane)
        r = client.post("/projects", json={"title": "Lane Test Project"})
        pid = r.json()["id"]

        # Create lane
        r = client.post("/lanes", json={"title": "My Lane", "active_project_id": pid})
        assert r.status_code == 200
        lid = r.json()["id"]
        assert r.json()["title"] == "My Lane"
        assert r.json()["active_project_id"] == pid

        # List lanes
        r = client.get("/lanes")
        assert r.status_code == 200
        assert any(l["id"] == lid for l in r.json())

        # Get lane
        r = client.get(f"/lanes/{lid}")
        assert r.status_code == 200
        assert r.json()["title"] == "My Lane"
        assert r.json()["active_project_id"] == pid
        assert r.json()["layout_state"] is None

        # Switch active project (lane switching)
        r2 = client.post("/projects", json={"title": "Other Project"})
        pid2 = r2.json()["id"]
        r = client.put(f"/lanes/{lid}", json={"active_project_id": pid2})
        assert r.status_code == 200
        assert r.json()["active_project_id"] == pid2

        # Clear active project
        r = client.put(f"/lanes/{lid}", json={"active_project_id": ""})
        assert r.status_code == 200
        assert r.json()["active_project_id"] is None

        # Update title
        r = client.put(f"/lanes/{lid}", json={"title": "Renamed Lane"})
        assert r.status_code == 200
        assert r.json()["title"] == "Renamed Lane"

        # Delete lane
        r = client.delete(f"/lanes/{lid}")
        assert r.status_code == 200

        # Not found
        r = client.get(f"/lanes/{lid}")
        assert r.status_code == 404


def test_lane_switch_invalid_project():
    with TestClient(app) as client:
        r = client.post("/lanes", json={"title": "Lane"})
        assert r.status_code == 200
        lid = r.json()["id"]

        # Try to set invalid project
        r = client.put(f"/lanes/{lid}", json={"active_project_id": "nonexistent-id"})
        assert r.status_code == 404
        assert "Project not found" in r.json()["detail"]


def test_lane_create_invalid_project():
    with TestClient(app) as client:
        r = client.post("/lanes", json={"title": "Lane", "active_project_id": "bad-id"})
        assert r.status_code == 404


def test_lane_not_found():
    with TestClient(app) as client:
        r = client.get("/lanes/fake-id")
        assert r.status_code == 404
        r = client.put("/lanes/fake-id", json={"title": "X"})
        assert r.status_code == 404
        r = client.delete("/lanes/fake-id")
        assert r.status_code == 404


def test_agent_crud():
    with TestClient(app) as client:
        # Create agent
        r = client.post("/agents", json={"name": "Coder", "mode": "auto", "status": "idle"})
        assert r.status_code == 200
        aid = r.json()["id"]
        assert r.json()["name"] == "Coder"
        assert r.json()["mode"] == "auto"
        assert r.json()["status"] == "idle"

        # List agents
        r = client.get("/agents")
        assert r.status_code == 200
        assert any(a["id"] == aid for a in r.json())

        # Get agent
        r = client.get(f"/agents/{aid}")
        assert r.status_code == 200
        assert r.json()["name"] == "Coder"

        # Update agent
        r = client.put(f"/agents/{aid}", json={"name": "Senior Coder", "status": "busy"})
        assert r.status_code == 200
        assert r.json()["name"] == "Senior Coder"
        assert r.json()["status"] == "busy"

        # Set capability_mask and schedule
        r = client.put(f"/agents/{aid}", json={
            "capability_mask": {"shell": True, "python": False},
            "schedule": {"cron": "0 9 * * *"}
        })
        assert r.status_code == 200

        # Delete agent
        r = client.delete(f"/agents/{aid}")
        assert r.status_code == 200

        # Not found
        r = client.get(f"/agents/{aid}")
        assert r.status_code == 404


def test_agent_parent_hierarchy():
    with TestClient(app) as client:
        # Create parent agent
        r = client.post("/agents", json={"name": "Parent Agent", "mode": "auto"})
        assert r.status_code == 200
        parent_id = r.json()["id"]

        # Create child agent with parent_scope
        r = client.post("/agents", json={"name": "Child Agent", "mode": "auto", "parent_scope": parent_id})
        assert r.status_code == 200
        child_id = r.json()["id"]

        # Verify parent_scope is set
        r = client.get(f"/agents/{child_id}")
        assert r.json()["parent_scope"] == parent_id

        # Invalid parent
        r = client.post("/agents", json={"name": "Orphan", "mode": "auto", "parent_scope": "bad-id"})
        assert r.status_code == 404
        assert "Parent agent not found" in r.json()["detail"]


def test_agent_not_found():
    with TestClient(app) as client:
        r = client.get("/agents/fake-id")
        assert r.status_code == 404
        r = client.put("/agents/fake-id", json={"name": "X"})
        assert r.status_code == 404
        r = client.delete("/agents/fake-id")
        assert r.status_code == 404


def test_process_crud():
    with TestClient(app) as client:
        # Create project (for process association)
        r = client.post("/projects", json={"title": "Process Test"})
        pid = r.json()["id"]

        # Create process
        r = client.post("/processes", json={
            "type": "shell", "command": "ls -la",
            "project_id": pid, "status": "starting"
        })
        assert r.status_code == 200
        proc_id = r.json()["id"]
        assert r.json()["type"] == "shell"
        assert r.json()["status"] == "starting"

        # List processes
        r = client.get("/processes")
        assert r.status_code == 200
        assert any(p["id"] == proc_id for p in r.json())

        # Filter by project
        r = client.get(f"/processes?project_id={pid}")
        assert r.status_code == 200
        assert any(p["id"] == proc_id for p in r.json())

        # Get process
        r = client.get(f"/processes/{proc_id}")
        assert r.status_code == 200
        assert r.json()["command"] == "ls -la"

        # Update process (e.g., set pid and status)
        r = client.put(f"/processes/{proc_id}", json={"status": "running", "pid": 12345})
        assert r.status_code == 200
        assert r.json()["status"] == "running"

        # Delete process
        r = client.delete(f"/processes/{proc_id}")
        assert r.status_code == 200
        r = client.get(f"/processes/{proc_id}")
        assert r.status_code == 404


def test_run_crud():
    with TestClient(app) as client:
        # Setup: project + process + (optionally) agent
        r = client.post("/projects", json={"title": "Run Test"})
        pid = r.json()["id"]
        r = client.post("/processes", json={"type": "shell", "command": "echo hi", "project_id": pid})
        proc_id = r.json()["id"]
        r = client.post("/agents", json={"name": "Test Agent", "mode": "auto"})
        agent_id = r.json()["id"]

        # Create run
        r = client.post("/runs", json={
            "project_id": pid,
            "process_id": proc_id,
            "actor_id": agent_id,
            "status": "running",
            "input": {"language": "shell"},
        })
        assert r.status_code == 200
        run_id = r.json()["id"]
        assert r.json()["status"] == "running"

        # List runs
        r = client.get("/runs")
        assert r.status_code == 200
        assert any(run["id"] == run_id for run in r.json())

        # Filter by actor
        r = client.get(f"/runs?actor_id={agent_id}")
        assert r.status_code == 200
        assert any(run["id"] == run_id for run in r.json())

        # Get run
        r = client.get(f"/runs/{run_id}")
        assert r.status_code == 200
        assert r.json()["input"]["language"] == "shell"
        assert r.json()["actor_id"] == agent_id

        # Complete run
        r = client.put(f"/runs/{run_id}", json={
            "status": "success",
            "output": "hello world",
            "finished_at": "2026-05-01T12:00:00Z"
        })
        assert r.status_code == 200
        assert r.json()["status"] == "success"
        assert r.json()["finished_at"] is not None

        # Delete run
        r = client.delete(f"/runs/{run_id}")
        assert r.status_code == 200
        r = client.get(f"/runs/{run_id}")
        assert r.status_code == 404


def test_run_invalid_project_or_process():
    with TestClient(app) as client:
        r = client.post("/processes", json={"type": "shell", "command": "echo"})
        proc_id = r.json()["id"]

        # Invalid project
        r = client.post("/runs", json={"project_id": "bad", "process_id": proc_id})
        assert r.status_code == 404
        assert "Project not found" in r.json()["detail"]

        # Invalid process
        r = client.post("/projects", json={"title": "P"})
        pid = r.json()["id"]
        r = client.post("/runs", json={"project_id": pid, "process_id": "bad"})
        assert r.status_code == 404
        assert "Process not found" in r.json()["detail"]

        # Invalid agent
        r = client.post("/runs", json={"project_id": pid, "process_id": proc_id, "actor_id": "bad"})
        assert r.status_code == 404
        assert "Agent not found" in r.json()["detail"]


def test_run_not_found():
    with TestClient(app) as client:
        for method, url, body in [
            (client.get, "/runs/fake", None),
            (client.put, "/runs/fake", {"status": "done"}),
            (client.delete, "/runs/fake", None),
        ]:
            if body:
                r = method(url, json=body)
            else:
                r = method(url)
            assert r.status_code == 404


def test_dashboard():
    with TestClient(app) as client:
        # Create some data
        r = client.post("/projects", json={"title": "Dashboard Project"})
        pid = r.json()["id"]

        r = client.post("/artifacts", json={
            "project_id": pid, "title": "Test Artifact", "kind": "text"
        })

        r = client.post("/tasks", json={"project_id": pid, "title": "Test Task"})

        # Get dashboard
        r = client.get("/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "projects" in data
        assert "running_terminals" in data
        assert "queued_agents" in data
        assert "recent_artifacts" in data
        assert "recent_tasks" in data
        # Should have the data we created
        assert any(p["title"] == "Dashboard Project" for p in data["projects"])
        assert any(a["title"] == "Test Artifact" for a in data["recent_artifacts"])
        assert any(t["title"] == "Test Task" for t in data["recent_tasks"])
        # Queued agents should be empty (no queued agents created)
        assert isinstance(data["queued_agents"], list)
        assert isinstance(data["running_terminals"], list)


def test_approval_crud():
    with TestClient(app) as client:
        # Create agent first
        r = client.post("/agents", json={"name": "Approval Agent", "mode": "manual"})
        assert r.status_code == 200
        agent_id = r.json()["id"]

        # Create approval
        r = client.post("/approvals", json={
            "agent_id": agent_id,
            "action_type": "run_shell",
            "action_payload": {"command": "rm -rf /"},
            "risk": 4,
            "urgency": 2,
            "priority": 3,
        })
        assert r.status_code == 200
        approval_id = r.json()["id"]
        assert r.json()["status"] == "pending"
        assert r.json()["risk"] == 4

        # List approvals
        r = client.get("/approvals")
        assert r.status_code == 200
        assert any(a["id"] == approval_id for a in r.json())

        # Filter by agent_id
        r = client.get(f"/approvals?agent_id={agent_id}")
        assert r.status_code == 200
        assert any(a["id"] == approval_id for a in r.json())

        # Filter by status
        r = client.get("/approvals?status=pending")
        assert r.status_code == 200
        assert any(a["id"] == approval_id for a in r.json())

        # Get approval detail
        r = client.get(f"/approvals/{approval_id}")
        assert r.status_code == 200
        assert r.json()["action_type"] == "run_shell"
        assert r.json()["action_payload"]["command"] == "rm -rf /"

        # Approve
        r = client.post(f"/approvals/{approval_id}/respond", json={
            "decision": "approved",
            "reason": "Safe in sandbox"
        })
        assert r.status_code == 200
        assert r.json()["status"] == "approved"
        assert r.json()["reason"] == "Safe in sandbox"
        assert r.json()["responded_at"] is not None

        # Cannot respond twice
        r = client.post(f"/approvals/{approval_id}/respond", json={"decision": "denied"})
        assert r.status_code == 409

        # Deny another approval
        r = client.post("/approvals", json={
            "agent_id": agent_id, "action_type": "write_file",
            "risk": 5, "urgency": 1, "priority": 5,
        })
        aid2 = r.json()["id"]
        r = client.post(f"/approvals/{aid2}/respond", json={
            "decision": "denied", "reason": "Too risky"
        })
        assert r.status_code == 200
        assert r.json()["status"] == "denied"


def test_approval_invalid_score():
    with TestClient(app) as client:
        r = client.post("/agents", json={"name": "Test", "mode": "auto"})
        agent_id = r.json()["id"]

        # Invalid risk score (> 5)
        r = client.post("/approvals", json={
            "agent_id": agent_id, "action_type": "x", "risk": 10
        })
        assert r.status_code == 422

        # Invalid score (< 1)
        r = client.post("/approvals", json={
            "agent_id": agent_id, "action_type": "x", "risk": 0
        })
        assert r.status_code == 422


def test_approval_invalid_agent():
    with TestClient(app) as client:
        r = client.post("/approvals", json={
            "agent_id": "nonexistent", "action_type": "run"
        })
        assert r.status_code == 404
        assert "Agent not found" in r.json()["detail"]


def test_approval_not_found():
    with TestClient(app) as client:
        r = client.get("/approvals/fake-id")
        assert r.status_code == 404
        r = client.post("/approvals/fake-id/respond", json={"decision": "approved"})
        assert r.status_code == 404


def test_approval_invalid_decision():
    with TestClient(app) as client:
        r = client.post("/agents", json={"name": "Test", "mode": "auto"})
        agent_id = r.json()["id"]
        r = client.post("/approvals", json={"agent_id": agent_id, "action_type": "x"})
        approval_id = r.json()["id"]
        r = client.post(f"/approvals/{approval_id}/respond", json={"decision": "maybe"})
        assert r.status_code == 422


def test_task_pause_resume_cancel():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "Task Actions"})
        pid = r.json()["id"]
        r = client.post("/tasks", json={"project_id": pid, "title": "Test Task"})
        task_id = r.json()["id"]
        assert r.json()["status"] in ("todo", "Todo")

        # Pause
        r = client.post(f"/tasks/{task_id}/pause")
        assert r.status_code == 200, f"pause failed: {r.status_code} {r.json()}"
        assert r.json()["status"] == "paused"

        # Resume: paused → in_progress
        r = client.post(f"/tasks/{task_id}/resume")
        assert r.status_code == 200, f"resume failed: {r.status_code} {r.json()}"
        assert r.json()["status"] == "in_progress"

        # Cancel directly from in_progress (cancel works from any non-done state)
        r = client.post(f"/tasks/{task_id}/cancel")
        assert r.status_code == 200, f"cancel failed: {r.status_code} {r.json()}"
        assert r.json()["status"] == "cancelled"

        # Cannot pause a cancelled task
        r = client.post(f"/tasks/{task_id}/pause")
        assert r.status_code == 409
        assert "Cannot pause" in r.json()["detail"]

        # Cannot cancel an already cancelled task
        r = client.post(f"/tasks/{task_id}/cancel")
        assert r.status_code == 409


def test_task_actions_on_done_task():
    with TestClient(app) as client:
        r = client.post("/projects", json={"title": "P"})
        pid = r.json()["id"]
        r = client.post("/tasks", json={"project_id": pid, "title": "Done Task"})
        task_id = r.json()["id"]
        r = client.put(f"/tasks/{task_id}", json={"status": "done"})
        assert r.json()["status"] == "done"

        # Cannot pause/cancel a done task
        r = client.post(f"/tasks/{task_id}/pause")
        assert r.status_code == 409
        r = client.post(f"/tasks/{task_id}/cancel")
        assert r.status_code == 409
        r = client.post(f"/tasks/{task_id}/resume")
        assert r.status_code == 409
