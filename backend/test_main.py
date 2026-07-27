from fastapi.testclient import TestClient
import sys
import os

# Include backend/ directory in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)

def test_get_subjects():
    response = client.get("/api/subjects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check keys
    for item in data:
        assert "id" in item
        assert "name" in item
        assert "icon" in item
        assert "questions_count" in item

def test_get_syllabus_economics():
    response = client.get("/api/syllabus/Economy")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for item in data:
        assert "name" in item
        assert "textbook" in item

def test_get_questions():
    response = client.get("/api/questions?subject=Economy")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        q = data[0]
        assert "subject" in q
        assert "topic" in q
        assert "question_en" in q
        assert "question_ta" in q
        assert "options" in q
        assert "correct_option" in q

def test_calculate_stats_empty():
    response = client.post("/api/stats", json=[])
    assert response.status_code == 200
    data = response.json()
    assert data["total_tests"] == 0
    assert data["mastery_percent"] == 0

def test_calculate_stats_with_data():
    sample_history = [
        {
            "topic": "Nature of Indian Economy",
            "group": "Group 1",
            "correctCount": 8,
            "totalCount": 10,
            "answers": {"0": "A", "1": "B"},
            "questions": []
        }
    ]
    response = client.post("/api/stats", json=sample_history)
    assert response.status_code == 200
    data = response.json()
    assert data["total_tests"] == 1
    assert data["total_correct"] == 8
    assert data["total_solved"] == 10
    assert data["avg_accuracy"] == 80

def test_submit_session():
    # Insert a mock session submission
    payload = {
        "user_id": "test_user_uuid_or_email",
        "topic_name": "Nature of Indian Economy",
        "correct_count": 4,
        "total_count": 5,
        "time_taken": 120,
        "answers": [
            {"question_id": 1, "selected_option": "A", "is_correct": True},
            {"question_id": 2, "selected_option": "B", "is_correct": False}
        ]
    }
    response = client.post("/api/sessions/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "success"

