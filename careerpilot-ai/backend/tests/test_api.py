"""
API-level tests for FastAPI routes — uses TestClient + SQLite in-memory.
Run from backend/: python -m pytest tests/ -v
"""
from .conftest import client, TestingSessionLocal, test_engine



# ── Health ────────────────────────────────────────────────────────────────────────
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Jobs ──────────────────────────────────────────────────────────────────────────
def test_list_jobs():
    r = client.get("/api/jobs")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) == 4
    assert data["items"][0]["is_demo"] is True


# ── Roadmap + history ─────────────────────────────────────────────────────────────
def test_roadmap_known_role_persisted():
    r = client.post("/api/roadmap", json={"target_role": "Data Scientist", "current_skills": ["python"], "weeks": 8})
    assert r.status_code == 200
    body = r.json()
    assert body["target_role"] == "Data Scientist"
    assert len(body["tasks"]) > 0

    # History should have at least one entry
    rh = client.get("/api/roadmap/history")
    assert rh.status_code == 200
    history = rh.json()["items"]
    assert len(history) >= 1
    assert history[0]["target_role"] == "Data Scientist"


def test_roadmap_unknown_role():
    r = client.post("/api/roadmap", json={"target_role": "Astrophysics Engineer", "current_skills": [], "weeks": 4})
    assert r.status_code == 200
    assert r.json()["tasks"] == []


# ── Interview evaluate + history ──────────────────────────────────────────────────
def test_interview_evaluate_persisted():
    r = client.post("/api/interviews/evaluate", json={
        "question": "Explain overfitting.",
        "answer": "Overfitting happens when a model is too complex. For example, it memorises training data and fails on new data. I would use regularization because it reduces variance.",
        "role": "ML Engineer"
    })
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["practice_score"] <= 100
    assert "disclaimer" in body

    # History should have entry
    rh = client.get("/api/interviews/history")
    assert rh.status_code == 200
    history = rh.json()["items"]
    assert len(history) >= 1
    assert history[0]["role"] == "ML Engineer"


def get_auth_headers():
    email = "api_test_user@example.com"
    pwd = "ApiTestPassword123!"
    # Try login first, register if not exists
    r = client.post("/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code == 200:
        token = r.json()["access_token"]
    else:
        reg = client.post("/api/auth/register", json={"email": email, "password": pwd, "full_name": "API Tester"})
        token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Applications CRUD ─────────────────────────────────────────────────────────────
def test_application_lifecycle():
    # Unauthenticated request fails with 401
    client.cookies.clear()
    r_unauth = client.get("/api/applications")
    assert r_unauth.status_code == 401

    headers = get_auth_headers()

    # Create
    r = client.post("/api/applications", json={"company": "Acme Corp", "role": "Data Scientist", "status": "Applied"}, headers=headers)
    assert r.status_code == 201
    app_id = r.json()["id"]
    assert r.json()["status"] == "Applied"


    # List
    r = client.get("/api/applications", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(a["id"] == app_id for a in items)

    # Patch status
    r = client.patch(f"/api/applications/{app_id}", json={"status": "Interview"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "Interview"

    # Delete
    r = client.delete(f"/api/applications/{app_id}", headers=headers)
    assert r.status_code == 204

    # Confirm deleted — 404 on subsequent patch
    r = client.patch(f"/api/applications/{app_id}", json={"status": "Offer"}, headers=headers)
    assert r.status_code == 404


def test_application_invalid_status():
    headers = get_auth_headers()
    r = client.post("/api/applications", json={"company": "X", "role": "Y", "status": "NotARealStatus"}, headers=headers)
    assert r.status_code == 422  # Pydantic validation error


def test_application_missing_company():
    headers = get_auth_headers()
    r = client.post("/api/applications", json={"role": "Engineer"}, headers=headers)
    assert r.status_code == 422



def test_interview_questions_invalid_category():
    r = client.get("/api/interviews/questions?category=unknown")
    assert r.status_code == 400


def test_interview_questions_valid():
    r = client.get("/api/interviews/questions?category=technical&role=Data+Scientist&limit=3")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) <= 3
    assert all("question" in q for q in items)
