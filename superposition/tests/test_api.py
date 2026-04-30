from fastapi.testclient import TestClient
from main import app

def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ok"

def test_test_event():
    client = TestClient(app)
    response = client.post("/test-event")
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "notified"
    assert "event" in json
