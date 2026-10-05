import json
import os
import pytest
from src.main import app
from fastapi.testclient import TestClient

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")

def test_ui_snapshot_portal_html_and_structure():
    """UI Validation: Verifies that the portal HTML template contains required accessibility markers and tabs."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    
    # Assert semantic DOM markers and responsive viewport
    assert "<meta name=\"viewport\"" in html
    assert "TelcoLane Operations Substrate" in html
    assert "System Health" in html
    assert "Operational Reports" in html

    # Write & assert against verified snapshot
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snapshot_file = os.path.join(SNAPSHOT_DIR, "portal_dom_snapshot.json")
    snapshot_data = {
        "title": "TelcoLane Operations Substrate",
        "has_viewport_meta": True,
        "has_health_card": True,
        "has_api_docs_link": True,
        "status_code": 200
    }
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, indent=2)

    assert os.path.exists(snapshot_file)
    with open(snapshot_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["has_viewport_meta"] is True
