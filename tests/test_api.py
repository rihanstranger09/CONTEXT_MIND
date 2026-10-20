import os

os.environ["SKIP_DB_INIT"] = "true"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as api


def client():
    return api.create_app(initialize=False).test_client()


def test_health_endpoint():
    response = client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_create_requires_valid_title():
    response = client().post("/api/tasks", json={"title": "  "})
    assert response.status_code == 400
    assert "title" in response.get_json()["error"]


def test_create_rejects_non_json():
    response = client().post("/api/tasks", data="not-json", content_type="text/plain")
    assert response.status_code == 400


def test_update_requires_boolean():
    response = client().patch("/api/tasks/10", json={"completed": "yes"})
    assert response.status_code == 400
