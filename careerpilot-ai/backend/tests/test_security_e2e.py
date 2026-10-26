"""
Security, End-to-End, and Data-Isolation Tests for CareerPilot AI.
Verifies expired/tampered tokens, cross-user isolation for history & applications,
CORS preflight configuration, and database persistence.
"""
from datetime import timedelta
import jwt
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM
from app.services.auth import create_access_token
from app.main import app
import app.models as models
from .conftest import client, TestingSessionLocal, test_engine


def test_expired_token_handling():
    # Register test user
    client.post("/api/auth/register", json={"email": "expired_test@example.com", "password": "Password123!"})
    login_res = client.post("/api/auth/login", json={"email": "expired_test@example.com", "password": "Password123!"})
    user_id = login_res.json()["user"]["id"]

    # Issue an expired token (expired 10 minutes ago)
    expired_token = create_access_token(user_id, expires_delta=timedelta(minutes=-10))

    client.cookies.clear()
    r_auth = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r_auth.status_code == 401
    assert "expired" in r_auth.json()["detail"].lower()

    r_app = client.get("/api/applications", headers={"Authorization": f"Bearer {expired_token}"})
    assert r_app.status_code == 401


def test_tampered_and_invalid_token_handling():
    client.cookies.clear()
    # 1. Fake signature signed with an attacker's key (minimum 32 bytes to conform to RFC 7518)
    attacker_key = "attacker-secret-key-that-is-at-least-32-bytes-long!"
    attacker_token = jwt.encode({"sub": "1", "email": "admin@example.com"}, attacker_key, algorithm="HS256")
    r_tampered = client.get("/api/auth/me", headers={"Authorization": f"Bearer {attacker_token}"})
    assert r_tampered.status_code == 401


    # 2. Corrupted base64 token
    r_corrupt = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert r_corrupt.status_code == 401

    # 3. Malformed Authorization headers
    r_no_bearer = client.get("/api/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert r_no_bearer.status_code == 401

    r_empty_bearer = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
    assert r_empty_bearer.status_code == 401


def test_cross_user_history_data_isolation():
    # Register User Alpha and User Beta
    client.cookies.clear()
    r_alpha = client.post("/api/auth/register", json={"email": "alpha@example.com", "password": "AlphaPassword123!", "full_name": "Alpha"})
    alpha_token = r_alpha.json()["access_token"]
    alpha_headers = {"Authorization": f"Bearer {alpha_token}"}

    r_beta = client.post("/api/auth/register", json={"email": "beta@example.com", "password": "BetaPassword123!", "full_name": "Beta"})
    beta_token = r_beta.json()["access_token"]
    beta_headers = {"Authorization": f"Bearer {beta_token}"}

    client.cookies.clear()

    # 1. Alpha generates a roadmap snapshot
    client.post("/api/roadmap", json={"target_role": "Data Scientist", "current_skills": ["python"], "weeks": 8}, headers=alpha_headers)

    # 2. Beta requests roadmap history -> must NOT contain Alpha's snapshot
    beta_history = client.get("/api/roadmap/history", headers=beta_headers).json()["items"]
    assert len(beta_history) == 0

    # 3. Alpha requests roadmap history -> contains Alpha's snapshot
    alpha_history = client.get("/api/roadmap/history", headers=alpha_headers).json()["items"]
    assert len(alpha_history) >= 1
    assert all(h["target_role"] == "Data Scientist" for h in alpha_history)

    # 4. Alpha completes an interview evaluation
    client.post("/api/interviews/evaluate", json={
        "question": "What is precision and recall?",
        "answer": "Precision measures true positives over all predicted positives. Recall measures true positives over all actual positives.",
        "role": "Data Scientist"
    }, headers=alpha_headers)

    # 5. Beta requests interview history -> must NOT contain Alpha's session
    beta_interview_history = client.get("/api/interviews/history", headers=beta_headers).json()["items"]
    assert len(beta_interview_history) == 0

    # 6. Alpha requests interview history -> contains Alpha's session
    alpha_interview_history = client.get("/api/interviews/history", headers=alpha_headers).json()["items"]
    assert len(alpha_interview_history) >= 1


def test_cors_preflight_configuration():
    # Test preflight OPTIONS request from configured origin
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    r = client.options("/api/applications", headers=headers)
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r.headers.get("access-control-allow-credentials") == "true"


def test_database_persistence_and_relations():
    # Direct database verification using a separate DB session
    client.cookies.clear()
    r = client.post("/api/auth/register", json={"email": "db_verify@example.com", "password": "DbPassword123!", "full_name": "DB Tester"})
    token = r.json()["access_token"]
    user_id = r.json()["user"]["id"]

    client.post(
        "/api/applications",
        json={"company": "Persistent Corp", "role": "Full Stack Dev", "status": "Applied", "notes": "E2E persistence check"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Query DB directly to verify persistence
    db = TestingSessionLocal()
    app_record = db.query(models.Application).filter(models.Application.company == "Persistent Corp").first()
    assert app_record is not None
    assert app_record.user_id == user_id
    assert app_record.status == "Applied"
    assert app_record.notes == "E2E persistence check"
    assert app_record.created_at is not None
    assert app_record.owner.email == "db_verify@example.com"
    db.close()


def test_all_core_ml_services_remain_operational():
    # Ensure all core intelligence services work smoothly with or without auth
    client.cookies.clear()
    r_reg = client.post("/api/auth/register", json={"email": "ml_test@example.com", "password": "MlPassword123!"})
    token = r_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Jobs catalogue
    r_jobs = client.get("/api/jobs")
    assert r_jobs.status_code == 200
    assert len(r_jobs.json()["items"]) > 0

    # 2. Text match
    r_match = client.post(
        "/api/match",
        json={
            "resume_text": "Experienced Python developer with pandas, SQL, machine learning, and data analysis skills.",
            "job_description": "Looking for a Python and SQL engineer with machine learning and pandas experience.",
            "role": "Data Scientist",
        },
        headers=headers,
    )
    assert r_match.status_code == 200
    match_data = r_match.json()
    assert match_data["similarity_score"] > 0
    assert "python" in match_data["matched_skills"]
    assert "role_gap" in match_data

    # 3. Roadmap generation
    r_roadmap = client.post(
        "/api/roadmap",
        json={"target_role": "Data Scientist", "current_skills": ["python"], "weeks": 8},
        headers=headers,
    )
    assert r_roadmap.status_code == 200
    assert len(r_roadmap.json()["tasks"]) > 0

    # 4. Interview questions
    r_questions = client.get("/api/interviews/questions?role=Data+Scientist&category=technical")
    assert r_questions.status_code == 200
    assert len(r_questions.json()["items"]) > 0

    # 5. Interview evaluation
    r_eval = client.post(
        "/api/interviews/evaluate",
        json={
            "question": "What is gradient descent?",
            "answer": "Gradient descent is an optimization algorithm used to minimize a cost function by iteratively moving in the direction of steepest descent.",
            "role": "Data Scientist",
        },
        headers=headers,
    )
    assert r_eval.status_code == 200
    assert 0 <= r_eval.json()["practice_score"] <= 100
