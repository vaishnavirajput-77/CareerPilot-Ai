"""
Phase 5: Database Persistence & Cross-User Isolation Tests for CareerPilot AI.
Verifies:
1. Applications CRUD persistence and cross-user data isolation.
2. Resume analysis persistence and latest resume retrieval.
3. Skill roadmap persistence and latest roadmap reload.
4. Mock interview evaluation persistence and latest interview reload.
5. Cross-user isolation: User B cannot retrieve or overwrite User A's saved records.
"""
import io
import pytest
from app.main import app
import app.models as models
from .conftest import client, TestingSessionLocal, test_engine


def test_applications_crud_and_cross_user_isolation():
    client.cookies.clear()
    
    # 1. Register User 1 and User 2
    r1 = client.post("/api/auth/register", json={"email": "pers_user1@example.com", "password": "Password123!", "full_name": "User One"})
    assert r1.status_code == 201
    token1 = r1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    r2 = client.post("/api/auth/register", json={"email": "pers_user2@example.com", "password": "Password123!", "full_name": "User Two"})
    assert r2.status_code == 201
    token2 = r2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    client.cookies.clear()

    # 2. User 1 creates an application
    create_res = client.post(
        "/api/applications",
        json={"company": "Acme Corp", "role": "Senior Engineer", "status": "Applied", "notes": "Initial application"},
        headers=headers1
    )
    assert create_res.status_code == 201
    app1_data = create_res.json()
    app1_id = app1_data["id"]
    assert app1_data["company"] == "Acme Corp"
    assert app1_data["status"] == "Applied"

    # 3. User 1 fetches applications (simulating page reload)
    list1_res = client.get("/api/applications", headers=headers1)
    assert list1_res.status_code == 200
    apps1 = list1_res.json()["items"]
    assert len(apps1) == 1
    assert apps1[0]["id"] == app1_id
    assert apps1[0]["company"] == "Acme Corp"

    # 4. User 2 fetches applications -> must be empty (Cross-User Isolation)
    list2_res = client.get("/api/applications", headers=headers2)
    assert list2_res.status_code == 200
    assert len(list2_res.json()["items"]) == 0

    # 5. User 2 tries to update User 1's application -> 404
    hack_res = client.patch(
        f"/api/applications/{app1_id}",
        json={"status": "Rejected"},
        headers=headers2
    )
    assert hack_res.status_code == 404

    # 6. User 1 updates application status to "Interview"
    update_res = client.patch(
        f"/api/applications/{app1_id}",
        json={"status": "Interview", "notes": "Phone screen scheduled"},
        headers=headers1
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "Interview"
    assert update_res.json()["notes"] == "Phone screen scheduled"

    # 7. Reload and verify updated record persists
    reload_res = client.get("/api/applications", headers=headers1)
    assert reload_res.json()["items"][0]["status"] == "Interview"

    # 8. User 2 tries to delete User 1's application -> 404
    del_hack_res = client.delete(f"/api/applications/{app1_id}", headers=headers2)
    assert del_hack_res.status_code == 404

    # 9. User 1 deletes their application -> 204
    del_res = client.delete(f"/api/applications/{app1_id}", headers=headers1)
    assert del_res.status_code == 204

    # 10. Reload and verify deletion persisted
    final_reload = client.get("/api/applications", headers=headers1)
    assert len(final_reload.json()["items"]) == 0


def test_resume_analysis_persistence_and_reload():
    client.cookies.clear()
    
    # Register Resume User
    r_user = client.post("/api/auth/register", json={"email": "resume_pers@example.com", "password": "Password123!"})
    token = r_user.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.cookies.clear()

    # Before upload, latest resume item is None
    r_none = client.get("/api/analyze/resume/latest", headers=headers)
    assert r_none.status_code == 200
    assert r_none.json()["item"] is None

    # Upload resume text file
    resume_content = b"John Doe\nSoftware Engineer with experience in Python, FastAPI, Docker, and React."
    upload_res = client.post(
        "/api/analyze/resume",
        files={"file": ("resume.txt", io.BytesIO(resume_content), "text/plain")},
        headers=headers
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "python" in [s.lower() for s in upload_data["skills"]]
    assert upload_data["filename"] == "resume.txt"

    # Simulate page refresh by fetching /api/analyze/resume/latest
    latest_res = client.get("/api/analyze/resume/latest", headers=headers)
    assert latest_res.status_code == 200
    persisted_data = latest_res.json()["item"]
    assert persisted_data is not None
    assert persisted_data["filename"] == "resume.txt"
    assert "python" in [s.lower() for s in persisted_data["skills"]]
    assert persisted_data["character_count"] == upload_data["character_count"]

    # Verify cross-user isolation: Another user receives None
    r_other = client.post("/api/auth/register", json={"email": "resume_other@example.com", "password": "Password123!"})
    other_token = r_other.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}
    client.cookies.clear()

    other_latest = client.get("/api/analyze/resume/latest", headers=other_headers)
    assert other_latest.status_code == 200
    assert other_latest.json()["item"] is None


def test_skill_roadmap_persistence_and_latest_reload():
    client.cookies.clear()
    
    r_user = client.post("/api/auth/register", json={"email": "roadmap_pers@example.com", "password": "Password123!"})
    token = r_user.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.cookies.clear()

    # Generate roadmap for Backend Developer
    gen_res = client.post(
        "/api/roadmap",
        json={"target_role": "Backend Developer", "current_skills": ["python"], "weeks": 6},
        headers=headers
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["target_role"] == "Backend Developer"
    assert len(gen_data["tasks"]) > 0

    # Fetch latest roadmap (simulating page reload)
    latest_res = client.get("/api/roadmap/latest", headers=headers)
    assert latest_res.status_code == 200
    latest_item = latest_res.json()["item"]
    assert latest_item is not None
    assert latest_item["target_role"] == "Backend Developer"
    assert latest_item["weeks"] == 6
    assert len(latest_item["result_json"]["tasks"]) == len(gen_data["tasks"])

    # Verify cross-user isolation: User B has no roadmap
    r_user2 = client.post("/api/auth/register", json={"email": "roadmap_pers2@example.com", "password": "Password123!"})
    token2 = r_user2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    client.cookies.clear()

    latest_user2 = client.get("/api/roadmap/latest", headers=headers2)
    assert latest_user2.status_code == 200
    assert latest_user2.json()["item"] is None


def test_mock_interview_persistence_and_latest_reload():
    client.cookies.clear()
    
    r_user = client.post("/api/auth/register", json={"email": "interview_pers@example.com", "password": "Password123!"})
    token = r_user.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.cookies.clear()

    # Evaluate interview response
    eval_res = client.post(
        "/api/interviews/evaluate",
        json={
            "question": "Explain dependency injection in FastAPI.",
            "answer": "FastAPI uses Depends() to declare dependencies in path operations, allowing clean sharing of database sessions and auth services.",
            "role": "Backend Developer"
        },
        headers=headers
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert "suggestions" in eval_data
    assert "practice_score" in eval_data

    # Fetch latest interview (simulating page reload)
    latest_res = client.get("/api/interviews/latest", headers=headers)
    assert latest_res.status_code == 200
    latest_item = latest_res.json()["item"]
    assert latest_item is not None
    assert latest_item["role"] == "Backend Developer"
    assert latest_item["question"] == "Explain dependency injection in FastAPI."
    assert latest_item["practice_score"] == eval_data["practice_score"]
    assert len(latest_item["suggestions_json"]) == len(eval_data["suggestions"])

    # Verify cross-user isolation: User B has no interview session
    r_user2 = client.post("/api/auth/register", json={"email": "interview_pers2@example.com", "password": "Password123!"})
    token2 = r_user2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    client.cookies.clear()

    latest_user2 = client.get("/api/interviews/latest", headers=headers2)
    assert latest_user2.status_code == 200
    assert latest_user2.json()["item"] is None
